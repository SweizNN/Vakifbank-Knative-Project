# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Sistem bağımlılıkları (build için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Önce bağımlılıkları kopyala (Docker layer cache optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="VakıfBank DevOps Team" \
      service="producer-api" \
      version="1.0.0"

WORKDIR /app

# Güvenlik: root olmayan kullanıcı
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Bağımlılıkları builder'dan kopyala
COPY --from=builder /install /usr/local

# Uygulama kodunu kopyala
COPY --chown=appuser:appuser main.py .

USER appuser

# K_SINK env variable Knative SinkBinding tarafından inject edilecek
# Bu Dockerfile'da hiçbir URL/IP tanımlanmaz.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
