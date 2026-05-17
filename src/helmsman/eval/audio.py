"""音声ファイル → Utterance ストリーム化。

Azure Speech SDK の continuous recognition を file 入力で動かして、
final 認識を順次 yield する。WAV (16kHz/16bit/mono PCM) を期待。

m4a/mp4 などは事前に ffmpeg で変換:
  ffmpeg -i in.m4a -ar 16000 -ac 1 -c:a pcm_s16le out.wav

JSONL モード (--transcript) では Speech SDK を呼ばず、テキストから直接
Utterance を組み立てる (agents プロンプト調整時の高速イテレーション用)。
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
import wave
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.models.utterance import Utterance

# Speech SDK が直接食える音声拡張子。それ以外は ffmpeg で WAV 化する。
NATIVE_WAV_SUFFIXES = {".wav"}
SUPPORTED_INPUT_SUFFIXES = {
    ".wav", ".mp3", ".m4a", ".mp4", ".aac", ".flac", ".ogg", ".opus", ".webm",
}


class TranscriptLine(BaseModel):
    """JSONL モードで読み込む 1 行。speaker_id / 経過時間は任意。"""

    text: str
    speaker_id: str = "unknown"
    offset_sec: float = 0.0
    duration_sec: float = 2.0


def detect_audio_duration_seconds(wav_path: Path) -> float:
    """WAV ファイルの長さ (秒) を取得。WAV 以外は 0 を返す。"""
    try:
        with wave.open(str(wav_path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate() or 16000
            return frames / float(rate)
    except (wave.Error, OSError, FileNotFoundError):
        return 0.0


class FfmpegMissingError(RuntimeError):
    """ffmpeg がインストールされていない時に投げる。"""


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def convert_to_wav_16k_mono(src: Path) -> Path:
    """src を 16kHz / mono / 16-bit PCM WAV に変換した一時ファイルパスを返す。

    呼び出し側は使い終わったら削除する責任を負う (通常は `tempfile` cleanup)。
    src が既に .wav の場合はそのまま返す (再変換しない)。

    Raises:
      FfmpegMissingError: ffmpeg が見つからない
      RuntimeError: 変換失敗
    """
    if src.suffix.lower() in NATIVE_WAV_SUFFIXES:
        return src

    if not _ffmpeg_available():
        raise FfmpegMissingError(
            "ffmpeg が見つかりません。Mac なら `brew install ffmpeg`、"
            "Ubuntu なら `apt install ffmpeg` でインストールしてください。"
            "もしくは事前に WAV (16kHz/mono/16bit PCM) に変換してから --audio に渡してください。"
        )

    if src.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
        logger.warning(
            "eval.audio.unknown_suffix",
            suffix=src.suffix,
            hint="サポート外の拡張子ですが ffmpeg に渡してみます",
        )

    # 一時 WAV ファイル (呼び出し側で unlink)
    fd, tmp_path_str = tempfile.mkstemp(prefix="helmsman_eval_", suffix=".wav")
    import os

    os.close(fd)
    tmp_path = Path(tmp_path_str)

    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i", str(src),
        "-ar", "16000",  # 16 kHz
        "-ac", "1",  # mono
        "-c:a", "pcm_s16le",  # 16-bit PCM
        "-loglevel", "error",
        str(tmp_path),
    ]
    logger.info("eval.audio.converting", src=str(src), dst=str(tmp_path))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"ffmpeg 変換失敗 (exit {proc.returncode}): {proc.stderr.strip()[:500]}"
        )
    logger.info(
        "eval.audio.converted",
        src=str(src),
        dst=str(tmp_path),
        size_bytes=tmp_path.stat().st_size,
    )
    return tmp_path


async def stream_utterances_from_wav(
    wav_path: Path,
    *,
    meeting_id: str,
    language: str = "ja-JP",
    speaker_resolver=None,
) -> AsyncIterator[Utterance]:
    """WAV ファイルを Azure Speech SDK に流し、final 認識を Utterance として yield。

    Speech SDK の認識コールバックは別 thread から呼ばれるので asyncio.Queue
    経由でメインループに橋渡しする (StreamingTranscriber と同じパターン)。
    """
    settings = get_settings()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        raise RuntimeError(
            "Azure Speech が設定されていません (AZURE_SPEECH_KEY / AZURE_SPEECH_REGION)"
        )

    import azure.cognitiveservices.speech as speechsdk  # 遅延 import

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )
    speech_config.speech_recognition_language = language

    audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[TranscriptLine | None] = asyncio.Queue()

    def _on_recognized(evt: object) -> None:  # noqa: ANN401
        r = evt.result  # type: ignore[attr-defined]
        text = (r.text or "").strip()
        if not text:
            return
        offset_sec = (r.offset or 0) / 10_000_000.0  # 100ns → s
        duration_sec = max(0.5, (r.duration or 0) / 10_000_000.0)
        line = TranscriptLine(
            text=text,
            offset_sec=offset_sec,
            duration_sec=duration_sec,
        )
        try:
            loop.call_soon_threadsafe(queue.put_nowait, line)
        except RuntimeError:
            pass

    def _on_session_stopped(_evt: object) -> None:  # noqa: ANN401
        try:
            loop.call_soon_threadsafe(queue.put_nowait, None)
        except RuntimeError:
            pass

    def _on_canceled(evt: object) -> None:  # noqa: ANN401
        logger.warning("eval.audio.canceled", reason=str(evt))
        try:
            loop.call_soon_threadsafe(queue.put_nowait, None)
        except RuntimeError:
            pass

    recognizer.recognized.connect(_on_recognized)
    recognizer.session_stopped.connect(_on_session_stopped)
    recognizer.canceled.connect(_on_canceled)
    recognizer.start_continuous_recognition_async()

    try:
        while True:
            line = await queue.get()
            if line is None:
                break
            yield _line_to_utterance(
                line, meeting_id=meeting_id, speaker_resolver=speaker_resolver
            )
    finally:
        recognizer.stop_continuous_recognition_async()


async def stream_utterances_from_jsonl(
    jsonl_path: Path,
    *,
    meeting_id: str,
    delay_between_sec: float = 0.0,
) -> AsyncIterator[Utterance]:
    """JSONL の各行を Utterance に変換して yield (STT を介さない高速モード)。

    delay_between_sec > 0 なら各行の間に sleep — リアルタイム再生のシミュレーション。
    """
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        data = json.loads(raw)
        line = TranscriptLine.model_validate(data)
        yield _line_to_utterance(line, meeting_id=meeting_id, speaker_resolver=None)
        if delay_between_sec > 0:
            await asyncio.sleep(delay_between_sec)


def _line_to_utterance(
    line: TranscriptLine,
    *,
    meeting_id: str,
    speaker_resolver,
) -> Utterance:
    base = datetime.now(UTC)
    started = base + timedelta(seconds=line.offset_sec)
    speaker_id = (
        speaker_resolver(line) if speaker_resolver else line.speaker_id
    ) or "unknown"
    return Utterance(
        meeting_id=meeting_id,
        speaker_id=speaker_id,
        text=line.text,
        started_at=started,
        ended_at=started + timedelta(seconds=line.duration_sec),
        duration_sec=line.duration_sec,
        confidence=1.0,
        is_final=True,
    )
