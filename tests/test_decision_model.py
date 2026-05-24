"""Decision model invariants — Phase 7 (会議横断記憶) の基底単体テスト。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from helmsman.models.decision import Decision


def test_make_id_is_deterministic():
    """同一 meeting + topic で生成される ID が安定 (upsert キー)。"""
    a = Decision.make_id("m1", "t1")
    b = Decision.make_id("m1", "t1")
    assert a == b == "m1:t1"


def test_make_id_differs_per_topic():
    assert Decision.make_id("m1", "t1") != Decision.make_id("m1", "t2")


def test_build_embed_text_fixed_order():
    """順序固定により表現差で別ベクトルになるノイズを抑える。"""
    a = Decision.build_embed_text(
        topic_name="価格", decision_text="¥1200/月で進める",
        owner="田中", evidence_quote="では1200で",
    )
    b = Decision.build_embed_text(
        topic_name="価格", decision_text="¥1200/月で進める",
        owner="田中", evidence_quote="では1200で",
    )
    assert a == b
    assert "価格" in a
    assert "1200" in a
    assert "田中" in a


def test_build_embed_text_omits_blank_fields():
    text = Decision.build_embed_text(
        topic_name="価格", decision_text="¥1200/月",
        owner="", evidence_quote=None,
    )
    assert "担当:" not in text
    assert "根拠:" not in text


def test_minimal_decision_validates():
    d = Decision(
        id="m1:t1",
        organizer_id="u",
        meeting_id="m1",
        topic_id="t1",
        topic_name="価格",
        decision_text="¥1200/月で進める",
    )
    assert d.confidence == 0.0
    assert d.embedding is None
    assert d.dissent == []
    assert d.series_id is None


def test_touch_updates_timestamp():
    d = Decision(
        id="m1:t1",
        organizer_id="u",
        meeting_id="m1",
        topic_id="t1",
        topic_name="価格",
        decision_text="¥1200/月",
    )
    original = d.updated_at
    # 確実に差が出るよう少し過去にしておく
    d.updated_at = datetime.now(UTC) - timedelta(seconds=5)
    d.touch()
    assert d.updated_at > original - timedelta(seconds=10)


def test_decision_text_required():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Decision(
            id="m1:t1",
            organizer_id="u",
            meeting_id="m1",
            topic_id="t1",
            topic_name="価格",
            decision_text="",  # min_length=1
        )


def test_decision_serializes_to_json_safely():
    d = Decision(
        id="m1:t1",
        organizer_id="u",
        meeting_id="m1",
        topic_id="t1",
        topic_name="価格",
        decision_text="¥1200/月",
        embedding=[0.1, 0.2, 0.3],
    )
    dumped = d.model_dump(mode="json")
    assert dumped["id"] == "m1:t1"
    assert dumped["embedding"] == [0.1, 0.2, 0.3]
    # captured_at が ISO 8601 文字列に変換されている (Cosmos 互換)
    assert isinstance(dumped["captured_at"], str)
