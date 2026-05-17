"""Azure Speech SDK ストリーミング STT を asyncio に橋渡しする wrapper。

ACS Media Streaming WebSocket から流れてくる PCM 16kHz/16bit/mono audio chunk を
push_audio() で投げ込むと、final 認識結果が async queue に流れる。
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from helmsman.core.config import get_settings
from helmsman.core.logging import logger


class TranscriptEvent(BaseModel):
    """STT が認識した 1 フレーズ。

    UNMIXED の場合 speaker_id に participantRawID が入る。MIXED や eval だと "unknown"。
    """

    text: str
    speaker_id: str = "unknown"
    offset_ms: int = 0
    duration_ms: int = 0
    is_final: bool = True
    detected_at: datetime = datetime.now(UTC)


class StreamingTranscriber:
    """1 つの participant 音声ストリームに紐付く STT セッション。

    UNMIXED では participant ごとに 1 instance、MIXED では call 全体で 1 instance。
    `participant_id` が認識結果の TranscriptEvent.speaker_id に渡る。

    Lifecycle:
        t = StreamingTranscriber(participant_id="8:orgid:abcd")
        t.start()
        t.push_audio(pcm_bytes)  # 何度でも
        async for event in t.events():
            ...
        t.stop()
    """

    SAMPLE_RATE = 16000  # Hz, ACS unmixed / mixed の標準
    BITS_PER_SAMPLE = 16
    CHANNELS = 1
    LANGUAGE = "ja-JP"

    def __init__(self, *, participant_id: str = "unknown") -> None:
        self.participant_id = participant_id
        self._queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        self._loop = asyncio.get_event_loop()
        self._push_stream = None  # type: ignore[assignment]
        self._recognizer = None  # type: ignore[assignment]
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        settings = get_settings()
        if not (settings.azure_speech_key and settings.azure_speech_region):
            raise RuntimeError("Azure Speech not configured (AZURE_SPEECH_KEY/REGION)")

        # 遅延 import: SDK が重い
        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = self.LANGUAGE

        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=self.SAMPLE_RATE,
            bits_per_sample=self.BITS_PER_SAMPLE,
            channels=self.CHANNELS,
        )
        self._push_stream = speechsdk.audio.PushAudioInputStream(audio_format)
        audio_config = speechsdk.audio.AudioConfig(stream=self._push_stream)
        self._recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        # 認識結果コールバック (SDK は別 thread から呼ぶ → loop に enqueue)
        def _on_recognized(evt: object) -> None:  # noqa: ANN401
            r = evt.result  # type: ignore[attr-defined]
            text = (r.text or "").strip()
            if not text:
                return
            event = TranscriptEvent(
                text=text,
                speaker_id=self.participant_id,
                offset_ms=int(r.offset / 10_000),
                duration_ms=int(r.duration / 10_000),
                is_final=True,
            )
            # asyncio.Queue.put_nowait は thread-safe ではないので loop に submit
            try:
                self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
            except RuntimeError:
                pass  # loop が閉じている

        def _on_canceled(evt: object) -> None:  # noqa: ANN401
            logger.warning("speech.canceled", reason=str(evt))
            try:
                self._loop.call_soon_threadsafe(self._queue.put_nowait, None)
            except RuntimeError:
                pass

        self._recognizer.recognized.connect(_on_recognized)
        self._recognizer.canceled.connect(_on_canceled)
        self._recognizer.start_continuous_recognition_async()
        self._started = True
        logger.info("speech.started", language=self.LANGUAGE)

    def push_audio(self, chunk: bytes) -> None:
        """ACS から届いた raw PCM chunk を SDK に流し込む。"""
        if not self._started or self._push_stream is None:
            return
        try:
            self._push_stream.write(chunk)
        except Exception as e:  # noqa: BLE001
            logger.warning("speech.push_failed", error=str(e), size=len(chunk))

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        """final 認識結果を非同期に yield する。stop() されると終わる。"""
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event

    def stop(self) -> None:
        if not self._started:
            return
        try:
            if self._push_stream is not None:
                self._push_stream.close()
            if self._recognizer is not None:
                self._recognizer.stop_continuous_recognition_async()
        finally:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, None)
            self._started = False
            logger.info("speech.stopped")


def transcript_event_to_utterance(
    *,
    event: TranscriptEvent,
    meeting_id: str,
    speaker_id: str | None = None,
):
    """TranscriptEvent → Utterance (Cosmos / agents 用)。

    speaker_id 引数を渡さなければ event.speaker_id をそのまま使う (UNMIXED 経路)。
    渡された場合 (display name 解決後など) はそれを優先。
    """
    from helmsman.models.utterance import Utterance

    started = event.detected_at
    duration = max(0.5, event.duration_ms / 1000.0)
    return Utterance(
        meeting_id=meeting_id,
        speaker_id=speaker_id or event.speaker_id or "unknown",
        text=event.text,
        started_at=started,
        ended_at=started + timedelta(seconds=duration),
        duration_sec=duration,
        confidence=1.0,
        is_final=event.is_final,
    )
