"""
VakıfBank Knative — Producer API
=================================
FastAPI uygulaması. Frontend'den gelen işlem isteklerini alır,
CloudEvents formatına çevirir ve K_SINK ortam değişkeniyle
enjekte edilen Knative Broker adresine HTTP POST ile gönderir.

ÖNEMLI: Bu dosyada hiçbir hardcoded IP/URL yoktur.
Hedef adres tamamen K_SINK env variable'ından okunur.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from cloudevents.http import CloudEvent, to_structured
from cloudevents.conversion import to_json
from pydantic import BaseModel, Field

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("producer-api")

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="VakıfBank Knative Producer API",
    description="CloudEvent üretici — Event-Driven Banking Transaction System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Production'da spesifik origin kısıtla
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config — K_SINK env variable (Knative SinkBinding inject eder) ──────────
def get_sink_url() -> str:
    """
    K_SINK: Knative SinkBinding tarafından otomatik inject edilir.
    Bu değer Broker'ın in-cluster adresidir.
    Lokal test için K_SINK env variable'ı export edilebilir.
    """
    sink = os.environ.get("K_SINK")
    if not sink:
        raise RuntimeError(
            "K_SINK environment variable is not set. "
            "Bu uygulama Knative SinkBinding ile birlikte çalışmalıdır. "
            "Lokal test için: export K_SINK=http://broker-ingress.knative-eventing.svc.cluster.local/banking-system/default"
        )
    return sink

# ─── Risk Score Engine ───────────────────────────────────────────────────────
RISK_SCORES: Dict[str, int] = {
    "standard_eft":          10,
    "credit_card_purchase":  40,
    "suspicious_transfer":   85,
    "overseas_atm_withdrawal": 95,
}

CLOUDEVENT_TYPES: Dict[str, str] = {
    "standard_eft":            "banking.transaction",
    "credit_card_purchase":    "banking.transaction",
    "suspicious_transfer":     "banking.suspicious",
    "overseas_atm_withdrawal": "banking.suspicious",
}

RISK_LEVELS: Dict[str, str] = {
    "standard_eft":            "low",
    "credit_card_purchase":    "medium",
    "suspicious_transfer":     "high",
    "overseas_atm_withdrawal": "critical",
}

# ─── Request Models ──────────────────────────────────────────────────────────
class SimulateRequest(BaseModel):
    transaction_type: str = Field(
        ...,
        description="İşlem tipi",
        examples=["standard_eft", "credit_card_purchase", "suspicious_transfer", "overseas_atm_withdrawal"],
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="İşlem detayları (frontend tarafından üretilir)",
    )

# ─── CloudEvent Factory ──────────────────────────────────────────────────────
def build_cloud_event(tx_type: str, payload: Dict[str, Any]) -> CloudEvent:
    """
    CloudEvents v1.0 spec'e uygun event oluşturur.
    Extensions alanına risk metadata'sı eklenir (Trigger filter için kullanılır).
    """
    event_id = str(uuid.uuid4())
    risk_level = RISK_LEVELS.get(tx_type, "low")
    risk_score = RISK_SCORES.get(tx_type, 0)
    ce_type = CLOUDEVENT_TYPES.get(tx_type, "banking.transaction")

    # Trigger filter için extension attributes
    attributes = {
        "type":              ce_type,
        "source":            "vakifbank/producer-api/v1",
        "id":                event_id,
        "time":              datetime.now(timezone.utc).isoformat(),
        "datacontenttype":   "application/json",
        "specversion":       "1.0",
        # Custom extensions (Knative Trigger filter bu alanlara bakabilir)
        "risklevel":         risk_level,   # lowercase, no underscore (CE spec)
        "riskscore":         str(risk_score),
        "transactiontype":   tx_type,
    }

    # Payload'a hesaplanan risk bilgisini ekle
    enriched_payload = {
        **payload,
        "risk_level":  risk_level,
        "risk_score":  risk_score,
        "event_id":    event_id,
        "ce_type":     ce_type,
    }

    return CloudEvent(attributes=attributes, data=enriched_payload)

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/health", summary="Health check", tags=["System"])
async def health_check():
    """Liveness probe endpoint."""
    sink_configured = bool(os.environ.get("K_SINK"))
    return {
        "status":          "healthy",
        "service":         "producer-api",
        "version":         "1.0.0",
        "k_sink_set":      sink_configured,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/health", summary="Health check (API prefix)", tags=["System"])
async def health_check_api():
    """Nginx /api prefix üzerinden health check."""
    return await health_check()

@app.post("/simulate", summary="İşlem simüle et ve CloudEvent gönder", tags=["Events"])
async def simulate_transaction(request: SimulateRequest):
    """
    Frontend'den gelen işlem isteğini CloudEvent'e çevirir ve
    K_SINK (Knative Broker) adresine HTTP POST ile gönderir.
    """
    tx_type = request.transaction_type

    if tx_type not in CLOUDEVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bilinmeyen işlem tipi: '{tx_type}'. "
                   f"Geçerli tipler: {list(CLOUDEVENT_TYPES.keys())}",
        )

    # K_SINK'ten broker adresini al
    try:
        sink_url = get_sink_url()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # CloudEvent oluştur
    event = build_cloud_event(tx_type, request.payload)
    headers, body = to_structured(event)

    logger.info(
        "CloudEvent gönderiliyor | type=%s | risk=%s | sink=%s | event_id=%s",
        event["type"],
        event["risklevel"],
        sink_url,
        event["id"],
    )

    # Knative Broker'a HTTP POST
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                sink_url,
                content=body,
                headers=dict(headers),
            )
            response.raise_for_status()

        logger.info(
            "CloudEvent kabul edildi | status=%d | event_id=%s",
            response.status_code,
            event["id"],
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status":           "accepted",
                "event_id":         event["id"],
                "event_type":       event["type"],
                "risk_level":       event["risklevel"],
                "risk_score":       event["riskscore"],
                "sink":             sink_url,
                "broker_status":    response.status_code,
                "transaction_type": tx_type,
            },
        )

    except httpx.HTTPStatusError as e:
        logger.error("Broker HTTP hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Knative Broker yanıt hatası: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error("Broker bağlantı hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Knative Broker'a ulaşılamıyor: {type(e).__name__}",
        )

@app.post("/api/simulate", summary="İşlem simüle et (API prefix)", tags=["Events"])
async def simulate_transaction_api(request: SimulateRequest):
    """Nginx /api prefix üzerinden yönlendirilen simulate endpoint."""
    return await simulate_transaction(request)

@app.get("/", summary="Root", include_in_schema=False)
async def root():
    return {"service": "VakıfBank Knative Producer API", "docs": "/api/docs"}

# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )
