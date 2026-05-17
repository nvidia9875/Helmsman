"""Structured logging via structlog + optional Azure Monitor integration."""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO", *, json_output: bool | None = None) -> None:
    """Configure structlog.

    Args:
        level: log level string.
        json_output: True → JSON renderer (本番 Container Apps + App Insights 用)
                     False → ANSI 色付き ConsoleRenderer (ローカル開発)
                     None → stdout.isatty() で自動判定
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        stream=sys.stdout,
    )

    if json_output is None:
        json_output = not sys.stdout.isatty()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def setup_azure_monitor(connection_string: str | None) -> bool:
    """Optionally enable Application Insights via azure-monitor-opentelemetry.

    Auto-instruments FastAPI / httpx / requests / asyncio / logging, sending traces +
    metrics + logs to App Insights. Returns True if wired up successfully.
    """
    if not connection_string:
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=connection_string,
            disable_offline_storage=False,
        )
        return True
    except Exception as e:  # noqa: BLE001
        # Observability の失敗でアプリ本体を落とさない
        logging.getLogger("helmsman").warning(
            "appinsights.setup_failed", extra={"error": str(e)}
        )
        return False


logger = structlog.get_logger("helmsman")
