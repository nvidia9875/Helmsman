"""In-process per-call utterance buffer + auto-tick orchestration.

ACS Media Stream の WebSocket が生きている間、その call_connection_id に対する
バッファとトランスクライバーを保持する。発言が貯まったら自動で /tick を発火し、
8 agents の分析を回す。

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


@dataclass
class CallSession:
    call_connection_id: str
    meeting_id: str
    organizer_id: str
    transcriber: StreamingTranscriber = field(default_factory=StreamingTranscriber)
    utterances: list[Utterance] = field(default_factory=list)
    pending_since_last_tick: int = 0
    last_tick_at: float | None = None
    consumer_task: asyncio.Task | None = None
    ticker_task: asyncio.Task | None = None
    # bidirectional Media Streaming で TTS を会議に流すための WebSocket 参照
    media_ws: WebSocket | None = None


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
            session.transcriber.stop()
            for t in (session.consumer_task, session.ticker_task):
                if t and not t.done():
                    t.cancel()
            logger.info("call.session_dropped", call_id=call_connection_id)

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


async def start_session_consumer(session: CallSession) -> None:
    """transcriber から流れてくる TranscriptEvent を Utterance に変換してバッファに積む。

    バッファが TICK_AFTER_NEW_UTTERANCES 件に達すると、Meeting 用の tick を
    別 task で発火する。
    """
    from helmsman.services.call_tick import maybe_trigger_tick

    try:
        async for ev in session.transcriber.events():
            utterance = transcript_event_to_utterance(
                event=ev, meeting_id=session.meeting_id
            )
            session.utterances.append(utterance)
            session.pending_since_last_tick += 1
            logger.info(
                "call.utterance",
                meeting_id=session.meeting_id,
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
