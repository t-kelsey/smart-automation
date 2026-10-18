# Build context is the repo root (see docker-compose.yml): the pipeline reads ../standards (DIN 4023).
FROM python:3.12-slim-trixie

# poppler-utils: pdftoppm, so Claude can render PDF pages (scans, colours, hatching).
# libreoffice-writer: converts Word documents to PDF before the pipeline reads them.
# nodejs/npm: the pipeline shells out to the Claude Code CLI (`claude -p`).
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends poppler-utils libreoffice-writer fonts-liberation nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /repo/bem
COPY bem/pyproject.toml bem/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY bem/pipeline ./pipeline
COPY standards /repo/standards

# BEM_ENV=prod: nothing is kept on disk besides temp files. HOME must be writable for the claude CLI.
ENV BEM_ENV=prod BEM_PORT=8000 BEM_WORKDIR=/data/work HOME=/home/app PYTHONUNBUFFERED=1
RUN useradd --create-home app && mkdir -p /data/work && chown -R app /data /home/app
USER app
EXPOSE 8000
CMD ["python", "-m", "pipeline.server"]
