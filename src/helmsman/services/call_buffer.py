"""In-process per-call utterance buffer + auto-tick orchestration.

ACS Media Stream の WebSocket が生きている間、その call_connection_id に対する
バッファとトランスクライバーを保持する。発言が貯まったら自動で /tick を発火し、
8 agents の分析を回す。

**UNMIXED モード**: 参加者ごとに 1 つの StreamingTranscriber を持ち、
participantRawID で speaker_id をタグする。声紋識別は不要。

Container App の単一プロセス内で動く前提 (multi-replica 化したら redis 化必須)。
Phase B MVP として割り切る。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from helmsman.core.logging import logger
from helmsman.services.realtime_transcription import (
    StreamingTranscriber,
    transcript_event_to_utterance,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from helmsman.models.utterance import Utterance

# 自動 tick の発火条件
TICK_AFTER_NEW_UTTERANCES = 3
TICK_INTERVAL_SECONDS = 20.0  # 発言が来ていなくても定期 tick (TimeKeeper のため)

# UNMIXED で participant_id が不明な時の fallback
UNKNOWN_PARTICIPANT_ID = "unknown"


@dataclass
class CallSession:
    """1 つの ACS 通話 (= 1 Teams 会議) に紐付くセッション状態。

    UNMIXED モードでは `transcribers` に participant ごとの STT が並ぶ。
    `participants_by_raw_id` は participantRawID → display name の解決キャッシュ
    (まだ呼ばれていない場合は空、後で list_participants() で埋める)。
    """

    call_connection_id: str
    meeting_id: str
    organizer_id: str

    transcribers: dict[str, StreamingTranscriber] = field(default_factory=dict)
    consumer_tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    participants_by_raw_id: dict[str, str] = field(default_factory=dict)

    utterances: list[Utterance] = field(default_factory=list)
    pending_since_last_tick: int = 0
    last_tick_at: float | None = None
    ticker_task: asyncio.Task | None = None
    # bidirectional Media Streaming で TTS を会議に流すための WebSocket 参照
    media_ws: WebSocket | None = None

    def display_name_for(self, participant_id: str) -> str:
        """participantRawID から表示名を解決。未解決なら ID をそのまま返す。"""
        return self.participants_by_raw_id.get(participant_id, participant_id)


class CallRegistry:
    """call_connection_id → CallSession の in-memory ストア。"""

    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self, *, call_connection_id: str, meeting_id: str, organizer_id: str
    ) -> CallSession:
        async with self._lock:
            session = self._sessions.get(call_connection_id)
            if session is None:
                session = CallSession(
                    call_connection_id=call_connection_id,
                    meeting_id=meeting_id,
                    organizer_id=organizer_id,
                )
                self._sessions[call_connection_id] = session
                logger.info("call.session_created", call_id=call_connection_id)
            return session

    async def drop(self, call_connection_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(call_connection_id, None)
        if session:
            for t in session.transcribers.values():
                try:
                    t.stop()
                except Exception:  # noqa: BLE001
                    pass
            for task in (
                *session.consumer_tasks.values(),
                session.ticker_task,
            ):
                if task and not task.done():
                    task.cancel()
            logger.info(
                "call.session_dropped",
                call_id=call_connection_id,
                transcribers=len(session.transcribers),
            )

    async def lookup_by_meeting(
        self, meeting_id: str
    ) -> CallSession | None:
        async with self._lock:
            for s in self._sessions.values():
                if s.meeting_id == meeting_id:
                    return s
            return None


_registry = CallRegistry()


def get_call_registry() -> CallRegistry:
    return _registry


def get_or_create_transcriber(
    session: CallSession, *, participant_id: str
) -> tuple[StreamingTranscriber, bool]:
    """participant_id 用 STT を返す。なければ新規作成 (start() 済)。

    Returns:
      (transcriber, is_new): is_new=True なら呼び出し側で consumer task を起こす。
    """
    existing = session.transcribers.get(participant_id)
    if existing is not None:
        return existing, False

    t = StreamingTranscriber(participant_id=participant_id)
    try:
        t.start()
    except RuntimeError as e:
        logger.error(
            "call.transcriber_start_failed",
            participant_id=participant_id,
            error=str(e),
        )
        raise
    session.transcribers[participant_id] = t
    logger.info(
        "call.transcriber_created",
        call_id=session.call_connection_id,
        participant_id=participant_id,
        total_transcribers=len(session.transcribers),
    )
    return t, True


async def start_transcriber_consumer(
    session: CallSession, transcriber: StreamingTranscriber
) -> None:
    """1 つの transcriber から流れる TranscriptEvent を Utterance に変換してバッファに積む。

    バッファが TICK_AFTER_NEW_UTTERANCES 件に達すると tick を発火。
    複数の participant transcriber が並列で同じ session.utterances に append するので、
    順序は到着順 (= ほぼ発話順)。
    """
    from helmsman.services.call_tick import maybe_trigger_tick

    try:
        async for ev in transcriber.events():
            # display name に解決できればそれを、なければ ID をそのまま speaker_id に
            resolved = session.display_name_for(ev.speaker_id)
            utterance = transcript_event_to_utterance(
                event=ev,
                meeting_id=session.meeting_id,
                speaker_id=resolved,
            )
            session.utterances.append(utterance)
            session.pending_since_last_tick += 1
            logger.info(
                "call.utterance",
                meeting_id=session.meeting_id,
                speaker=resolved,
                text=utterance.text[:80],
                pending=session.pending_since_last_tick,
            )
            if session.pending_since_last_tick >= TICK_AFTER_NEW_UTTERANCES:
                await maybe_trigger_tick(session)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(
            "call.consumer_failed",
            call_id=session.call_connection_id,
            participant_id=transcriber.participant_id,
            error=str(e),
        )


async def start_session_ticker(session: CallSession) -> None:
    """発言が来ていなくても TICK_INTERVAL_SECONDS おきに tick を回す (TimeKeeper 用)。"""
    from helmsman.services.call_tick import maybe_trigger_tick

    try:
        while True:
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
            await maybe_trigger_tick(session, force=True)
    except asyncio.CancelledError:
        raise
