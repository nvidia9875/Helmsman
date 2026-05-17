"""Azure OpenAI text-embedding-3 wrapper."""
from __future__ import annotations

from helmsman.core.config import get_settings
from helmsman.core.llm_client import get_client
from helmsman.core.logging import logger
from helmsman.core.usage import UsageRecord

# 8K tokens がデフォルトのモデル上限。1 chunk あたりはそれより十分小さくする。
EMBED_MAX_BATCH = 16


async def embed_texts(texts: list[str]) -> tuple[list[list[float]], UsageRecord | None]:
    """テキストをまとめて埋め込みベクトルに変換。

    Returns:
        (vectors, usage_record). usage_record は cost 集計のためにオプションで返す。
    """
    if not texts:
        return [], None

    settings = get_settings()
    client = get_client()
    deployment = settings.azure_openai_deployment_embedding

    vectors: list[list[float]] = []
    total_prompt = 0
    for batch_start in range(0, len(texts), EMBED_MAX_BATCH):
        batch = texts[batch_start : batch_start + EMBED_MAX_BATCH]
        r = await client.embeddings.create(model=deployment, input=batch)
        vectors.extend([d.embedding for d in r.data])
        if r.usage:
            total_prompt += r.usage.prompt_tokens

    logger.info("embed.done", count=len(vectors), tokens=total_prompt)
    usage = (
        UsageRecord(
            agent_name="EmbeddingService",
            model_deployment=deployment,
            prompt_tokens=total_prompt,
            completion_tokens=0,
            total_tokens=total_prompt,
        )
        if total_prompt > 0
        else None
    )
    return vectors, usage
