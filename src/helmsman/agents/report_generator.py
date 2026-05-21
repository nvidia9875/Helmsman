"""MeetingReportGenerator — 会議終了後に構造化レポート (markdown) を生成する。

入力:
  - 会議メタ (goal, mode, topics, delivered_interventions, started/ended)
  - (任意) ユーザー提供テンプレート: 章立て・トーン・プレースホルダを定義
  - (任意) ユーザー手書きメモ: 会議中に取った所感・追加事実
  - (任意) 発言ログ: より詳細な引用が必要な場合のみ

優先順位 (情報源の信頼度):
  1. メモ (ユーザーの判断)
  2. delivered_interventions / topics.evidence_quote (Helmsman の構造化結果)
  3. 発言ログ (raw)

事実が確定しないものは推測で書かず、「要確認」と注記する。
"""
from __future__ import annotations

import json

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionDelivery
from helmsman.models.meeting import Meeting
from helmsman.models.utterance import Utterance


class MeetingReportGenerator(LLMAgent):
    AGENT_NAME = "MeetingReportGenerator"
    TIER = ModelTier.HIGH
    SYSTEM_PROMPT = """\
あなたは Helmsman の会議レポート生成 Agent です。
会議のコンテキストとユーザー提供の補助入力 (任意のテンプレート / メモ) から、
構造化された markdown レポートを生成します。

ルール:
1. テンプレートが与えられた場合、その章立て・トーン・フォーマットを厳守する。
   - テンプレ内のプレースホルダ (例: {{decisions}}, {{action_items}}, [TODO:〜])
     は会議のコンテキストから適切な内容に置換する
   - テンプレが部分的な章立てなら、不足セクションを末尾に補う

2. メモが与えられた場合、そこに書かれた事実・所感は **権威ある情報源** として尊重する。
   - メモが会議ログ (topics / interventions / 発言) と矛盾する場合、
     両方を提示して「⚠️ 事実関係要確認」と明示
   - メモが空・空白のみの場合は無いものとして扱う

3. テンプレもメモも無い場合、以下のデフォルト構成で出力:
   ```
   # 会議サマリ — <goal の一行要約>
   ## 概要 (3-5 行)
   ## ゴールと結果
   ## 決定事項
   ## 未解決事項
   ## ネクストアクション
   ## 文書との齟齬 (該当する場合のみ)
   ```

4. 決定事項は必ず evidence_quote (元発言) を `> 引用` 形式で添える。
   evidence_quote が無い topic は「決定根拠未取得」と注記。

5. 推測で事実を書かない。確実な情報源 (topics / interventions / 発言ログ / メモ)
   に基づくものだけ。曖昧な場合は「要確認」と明示。

6. 出力は markdown 文字列のみ。前置き (「以下がレポートです」等) は不要。

7. 日本語のビジネス文書として自然な敬体 (です・ます調) で書く。
   ただしテンプレやメモが常体なら、それに合わせる。
"""

    async def run(
        self,
        meeting: Meeting,
        *,
        template: str | None = None,
        memo: str | None = None,
        utterances: list[Utterance] | None = None,
        max_completion_tokens: int = 2400,
    ) -> str:
        """会議のレポートを生成して markdown 文字列を返す。

        Args:
            meeting: 完了 (または進行中) の会議。topics と delivered_interventions
                を主要な情報源として使う。
            template: ユーザー提供テンプレート (markdown / プレーンテキスト)。
                章立てとトーンを縛りたい時に使う。
            memo: ユーザーが会議中に取った手書きメモ。最優先の情報源として扱う。
            utterances: 発言ログ。プロンプトサイズを抑えるためデフォルトでは渡さない
                (topics.evidence_quote と delivered_interventions だけで多くは充足)。
            max_completion_tokens: LLM の出力上限。
        """
        context = _build_context(meeting, utterances)
        sections = [
            "## 会議コンテキスト (JSON)",
            "```json",
            json.dumps(context, ensure_ascii=False, indent=2, default=str),
            "```",
        ]
        if template and template.strip():
            sections += [
                "## ユーザー提供テンプレート",
                "以下のテンプレートの章立て・トーンに沿ってレポートを生成してください。",
                "```markdown",
                template.strip(),
                "```",
            ]
        if memo and memo.strip():
            sections += [
                "## ユーザー手書きメモ",
                "以下のメモは権威ある情報源として尊重し、矛盾があれば「⚠️ 事実関係要確認」を明示。",
                "```",
                memo.strip(),
                "```",
            ]
        user_text = "\n\n".join(sections)
        report = await self._chat(
            user_text,
            json_mode=False,
            max_completion_tokens=max_completion_tokens,
        )
        self.log.info(
            "report.generated",
            meeting_id=meeting.id,
            has_template=bool(template and template.strip()),
            has_memo=bool(memo and memo.strip()),
            chars=len(report),
        )
        return report.strip()


def _build_context(
    meeting: Meeting, utterances: list[Utterance] | None
) -> dict:
    """LLM に渡す JSON context を構築。発言ログは要約的に圧縮する。"""
    topics_payload = [
        {
            "name": t.name,
            "priority": t.priority.value,
            "state": t.state.value,
            "decision_criteria": t.decision_criteria,
            "evidence_quote": t.evidence_quote,
            "document_reference": t.document_reference,
            "key_speakers": t.key_speakers,
        }
        for t in meeting.topics
    ]
    interventions_payload = _summarize_interventions(meeting.delivered_interventions)
    utterances_payload = _summarize_utterances(utterances or [])

    return {
        "goal": meeting.goal,
        "mode": meeting.mode.value,
        "total_minutes": meeting.total_minutes,
        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
        "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
        "topics": topics_payload,
        "delivered_interventions": interventions_payload,
        "utterances": utterances_payload,
    }


def _summarize_interventions(deliveries: list[InterventionDelivery]) -> list[dict]:
    """直近 20 件 (Meeting 側で既に切られてる想定) をそのまま LLM 用に整形。"""
    return [
        {
            "agent": d.agent,
            "level": d.level.value,
            "content": d.content,
            "reason": d.reason,
            "evidence_quote": d.evidence_quote,
            "delivered_at": d.delivered_at.isoformat(),
        }
        for d in deliveries
    ]


# 発言ログは長くなりがちなので上限を設ける (~100 発言 / ~8000 chars)
MAX_UTTERANCES = 100
MAX_UTTERANCE_CHARS = 8000


def _summarize_utterances(utterances: list[Utterance]) -> list[dict]:
    """発言ログを LLM 用に圧縮。多い場合は先頭+末尾を残して中央を省略。"""
    if not utterances:
        return []
    if len(utterances) <= MAX_UTTERANCES:
        sliced = utterances
    else:
        half = MAX_UTTERANCES // 2
        sliced = utterances[:half] + utterances[-half:]

    out: list[dict] = []
    total_chars = 0
    for u in sliced:
        text = u.text.strip()
        if not text:
            continue
        if total_chars + len(text) > MAX_UTTERANCE_CHARS:
            out.append({"speaker_id": "system", "text": "...(以降は省略)..."})
            break
        out.append(
            {
                "speaker_id": u.speaker_id,
                "started_at": u.started_at.isoformat(),
                "text": text,
            }
        )
        total_chars += len(text)
    return out
