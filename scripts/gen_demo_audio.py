"""デモ動画用の擬似会議音声を Azure TTS で生成する。

JSONL fixture の発言を speaker 別に分けて、speaker ごとの WAV を生成する。
全 WAV は同じ全体長で揃うので、複数デバイスから **同時に再生** すれば
擬似的な多人数会議になる (発言は被らない設計の fixture が前提)。

デフォルトは 2 人会議 (`demo_meeting_2person.jsonl`) で、yamada と sato の
2 つの WAV を生成。

使い方:
    uv run python scripts/gen_demo_audio.py
    # → eval_runs/demo-audio/yamada.wav  (yamada だけの声 + 他は無音)
    # → eval_runs/demo-audio/sato.wav    (sato だけの声 + 他は無音)
    # → eval_runs/demo-audio/l3_intervention.wav (Helmsman bot の L3 介入)

    # 別 fixture を使う場合
    uv run python scripts/gen_demo_audio.py --fixture scripts/fixtures/demo_meeting.jsonl

音声マッピング (storyboard 準拠、全声を distinct に):
    yamada     (CTO・議長)   → ja-JP-DaichiNeural   (落ち着いた男性)
    sato       (PM)         → ja-JP-KeitaNeural    (中年男性、慎重)
    takahashi  (Eng Lead)   → ja-JP-NaokiNeural    (若手男性)
    nakamura   (Designer)   → ja-JP-AoiNeural      (控えめ女性)
    suzuki     (Marketing)  → ja-JP-MayuNeural     (明朗女性)
    Helmsman bot (L3)       → ja-JP-NanamiNeural   (既存と同じ)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import struct
import sys
import wave
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from helmsman.core.config import get_settings  # noqa: E402

SAMPLE_RATE: Final = 16000
SAMPLE_WIDTH_BYTES: Final = 2  # 16-bit
CHANNELS: Final = 1

VOICE_MAP: Final[dict[str, str]] = {
    "yamada": "ja-JP-DaichiNeural",   # 男性、落ち着いた CTO
    "sato": "ja-JP-MayuNeural",       # 女性、明朗な PM ← yamada と性別で区別
    "takahashi": "ja-JP-NaokiNeural",
    "nakamura": "ja-JP-AoiNeural",
    "suzuki": "ja-JP-KeitaNeural",
}

L3_INTERVENTION_TEXT: Final = (
    "残り 10 分です。各論点で、うまくいかなかった時の撤退ラインを確認しておきましょう。"
)
L3_VOICE: Final = "ja-JP-NanamiNeural"

DEFAULT_FIXTURE: Final = ROOT / "scripts" / "fixtures" / "demo_meeting_2person.jsonl"
OUT_DIR: Final = ROOT / "eval_runs" / "demo-audio"


async def synthesize_pcm_with_voice(text: str, voice_name: str) -> bytes:
    """指定した声で TTS → raw PCM (16kHz/16bit/mono)。"""
    settings = get_settings()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        raise RuntimeError("Azure Speech not configured (set AZURE_SPEECH_KEY/REGION)")

    def _sync() -> bytes:
        import azure.cognitiveservices.speech as speechsdk

        config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        config.speech_synthesis_voice_name = voice_name
        config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        synth = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        result = synth.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            raise RuntimeError(
                f"TTS canceled ({voice_name}): {details.reason} {details.error_details}"
            )
        raise RuntimeError(f"TTS failed ({voice_name}): {result.reason}")

    return await asyncio.to_thread(_sync)


def write_wav(pcm: bytes, out_path: Path) -> None:
    """raw PCM bytes を WAV ヘッダ付きで保存。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def silence_pcm_bytes(seconds: float) -> bytes:
    """指定秒数の無音 PCM (16-bit/16kHz/mono)。"""
    samples = max(0, int(seconds * SAMPLE_RATE))
    return struct.pack(f"<{samples}h", *([0] * samples))


