"""Application settings (pydantic-settings v2)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_dotenv() -> Path | None:
    """Walk up parent directories looking for .env (project root)."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    """Helmsman runtime settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=_find_dotenv(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Environment -----
    environment: str = Field(default="dev", description="dev / staging / prod")
    log_level: str = Field(default="INFO")

    # ----- Azure OpenAI -----
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_high: str = "gpt-5.4"
    azure_openai_deployment_mini: str = "gpt-5.4-mini"
    azure_openai_deployment_realtime: str = "gpt-realtime-1.5"
    azure_openai_deployment_embedding: str = "text-embedding-3-small"

    # ----- Azure AI Search (文書 RAG) -----
    azure_search_endpoint: str | None = None
    azure_search_key: str | None = None
    azure_search_index_name: str = "helmsman-documents"

    # ----- Azure AI Document Intelligence -----
    azure_docintel_endpoint: str | None = None
    azure_docintel_key: str | None = None

    # ----- Azure Communication Services (Teams bot) -----
    acs_connection_string: str | None = None
    acs_callback_base_url: str | None = None
    # ACS が webhook を叩く先のパス (callback_base_url + このパス)
    acs_callback_path: str = "/bot/callback"

    # ----- Azure AI Speech -----
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_endpoint: str | None = None

    # ----- Cosmos DB -----
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str = "helmsman"

    # ----- SignalR -----
    signalr_connection_string: str | None = None

    # ----- Observability -----
    applicationinsights_connection_string: str | None = None

    # ----- Storage -----
    azure_storage_connection_string: str | None = None

    # ----- Resource info -----
    azure_resource_group: str | None = None
    azure_subscription_id: str | None = None
    container_app_fqdn: str | None = None

    # ----- API auth (dev: shared secret. prod: Entra ID 推奨) -----
    helmsman_api_key: str | None = None
    helmsman_require_auth: bool = False

    # CORS: カンマ区切りの origin 一覧。
    # 空なら environment="dev" は "*"、それ以外は default の SWA host
    cors_allowed_origins: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance (singleton)."""
    return Settings()  # type: ignore[call-arg]
