"""Microsoft Graph recordResponse の WAV を Azure Speech で文字化して
既存 CallSession に utterance として流す (M.C2)。

フロー:
1. webhook で recordingLocation + recordingAccessToken を受ける
2. WAV を Authorization: Bearer でダウンロード
3. Azure Speech SDK の recognize_once_async で文字化 (batch)
4. CallSession.utterances に append + maybe_trigger_tick で agent pipeline 起動

CallSession は call_buffer の get_or_create でリサイクル (ACS 時代と同じ shape)。
"""
from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.models.utterance import Utterance
from helmsman.services.call_buffer import get_call_registry
from helmsman.services.call_tick import maybe_trigger_tick


async def _download_wav(url: str, access_token: str | None) -> bytes | None:
    """recording URL から WAV bytes を取得。auth token があれば Bearer 付与。"""
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "stt.download_failed",
                    url=url[:80],
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return None
            return resp.content
    except httpx.HTTPError as e:
        logger.warning("stt.download_error", url=url[:80], error=str(e))
        return None


# 日本語ビジネス会議で頻出する固有名詞 + 業務用語を Speech SDK に hint として渡す。
# PhraseListGrammar に登録すると、認識候補のスコアリングで優先される。
# 出典: 月次ビジネスレビュー想定 (リリース判定 / QA / マーケ / deep dive 議題 等)。
_JA_PHRASE_HINTS = [
    # 製品/業務カタカナ語 (STT の鬼門)
    "Q4", "Q3", "Q2", "Q1",
    "ロードマップ", "ロードプラン",
    "ローンチ", "プロダクトレビュー",
    "QA", "QA 期間", "テストカバレッジ", "smoke test", "スモークテスト",
    "プライシング", "月額", "年額",
    "マーケキャンペーン", "アンバサダー連携", "メディア配信",
    "ランディング", "クリエイティブ",
    "deep dive", "ディープダイブ",
    "パフォーマンスチューニング", "海外展開",
    "グロース", "ROI", "CV", "KPI",
    "ユーザーリサーチ",
    # 意思決定語彙
    "撤退ライン", "リリース判定",
    "クリティカル失敗", "致命的バグ", "致命バグ",
    "スコープ縮小", "巻きで進める",
    "確定", "承知しました",
    # 人名 (デモ fixture)
    "山田", "佐藤", "高橋", "中村", "鈴木",
    "山田 CTO", "佐藤 PM", "高橋 リード",
    # ファシリテーター名
    "Helmsman", "ヘルムスマン",
]


def _recognize_wav_sync(wav_bytes: bytes, language: str = "ja-JP") -> str | None:
    """同期 Azure Speech SDK で WAV bytes を文字化 (batch)。重いので executor 経由で呼ぶ。

    PhraseListGrammar に日本語ビジネス会議の頻出語彙を hint として渡し、
    固有名詞・業務用語の認識精度を向上させる。
    """
    settings = get_settings()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        logger.warning("stt.speech_not_configured")
        return None

    # SDK は file path を要求するので一時ファイル経由
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = language
        audio_config = speechsdk.audio.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        # phrase hints を登録 (ja-JP 認識の精度向上)
        phrase_list = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
        for phrase in _JA_PHRASE_HINTS:
            phrase_list.addPhrase(phrase)

        result = recognizer.recognize_once()
        reason = result.reason
        if reason == speechsdk.ResultReason.RecognizedSpeech:
            text = (result.text or "").strip()
            return text or None
        if reason == speechsdk.ResultReason.NoMatch:
            return None
        # Canceled
        if reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.CancellationDetails.from_result(result)
            logger.warning(
                "stt.canceled",
                reason=str(cancellation.reason),
                details=(cancellation.error_details or "")[:200],
            )
            return None
        return None
    except Exception as e:  # noqa: BLE001
        logger.error("stt.recognize_failed", error=str(e), error_type=type(e).__name__)
        return None
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


async def transcribe_and_dispatch(
    *,
    call_id: str,
    meeting_id: str,
    organizer_id: str,
    recording_url: str,
    access_token: str | None,
) -> None:
    """1 chunk の録音を download → STT → CallSession に utterance として追加 → tick 起動。"""
    wav_bytes = await _download_wav(recording_url, access_token)
    if not wav_bytes:
        return
    logger.info("stt.wav_downloaded", call_id=call_id, bytes=len(wav_bytes))

    # 重い処理は executor 経由
    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _recognize_wav_sync, wav_bytes)
    if not text:
        logger.info("stt.empty_result", call_id=call_id)
        return

    logger.info("stt.recognized", call_id=call_id, text=text[:100])

    # CallSession に utterance として追加
    registry = get_call_registry()
    session = await registry.get_or_create(
        call_connection_id=call_id,
        meeting_id=meeting_id,
        organizer_id=organizer_id,
    )
    now = datetime.now(UTC)
    # Graph では participant 識別は未実装、参加者まとめて "participant" にする
    utterance = Utterance(
        meeting_id=meeting_id,
        speaker_id="participant",
        text=text,
        started_at=now,
        ended_at=now,
        duration_sec=10.0,  # CHUNK_DURATION_SEC 相当
        confidence=1.0,
        is_final=True,
    )
    session.utterances.append(utterance)
    session.pending_since_last_tick += 1

    # 一定数溜まったら tick 発火
    if session.pending_since_last_tick >= 1:  # まずは 1 件で発火 (デモ向け、後で調整)
        await maybe_trigger_tick(session)
