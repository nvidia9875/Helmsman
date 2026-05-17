"""オフライン評価 CLI — 既存音声 (WAV) や事前書き起こし (JSONL) で
Helmsman パイプライン全体を走らせ、結果を `eval_runs/<timestamp>/` に書き出す。

Teams Bot trial を待つ間の精度向上ループ用。

使い方:
  # WAV 入力 (Speech SDK で STT)
  uv run python scripts/eval_offline.py \\
      --audio path/to/meeting.wav \\
      --goal "6/30 のローンチ可否を決定する" \\
      --mode Decision

  # 事前書き起こし入力 (STT スキップで agent プロンプト調整)
  uv run python scripts/eval_offline.py \\
      --transcript path/to/utterances.jsonl \\
      --goal "..."

非 WAV (mp3 / m4a / mp4 など) は CLI が裏で ffmpeg 自動変換します。
ffmpeg がない場合のみ事前変換が必要:
  ffmpeg -i meeting.m4a -ar 16000 -ac 1 -c:a pcm_s16le meeting.wav

JSONL フォーマット (1 行 1 utterance):
  {"text": "では始めます", "speaker_id": "tanaka", "offset_sec": 0, "duration_sec": 1.8}
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from helmsman.eval.audio import (
    FfmpegMissingError,
    convert_to_wav_16k_mono,
    detect_audio_duration_seconds,
    stream_utterances_from_jsonl,
    stream_utterances_from_wav,
)
from helmsman.eval.report import write_report
from helmsman.eval.runner import run_eval
from helmsman.models.meeting import MeetingMode, UserIntensity


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Helmsman offline evaluation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--audio",
        type=Path,
        help="音声ファイル (WAV / MP3 / m4a / mp4 など — WAV 以外は自動 ffmpeg 変換)",
    )
    src.add_argument(
        "--transcript",
        type=Path,
        help="JSONL 形式の事前書き起こし (STT スキップ)",
    )
    p.add_argument(
        "--goal",
        default="",
        help="会議のゴール (空なら監視モード)",
    )
    p.add_argument(
        "--mode",
        choices=[m.value for m in MeetingMode],
        default=MeetingMode.DECISION.value,
        help="会議モード",
    )
    p.add_argument(
        "--intensity",
        choices=[i.value for i in UserIntensity],
        default=UserIntensity.NORMAL.value,
        help="介入頻度",
    )
    p.add_argument(
        "--tick-every-sec",
        type=float,
        default=30.0,
        help="tick 発火間隔 (音声時間軸の秒数)",
    )
    p.add_argument(
        "--total-minutes",
        type=int,
        default=60,
        help="会議想定時間 (TimeKeeper 用)",
    )
    p.add_argument(
        "--language",
        default="ja-JP",
        help="STT 言語コード (audio モードのみ)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("eval_runs"),
        help="出力先ルートディレクトリ",
    )
    p.add_argument(
        "--label",
        default="",
        help="出力ディレクトリ名のサフィックス (省略時は timestamp のみ)",
    )
    p.add_argument(
        "--cheap",
        action="store_true",
        help=(
            "DecisionCapture と DissentSurface を gpt-5.4-mini に落とす "
            "(コスト約 75%% カット予想、品質劣化の幅を計測するモード)"
        ),
    )
    p.add_argument(
        "--doc-text",
        type=Path,
        default=None,
        help=(
            "RAG 検証用: plain text の文書ファイルパス。指定すると content が "
            "document_excerpts として GoalDecomposer / Coverage / Decision に注入される "
            "(本番は Azure AI Search からの抜粋を入れる経路を模擬)。"
        ),
    )
    return p.parse_args(argv)


def _apply_cheap_mode() -> None:
    """HIGH tier agents を MINI に動的書き換え (この run のみ)。"""
    from helmsman.agents import DecisionCapture, DissentSurface
    from helmsman.core.llm_client import ModelTier

    DecisionCapture.TIER = ModelTier.MINI
    DissentSurface.TIER = ModelTier.MINI


async def _main_async(args: argparse.Namespace) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{args.label}" if args.label else ""
    out_dir = args.out / f"{timestamp}{suffix}"

    print(f"→ output: {out_dir}", flush=True)
    print(f"→ goal: {args.goal or '(monitor mode)'}", flush=True)
    print(
        f"→ mode={args.mode} intensity={args.intensity} "
        f"tick={args.tick_every_sec}s"
        + (" cheap-mode" if args.cheap else ""),
        flush=True,
    )

    if args.cheap:
        _apply_cheap_mode()

    converted_wav: Path | None = None  # 一時 WAV (後始末用)
    audio_duration = 0.0

    doc_excerpts: str | None = None
    if args.doc_text:
        if not args.doc_text.exists():
            print(f"doc-text not found: {args.doc_text}", file=sys.stderr)
            return 5
        doc_excerpts = args.doc_text.read_text(encoding="utf-8")
        print(
            f"→ doc-text: {args.doc_text} ({len(doc_excerpts)} chars)",
            flush=True,
        )

    if args.audio:
        if not args.audio.exists():
            print(f"audio not found: {args.audio}", file=sys.stderr)
            return 2

        # WAV 以外は ffmpeg で 16kHz mono 16-bit PCM に自動変換
        try:
            wav_path = convert_to_wav_16k_mono(args.audio)
        except FfmpegMissingError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 3
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 4

        if wav_path != args.audio:
            converted_wav = wav_path  # 終わったら消す
            print(f"→ converted to WAV: {wav_path}", flush=True)

        audio_duration = detect_audio_duration_seconds(wav_path)
        print(f"→ audio duration: {audio_duration:.1f} sec", flush=True)

        stream = stream_utterances_from_wav(
            wav_path, meeting_id="eval", language=args.language
        )
    else:
        if not args.transcript.exists():
            print(f"transcript not found: {args.transcript}", file=sys.stderr)
            return 2
        stream = stream_utterances_from_jsonl(args.transcript, meeting_id="eval")

    try:
        result = await run_eval(
            stream,
            goal=args.goal,
            mode=MeetingMode(args.mode),
            intensity=UserIntensity(args.intensity),
            total_minutes=args.total_minutes,
            tick_every_sec=args.tick_every_sec,
            audio_duration_sec=audio_duration,
            doc_excerpts=doc_excerpts,
        )
    finally:
        if converted_wav is not None and converted_wav.exists():
            converted_wav.unlink(missing_ok=True)

    metrics = write_report(result, out_dir)

    print("", flush=True)
    print("─── results ─────────────────────", flush=True)
    print(f"  utterances:    {metrics['utterance_count']}", flush=True)
    print(f"  ticks:         {metrics['tick_count']}", flush=True)
    print(
        f"  candidates→delivered: "
        f"{metrics['candidates_total']} → {metrics['delivered_total']} "
        f"({metrics['acceptance_rate'] * 100:.1f}%)",
        flush=True,
    )
    levels = metrics["delivered_by_level"]
    print(
        f"  by level:      "
        f"L1={levels.get('L1', 0)} L2={levels.get('L2', 0)} L3={levels.get('L3', 0)}",
        flush=True,
    )
    print(f"  llm cost:      ${metrics['llm_cost_usd']:.4f}", flush=True)
    print(f"  llm tokens:    {metrics['llm_total_tokens']:,}", flush=True)
    print(f"  report:        {out_dir / 'report.md'}", flush=True)
    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
