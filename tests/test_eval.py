"""オフライン eval ハーネスの smoke。LLM 呼び出しをモックして
runner の orchestration + report 出力をパス含めて検証する。
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from helmsman.agents import (
    CoverageTracker,
    DecisionCapture,
    DissentSurface,
    GoalDecomposer,
    QuietActivator,
    SteeringAgent,
)
from helmsman.eval.audio import (
    FfmpegMissingError,
    TranscriptLine,
    _line_to_utterance,
    convert_to_wav_16k_mono,
)
from helmsman.eval.report import write_report
from helmsman.eval.runner import run_eval
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import MeetingMode, UserIntensity
from helmsman.models.topic import Topic, TopicPriority, TopicState


def _utterance(text: str, speaker: str = "alice", duration: float = 4.0):
    line = TranscriptLine(
        text=text, speaker_id=speaker, offset_sec=0.0, duration_sec=duration
    )
    return _line_to_utterance(line, meeting_id="eval", speaker_resolver=None)


async def _stream(utterances):
    for u in utterances:
        yield u


@pytest.mark.asyncio
async def test_run_eval_orchestrates_and_writes_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch every agent _chat_json to return minimal valid fixtures.
    fake_topic = Topic(
        id="t1",
        name="価格戦略",
        decision_criteria="GP 30% 以上",
        time_budget_pct=50.0,
        priority=TopicPriority.CRITICAL,
        dependencies=[],
        state=TopicState.NOT_STARTED,
    )

    monkeypatch.setattr(
        GoalDecomposer,
        "_chat_json",
        AsyncMock(
            return_value={
                "topics": [
                    {
                        "id": fake_topic.id,
                        "name": fake_topic.name,
                        "decision_criteria": fake_topic.decision_criteria,
                        "time_budget_pct": fake_topic.time_budget_pct,
                        "priority": fake_topic.priority.value,
                        "dependencies": [],
                    }
                ]
            }
        ),
    )

    monkeypatch.setattr(
        CoverageTracker,
        "_chat_json",
        AsyncMock(
            return_value={
                "topics": [
                    {
                        "id": fake_topic.id,
                        "state": "discussing",
                        "evidence_quote": "価格について議論しています",
                        "confidence": 0.8,
                        "key_speakers": ["alice"],
                        "document_reference": None,
                    }
                ]
            }
        ),
    )

    # Steering: off-topic 検知なし
    monkeypatch.setattr(
        SteeringAgent, "_chat_json", AsyncMock(return_value={"off_topic": False})
    )

    # DecisionCapture: 何も決まらず
    monkeypatch.setattr(
        DecisionCapture,
        "_chat_json",
        AsyncMock(return_value={"decided": False}),
    )

    # Quiet: 活性化候補なし
    monkeypatch.setattr(
        QuietActivator,
        "_chat_json",
        AsyncMock(return_value={"target_id": None}),
    )

    # Dissent: 同意連鎖検知なし
    monkeypatch.setattr(
        DissentSurface,
        "_chat_json",
        AsyncMock(return_value={"detected": False}),
    )

    utterances = [
        _utterance("価格はいくらにすべきでしょうか"),
        _utterance("私は 5000 円が妥当だと思います", "bob"),
        _utterance("競合は 4000 円なので少し下げたい", "alice"),
    ]

    result = await run_eval(
        _stream(utterances),
        goal="価格戦略を決定する",
        mode=MeetingMode.DECISION,
        intensity=UserIntensity.NORMAL,
        total_minutes=60,
        tick_every_sec=2.0,  # 短くして tick が複数回回るように
        audio_duration_sec=12.0,
    )

    # 基本構造
    assert len(result.utterances) == 3
    assert len(result.ticks) >= 1
    assert result.meeting.goal == "価格戦略を決定する"
    assert len(result.meeting.topics) == 1
    assert result.meeting.topics[0].name == "価格戦略"

    # レポート出力
    out_dir = tmp_path / "run-1"
    write_report(result, out_dir)

    for filename in (
        "utterances.jsonl",
        "interventions.jsonl",
        "candidates.jsonl",
        "ticks.jsonl",
        "final_meeting.json",
        "metrics.json",
        "report.md",
    ):
        assert (out_dir / filename).exists(), f"missing {filename}"

    # 内容スポットチェック
    utter_lines = (
        (out_dir / "utterances.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(utter_lines) == 3

    metrics_disk = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics_disk["utterance_count"] == 3
    assert metrics_disk["tick_count"] >= 1
    assert "topic_states" in metrics_disk

    md = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "Helmsman Eval Report" in md
    assert "価格戦略" in md or "Pipeline counts" in md  # トピック or セクション


@pytest.mark.asyncio
async def test_run_eval_handles_no_goal_monitor_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """goal が空でも crash しない (GoalDecomposer を呼ばない監視モード)。"""
    monkeypatch.setattr(
        CoverageTracker, "_chat_json", AsyncMock(return_value={"topics": []})
    )
    monkeypatch.setattr(
        SteeringAgent, "_chat_json", AsyncMock(return_value={"off_topic": False})
    )
    monkeypatch.setattr(
        DecisionCapture, "_chat_json", AsyncMock(return_value={"decided": False})
    )
    monkeypatch.setattr(
        QuietActivator, "_chat_json", AsyncMock(return_value={"target_id": None})
    )
    monkeypatch.setattr(
        DissentSurface, "_chat_json", AsyncMock(return_value={"detected": False})
    )

    utterances = [_utterance("おはようございます")]
    result = await run_eval(
        _stream(utterances),
        goal="",
        tick_every_sec=0.5,
    )
    assert result.meeting.topics == []
    assert len(result.utterances) == 1


def test_convert_to_wav_passthrough_for_wav(tmp_path: Path) -> None:
    """既に .wav なら ffmpeg を呼ばずそのまま返す。"""
    wav = tmp_path / "already.wav"
    wav.write_bytes(b"RIFF__fake__")
    assert convert_to_wav_16k_mono(wav) == wav


def test_convert_to_wav_raises_when_ffmpeg_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ffmpeg が PATH にない場合は明示エラーで失敗 (silent corruption を避ける)。"""
    monkeypatch.setattr("helmsman.eval.audio._ffmpeg_available", lambda: False)
    mp3 = tmp_path / "meeting.mp3"
    mp3.write_bytes(b"\x00fake mp3")
    with pytest.raises(FfmpegMissingError):
        convert_to_wav_16k_mono(mp3)


def test_intervention_candidates_serialize_in_report(tmp_path: Path) -> None:
    """all_candidates が JSONL に正しく書き出されるか。"""
    from helmsman.eval.runner import EvalResult
    from helmsman.models.meeting import Meeting

    meeting = Meeting(organizer_id="eval", goal="test")
    candidate = InterventionCandidate(
        meeting_id=meeting.id,
        agent="SteeringAgent",
        content="話を戻しましょう",
        reason="off-topic",
        evidence_quote=None,
        confidence=0.9,
        allowed_modes=[MeetingMode.DECISION.value],
    )
    result = EvalResult(
        meeting=meeting,
        utterances=[],
        ticks=[],
        all_candidates=[candidate],
        audio_duration_sec=0.0,
    )

    write_report(result, tmp_path)

    cand_text = (tmp_path / "candidates.jsonl").read_text(encoding="utf-8").strip()
    assert "SteeringAgent" in cand_text
    assert "話を戻しましょう" in cand_text
