"""EvalResult を `eval_runs/<timestamp>/` 配下に書き出す。

出力:
  utterances.jsonl     1 行 1 Utterance
  interventions.jsonl  1 行 1 InterventionDelivery (Arbiter が選んだものだけ)
  candidates.jsonl     1 行 1 InterventionCandidate (Arbiter フィルタ前を含む全件)
  ticks.jsonl          1 行 1 TickRecord
  final_meeting.json   Meeting 最終状態
  metrics.json         集計指標 (UI ダッシュボードや CI に流せる形)
  report.md            人間用サマリー
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from helmsman.eval.runner import EvalResult, TickRecord


def write_report(result: EvalResult, out_dir: Path) -> dict:
    """評価結果をディスクに書き出し、metrics.json と同じ dict を返す。"""
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_jsonl(
        out_dir / "utterances.jsonl",
        (u.model_dump(mode="json") for u in result.utterances),
    )
    _write_jsonl(
        out_dir / "interventions.jsonl",
        (d.model_dump(mode="json") for d in result.meeting.delivered_interventions),
    )
    _write_jsonl(
        out_dir / "candidates.jsonl",
        (c.model_dump(mode="json") for c in result.all_candidates),
    )
    _write_jsonl(out_dir / "ticks.jsonl", (_tick_to_dict(t) for t in result.ticks))

    (out_dir / "final_meeting.json").write_text(
        json.dumps(result.meeting.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metrics = _compute_metrics(result)
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    (out_dir / "report.md").write_text(_render_markdown(result, metrics), encoding="utf-8")
    return metrics


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _tick_to_dict(t: TickRecord) -> dict:
    d = asdict(t)
    if t.delivered:
        d["delivered"] = t.delivered.model_dump(mode="json")
    return d


def _compute_metrics(result: EvalResult) -> dict:
    m = result.meeting
    deliveries = m.delivered_interventions
    by_level = Counter(d.level for d in deliveries)
    by_agent = Counter(d.agent for d in deliveries)
    candidate_by_agent = Counter(c.agent for c in result.all_candidates)
    topic_states = Counter(
        (t.state.value if hasattr(t.state, "value") else str(t.state))
        for t in m.topics
    )
    avg_tick_latency = (
        sum(t.tick_latency_sec for t in result.ticks) / len(result.ticks)
        if result.ticks
        else 0.0
    )
    total_words = sum(len(u.text) for u in result.utterances)

    return {
        "audio_duration_sec": round(result.audio_duration_sec, 2),
        "wall_duration_sec": round(result.wall_duration_sec, 2),
        "utterance_count": len(result.utterances),
        "total_text_length": total_words,
        "tick_count": len(result.ticks),
        "avg_tick_latency_sec": round(avg_tick_latency, 3),
        "topics_total": len(m.topics),
        "topic_states": dict(topic_states),
        "delivered_total": len(deliveries),
        "delivered_by_level": dict(by_level),
        "delivered_by_agent": dict(by_agent),
        "candidates_total": len(result.all_candidates),
        "candidates_by_agent": dict(candidate_by_agent),
        "acceptance_rate": (
            round(len(deliveries) / len(result.all_candidates), 3)
            if result.all_candidates
            else 0.0
        ),
        "llm_cost_usd": round(m.usage.total_cost_usd, 6),
        "llm_total_tokens": m.usage.total_tokens,
        "llm_call_count": m.usage.call_count,
        "llm_by_agent": {
            name: round(rollup.cost_usd, 6)
            for name, rollup in m.usage.by_agent.items()
        },
    }


def _render_markdown(result: EvalResult, metrics: dict) -> str:
    m = result.meeting
    lines: list[str] = []

    lines.append("# Helmsman Eval Report")
    lines.append("")
    lines.append(f"- **Generated**: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- **Audio duration**: {metrics['audio_duration_sec']:.1f} sec")
    lines.append(f"- **Wall duration**: {metrics['wall_duration_sec']:.1f} sec")
    lines.append(f"- **Goal**: {m.goal or '(none — monitor mode)'}")
    lines.append(f"- **Mode**: {m.mode}")
    lines.append(f"- **Intensity**: {m.user_intensity}")
    lines.append("")

    lines.append("## Pipeline counts")
    lines.append("")
    lines.append(f"- Utterances: **{metrics['utterance_count']}**")
    lines.append(f"- Ticks fired: **{metrics['tick_count']}**")
    lines.append(f"- Avg tick latency: **{metrics['avg_tick_latency_sec']}** sec")
    lines.append(
        f"- Candidates → Delivered: **{metrics['candidates_total']} → "
        f"{metrics['delivered_total']}** "
        f"(arbiter acceptance {metrics['acceptance_rate'] * 100:.1f} %)"
    )
    lines.append("")

    lines.append("## Topics state")
    lines.append("")
    if not metrics["topic_states"]:
        lines.append("_no topics — monitor mode_")
    else:
        for state, count in sorted(metrics["topic_states"].items()):
            lines.append(f"- {state}: {count}")
    lines.append("")

    lines.append("## Interventions by level")
    lines.append("")
    if not metrics["delivered_by_level"]:
        lines.append("_no interventions delivered_")
    else:
        for level in ("L1", "L2", "L3"):
            count = metrics["delivered_by_level"].get(level, 0)
            lines.append(f"- {level}: **{count}**")
    lines.append("")

    lines.append("## Interventions by agent")
    lines.append("")
    if not metrics["delivered_by_agent"]:
        lines.append("_none_")
    else:
        for agent, count in sorted(
            metrics["delivered_by_agent"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"- {agent}: {count}")
    lines.append("")

    lines.append("## LLM cost")
    lines.append("")
    lines.append(f"- Total: **${metrics['llm_cost_usd']:.4f}**")
    lines.append(f"- Tokens: {metrics['llm_total_tokens']:,}")
    lines.append(f"- Calls: {metrics['llm_call_count']}")
    if metrics["llm_by_agent"]:
        lines.append("")
        lines.append("Per-agent cost:")
        for agent, cost in sorted(
            metrics["llm_by_agent"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"  - {agent}: ${cost:.6f}")
    lines.append("")

    lines.append("## Delivered interventions (chronological)")
    lines.append("")
    if not m.delivered_interventions:
        lines.append("_none_")
    else:
        for d in m.delivered_interventions:
            ts = d.delivered_at.strftime("%H:%M:%S") if d.delivered_at else "—"
            lines.append(f"- `{ts}` **{d.level}** [{d.agent}] {d.content}")
            if d.evidence_quote:
                lines.append(f"  - 引用: 「{d.evidence_quote}」")
    lines.append("")

    return "\n".join(lines)
