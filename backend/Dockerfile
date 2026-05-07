FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# LibreOffice + 中文字体（M3 起需要；M1 即装好避免后续返工）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-inter \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]" || pip install .

COPY app ./app
COPY templates ./templates

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