def verify_no_overlap(utterances: list[dict]) -> list[tuple[int, int, float]]:
    """全 utterance 間の被りを検出。被り 0 を保証する。"""
    overlaps = []
    intervals = sorted(
        [
            (u["offset_sec"], u["offset_sec"] + u["duration_sec"], i)
            for i, u in enumerate(utterances)
        ]
    )
    for i in range(len(intervals) - 1):
        a_start, a_end, a_idx = intervals[i]
        b_start, b_end, b_idx = intervals[i + 1]
        if a_end > b_start:
            overlaps.append((a_idx + 1, b_idx + 1, a_end - b_start))
    return overlaps


async def synthesize_one(idx: int, text: str, voice: str) -> tuple[int, bytes]:
    """単一発言を合成。"""
    try:
        pcm = await synthesize_pcm_with_voice(text, voice)
        duration = len(pcm) // (SAMPLE_RATE * SAMPLE_WIDTH_BYTES)
        print(
            f"  [{idx + 1:>2}] {voice:<22} {duration:>2}s {text[:42]}…"
        )
        return idx, pcm
    except Exception as e:  # noqa: BLE001
        print(
            f"  [{idx + 1:>2}] ❌ {voice:<22} FAILED: {e}",
            file=sys.stderr,
        )
        return idx, b""


def _mix_tracks(tracks: list[bytes]) -> bytes:
    """異なる長さの PCM トラックを sample-wise sum で 1 本にミックス。

    最長トラックに合わせて短いものは末尾を 0 padding。
    被り 0 の保証下では sum は単純な OR 等価。clip は念のため。
    """
    if not tracks:
        return b""

    max_len = max(len(t) for t in tracks)
    padded = [t + b"\x00" * (max_len - len(t)) for t in tracks]
    n_samples = max_len // SAMPLE_WIDTH_BYTES
    unpacked = [struct.unpack(f"<{n_samples}h", t) for t in padded]

    mixed = bytearray(max_len)
    for i in range(n_samples):
        s = sum(track[i] for track in unpacked)
        s = max(-32768, min(32767, s))  # int16 clip
        struct.pack_into("<h", mixed, i * SAMPLE_WIDTH_BYTES, s)

    return bytes(mixed)


