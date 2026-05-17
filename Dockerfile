# Helmsman FastAPI container image
# Multi-stage build: smaller final image
FROM python:3.14-slim AS builder

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# 依存 + 自身を install
RUN uv sync --frozen --no-dev

# ----- runtime stage -----
FROM python:3.14-slim AS runtime

# Azure Cognitive Services Speech SDK の native 依存 + ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      libssl3 \
      libasound2 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安全のため non-root user
RUN groupadd --system app && useradd --system --gid app --uid 10001 app

WORKDIR /app

# builder から venv をコピー
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "helmsman.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
