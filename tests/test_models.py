"""Domain model invariants."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from helmsman.models import Document, Meeting, MeetingMode, Topic, TopicPriority


def test_meeting_time_remaining_before_start():
    m = Meeting(organizer_id="u", goal="x")
    assert m.time_remaining_pct == 1.0


def test_meeting_time_remaining_half_way():
    m = Meeting(
        organizer_id="u", goal="x", total_minutes=60,
        started_at=datetime.now(UTC) - timedelta(minutes=30),
    )
    assert 0.45 < m.time_remaining_pct < 0.55


def test_meeting_time_remaining_clamped_at_zero():
    m = Meeting(
        organizer_id="u", goal="x", total_minutes=10,
        started_at=datetime.now(UTC) - timedelta(minutes=30),
    )
    assert m.time_remaining_pct == 0.0


def test_meeting_continuity_fields_default_empty():
    m = Meeting(organizer_id="u", goal="x")
    assert m.parent_meeting_id is None
    assert m.series_id is None
    assert m.series_index is None
    assert m.inherited_topic_ids == []


def test_topic_default_state():
    t = Topic(name="t", decision_criteria="c", time_budget_pct=20)
    assert t.state.value == "not_started"
    assert t.priority == TopicPriority.IMPORTANT
    assert t.confidence == 0.0


def test_document_status_lifecycle():
    d = Document(
        meeting_id="m1",
        filename="spec.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        blob_path="m1/d1/spec.pdf",
        uploaded_by="u1",
    )
    assert d.status.value == "uploaded"
    assert d.chunk_count == 0
    assert d.extracted_text is None


def test_meeting_mode_serializes_to_value():
    m = Meeting(organizer_id="u", goal="x", mode=MeetingMode.BRAINSTORM)
    dumped = m.model_dump(mode="json")
    assert dumped["mode"] == "Brainstorm"