def build_speaker_track(
    speaker_id: str,
    utterances: list[dict],
    pcms: dict[int, bytes],
    total_seconds: float,
) -> bytes:
    """指定 speaker の発言だけを offset_sec の位置に配置し、無音で埋める。"""
    total_samples = int(total_seconds * SAMPLE_RATE)
    track = bytearray(total_samples * SAMPLE_WIDTH_BYTES)

    for i, u in enumerate(utterances):
        if u["speaker_id"] != speaker_id:
            continue
        pcm = pcms.get(i, b"")
        if not pcm:
            continue
        start_byte = int(u["offset_sec"] * SAMPLE_RATE) * SAMPLE_WIDTH_BYTES
        end_byte = start_byte + len(pcm)
        if end_byte > len(track):
            track.extend(b"\x00" * (end_byte - len(track)))
        track[start_byte:end_byte] = pcm

    return bytes(track)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help=f"JSONL fixture (default: {DEFAULT_FIXTURE.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--skip-l3",
        action="store_true",
        help="L3 介入音声を生成しない (再生成不要な時のスキップ用)",
    )
    args = parser.parse_args()

    fixture_path: Path = args.fixture
    if not fixture_path.exists():
        print(f"❌ fixture not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    utterances = [
        json.loads(line) for line in fixture_path.read_text().splitlines() if line.strip()
    ]
    print(f"📝 Loaded {len(utterances)} utterances from {fixture_path.name}")

    # speaker validation
    speakers = sorted({u["speaker_id"] for u in utterances})
    missing = [s for s in speakers if s not in VOICE_MAP]
    if missing:
        print(f"⚠️  Missing voice mapping for: {missing}", file=sys.stderr)
        sys.exit(2)

    print(f"   speakers: {', '.join(speakers)}")

    # 被り検査 (同時再生で混線しないことを保証)
    overlaps = verify_no_overlap(utterances)
    if overlaps:
        print(f"❌ 被り {len(overlaps)} 件検出 — 同時再生すると混線します:", file=sys.stderr)
        for a, b, gap in overlaps:
            print(f"   utt[{a}] と utt[{b}] が {gap:.2f} 秒重なってる", file=sys.stderr)
        sys.exit(3)
    print("   ✅ 被り 0 件 — 同時再生 OK")
    print()

    # 全 utterance 並列 TTS
    print(f"🔊 Synthesizing {len(utterances)} utterances in parallel...")
    print()
    tasks = [
        synthesize_one(i, u["text"], VOICE_MAP[u["speaker_id"]])
        for i, u in enumerate(utterances)
    ]
    results = await asyncio.gather(*tasks)
    pcms = dict(results)
    success_count = sum(1 for p in pcms.values() if p)
    print()
    print(f"✅ Synthesized {success_count}/{len(utterances)} utterances")
    print()

    # 全体長 (max(offset + duration) + 余白 1 秒)
    last = utterances[-1]
    total_sec = last["offset_sec"] + last["duration_sec"] + 1.0

    # speaker ごとに 1 本の WAV を生成
    print(f"🎬 Building per-speaker tracks ({total_sec:.1f} sec each)...")
    print()
    speaker_tracks: dict[str, bytes] = {}
    for speaker_id in speakers:
        track_pcm = build_speaker_track(speaker_id, utterances, pcms, total_sec)
        speaker_tracks[speaker_id] = track_pcm
        out_path = OUT_DIR / f"{speaker_id}.wav"
        write_wav(track_pcm, out_path)
        utt_count = sum(1 for u in utterances if u["speaker_id"] == speaker_id)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        voice = VOICE_MAP[speaker_id]
        print(
            f"   → {out_path.relative_to(ROOT)}  "
            f"({utt_count} 発言, {voice}, {size_mb:.1f} MB)"
        )

    # combined.wav: 全 speaker トラックを sample-wise sum でミックス
    # 被り 0 なので clip しても無問題。eval_offline.py --audio のテスト用。
    print()
    print("🎵 Mixing combined track (for `eval_offline.py --audio` testing)...")
    combined_pcm = _mix_tracks(list(speaker_tracks.values()))
    combined_path = OUT_DIR / "combined.wav"
    write_wav(combined_pcm, combined_path)
    size_mb = combined_path.stat().st_size / (1024 * 1024)
    print(
        f"   → {combined_path.relative_to(ROOT)}  "
        f"({total_sec:.1f} sec, {size_mb:.1f} MB)"
    )

    # L3 介入は別 WAV
    if not args.skip_l3:
        print()
        print(f"🤖 Synthesizing L3 intervention ({L3_VOICE})...")
        l3_pcm = await synthesize_pcm_with_voice(L3_INTERVENTION_TEXT, L3_VOICE)
        l3_path = OUT_DIR / "l3_intervention.wav"
        write_wav(l3_pcm, l3_path)
        l3_duration = len(l3_pcm) / (SAMPLE_RATE * SAMPLE_WIDTH_BYTES)
        print(f"   → {l3_path.relative_to(ROOT)} ({l3_duration:.1f} sec)")
        print(f"   Text: 「{L3_INTERVENTION_TEXT}」")

    print()
    print("🎉 Done! 撮影手順:")
    print("   1. 2 台のスマホそれぞれに 1 つずつ転送")
    print(f"      - スマホ A → {speakers[0]}.wav")
    print(f"      - スマホ B → {speakers[1]}.wav" if len(speakers) > 1 else "")
    print("   2. 2 台の PC をそれぞれ Teams 会議に参加させる")
    print("   3. 同時に再生開始 (タイマー合わせて 0 秒スタート)")
    print("   4. Helmsman bot を派遣 → 会議として進行")


if __name__ == "__main__":
    asyncio.run(main())
