"""文書からテキストを抽出する。

優先順:
  1. Azure AI Document Intelligence (AZURE_DOCINTEL_* が両方セット時)
  2. ローカル抽出 (pypdf for PDF, decode for text/markdown)

3 以外の Office 形式 (Word/PPT/Excel) は本番では DocIntel に投げる。
dev 環境ではエラーを返さず "(本番デプロイで Document Intelligence が処理します)"
というプレースホルダを返す方針。
"""
from __future__ import annotations

import io

from helmsman.core.config import get_settings
from helmsman.core.logging import logger

# Document Intelligence が確実に扱える MIME (ローカル抽出不要)
DOCINTEL_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/heif",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# プレーンテキスト系は decode するだけ
PLAIN_TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/html",
}


async def extract_text(data: bytes, mime_type: str, filename: str) -> str:
    """文書バイナリからテキストを抽出する。

    抽出できない形式は空文字列を返さず、警告ログ + プレースホルダ。
    呼び出し側でステータスを FAILED に更新するかは判断する。
    """
    if mime_type in PLAIN_TEXT_MIME_TYPES or filename.endswith((".md", ".txt")):
        return data.decode("utf-8", errors="replace")

    settings = get_settings()
    has_docintel = bool(
        settings.azure_docintel_endpoint and settings.azure_docintel_key
    )
    if has_docintel and mime_type in DOCINTEL_MIME_TYPES:
        return await _extract_with_docintel(data, mime_type)

    if mime_type == "application/pdf":
        return _extract_pdf_local(data)

    logger.warning(
        "extractor.unsupported",
        mime=mime_type,
        filename=filename,
        has_docintel=has_docintel,
    )
    return (
        f"[未対応形式 {mime_type}] 本番環境では Azure AI Document Intelligence "
        f"が処理します。ファイル名: {filename}"
    )


def _extract_pdf_local(data: bytes) -> str:
    """pypdf で PDF からテキストを取り出す (dev フォールバック)。"""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        logger.warning("extractor.pypdf_missing", error=str(e))
        return ""

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as e:  # noqa: BLE001
            logger.warning("extractor.pdf_page_failed", page=i, error=str(e))
    return "\n\n".join(pages).strip()


async def _extract_with_docintel(data: bytes, mime_type: str) -> str:
    """Azure AI Document Intelligence の prebuilt-layout / read で抽出。"""
    settings = get_settings()
    # 遅延 import
    from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential

    assert settings.azure_docintel_endpoint and settings.azure_docintel_key
    async with DocumentIntelligenceClient(
        endpoint=settings.azure_docintel_endpoint,
        credential=AzureKeyCredential(settings.azure_docintel_key),
    ) as client:
        poller = await client.begin_analyze_document(
            model_id="prebuilt-read",
            body=AnalyzeDocumentRequest(bytes_source=data),
            content_type="application/json",
        )
        result = await poller.result()

    if not result.content:
        logger.warning("extractor.docintel_empty", mime=mime_type)
        return ""
    return result.content
