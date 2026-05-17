"""Azure Speech TTS で日本語介入音声を生成 → ACS 双方向 WebSocket で会議に流す。

ACS Call Automation の `play_media` REST API は Cognitive Services Direct Connection
が必要で設定が重い。ここでは Speech SDK で raw PCM を作って、bidirectional Media
Streaming WebSocket に base64 で送り込む方式。
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import TYPE_CHECKING

from helmsman.core.config import get_settings
from helmsman.core.logging import logger

if TYPE_CHECKING:
    from fastapi import WebSocket

# ACS Media Streaming は 16 kHz / 16-bit / mono PCM 固定
TTS_VOICE = "ja-JP-NanamiNeural"
PCM_FORMAT_SAMPLES_PER_SEC = 16000
PCM_CHUNK_MS = 20  # ACS 推奨 20ms フレーム
PCM_CHUNK_BYTES = int(PCM_FORMAT_SAMPLES_PER_SEC * (PCM_CHUNK_MS / 1000) * 2)  # 640 bytes


async def synthesize_pcm(text: str) -> bytes:
    """テキストを 16kHz/16bit/mono raw PCM bytes に変換。

    Speech SDK は sync API なので thread に逃がす。
    """
    settings = get_settings()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        raise RuntimeError("Azure Speech not configured")

    def _sync_synthesize() -> bytes:
        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_synthesis_voice_name = TTS_VOICE
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        # audio_config=None → 返り値の audio_data に raw PCM が乗る
        synth = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=None
        )
        result = synth.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details  # type: ignore[attr-defined]
            raise RuntimeError(f"TTS canceled: {details.reason} {details.error_details}")
        raise RuntimeError(f"TTS failed: {result.reason}")

    return await asyncio.to_thread(_sync_synthesize)


async def play_pcm_into_websocket(
    websocket: "WebSocket", pcm: bytes, *, real_time: bool = True
) -> None:
    """PCM bytes を ACS bidirectional WebSocket に base64 で流す。

    real_time=True なら 20ms ごとに送って実時間で再生される (会議で自然に聞こえる)。
    False なら速攻でバッファに詰めて ACS 側でバッファリングさせる (短いプロンプト向き)。
    """
    if not pcm:
        return

    total_frames = (len(pcm) + PCM_CHUNK_BYTES - 1) // PCM_CHUNK_BYTES
    sleep_interval = (PCM_CHUNK_MS / 1000) if real_time else 0

    for i in range(0, len(pcm), PCM_CHUNK_BYTES):
        chunk = pcm[i : i + PCM_CHUNK_BYTES]
        # 末尾フレームは zero-pad
        if len(chunk) < PCM_CHUNK_BYTES:
            chunk = chunk + b"\x00" * (PCM_CHUNK_BYTES - len(chunk))

        payload = {
            "kind": "AudioData",
            "audioData": {
                "data": base64.b64encode(chunk).decode("ascii"),
            },
            "stopAudio": None,
        }
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:  # noqa: BLE001
            logger.warning("tts.send_failed", error=str(e))
            return
        if sleep_interval > 0:
            await asyncio.sleep(sleep_interval)

    logger.info("tts.played", text_bytes=len(pcm), frames=total_frames)


async def speak_into_call(websocket: "WebSocket", text: str) -> None:
    """テキストを TTS → 会議に音声として流す (Phase C のメイン入口)。"""
    if not text.strip():
        return
    try:
        pcm = await synthesize_pcm(text)
    except Exception as e:  # noqa: BLE001
        logger.error("tts.synth_failed", error=str(e), text=text[:80])
        return
    logger.info("tts.start_play", text=text[:80], bytes=len(pcm))
    await play_pcm_into_websocket(websocket, pcm, real_time=True)
