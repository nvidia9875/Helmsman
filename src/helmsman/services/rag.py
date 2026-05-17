"""RAG リトリーバル — 会議の goal から参考文書抜粋を取得する。

優先パス:
  1. AI Search (索引化済の場合): goal を embedding → ベクトル検索
  2. フォールバック: Cosmos の document.extracted_text を先頭から拾い、結合
"""
from __future__ import annotations

from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.repositories.documents import DocumentRepository
from helmsman.services.embeddings import embed_texts
from helmsman.services.search_index import search_meeting_chunks

# プロンプトに注入する抜粋の合計上限 (文字数)
MAX_EXCERPT_CHARS = 6000


async def retrieve_excerpts_for_goal(
    *,
    meeting_id: str,
    goal: str,
    repo: DocumentRepository,
    top_k: int = 6,
    usage_sink: MeetingUsage | None = None,
) -> str:
    """会議の goal をクエリに参考文書抜粋テキストを作る。

    AI Search が使えない / 未索引の文書しかない場合は extracted_text を
    そのまま結合する。返り値は GoalDecomposer.run(document_excerpts=...) に渡せる
    フォーマット済みテキスト (空文字なら呼び出し側でスキップ)。
    """
    documents = await repo.list_by_meeting(meeting_id)
    if not documents:
        return ""

    # まず Search を試す (embed → ベクトル検索)
    try:
        vectors, usage = await embed_texts([goal])
        if usage and usage_sink is not None:
            usage_sink.apply(usage, calculate_cost_usd(usage))
        if vectors:
            hits = await search_meeting_chunks(
                meeting_id=meeting_id,
                query_embedding=vectors[0],
                top_k=top_k,
            )
            if hits:
                pieces = []
                for h in hits:
                    pieces.append(_format_chunk(h.get("text", "")))
                joined = "\n\n---\n\n".join(pieces)
                return joined[:MAX_EXCERPT_CHARS]
    except Exception as e:  # noqa: BLE001
        logger.warning("rag.search_failed", error=str(e))

    # フォールバック: 各文書の冒頭テキストを順に結合
    fallback_pieces = []
    budget = MAX_EXCERPT_CHARS
    for doc in documents:
        text = doc.extracted_text or ""
        if not text:
            continue
        piece = f"[{doc.filename}]\n{text[: budget // max(1, len(documents))]}"
        fallback_pieces.append(piece)
        budget -= len(piece)
        if budget <= 0:
            break
    return "\n\n---\n\n".join(fallback_pieces)[:MAX_EXCERPT_CHARS]


def _format_chunk(text: str) -> str:
    """検索結果のチャンクをプロンプトに貼れる形に整形。"""
    return text.strip()[:1500]


async def fetch_document_excerpts_simple(
    *, meeting_id: str, repo: DocumentRepository, per_doc_chars: int = 1500
) -> str:
    """Coverage Tracker 等が tick ごとに使う軽量版 — 文書の冒頭抜粋を結合。

    AI Search を叩かないので毎 tick 呼んでも安い (Cosmos read 1 件のみ)。
    返り値は CoverageTracker.run(document_excerpts=...) にそのまま渡せる
    フォーマット (空文字なら呼び出し側でスキップ)。
    """
    documents = await repo.list_by_meeting(meeting_id)
    if not documents:
        return ""
    pieces: list[str] = []
    for doc in documents:
        text = (doc.extracted_text or "").strip()
        if not text:
            continue
        pieces.append(f"[{doc.filename}]\n{text[:per_doc_chars]}")
    return "\n\n---\n\n".join(pieces)[: MAX_EXCERPT_CHARS]
