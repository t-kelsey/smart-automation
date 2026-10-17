FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# tesseract + poppler for pytesseract/pdf2image; libgl/glib for the OpenCV that docling/easyocr pull in
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-spa \
        poppler-utils libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" HF_HOME=/opt/hf

# Dependencies first so code changes don't reinstall them
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev

# Bake the MarianMT translation models into the image so runs work offline (ADR-0018)
RUN python -m bem.translation_and_labeling.download_models
ENV HF_HUB_OFFLINE=1

# Inputs are mounted at /data (read-only); results go to /app/out and /app/output
ENTRYPOINT ["bem"]
CMD ["--help"]
