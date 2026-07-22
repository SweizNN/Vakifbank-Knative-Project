"""
VakıfBank Knative — Transaction Logger Service
================================================
Knative Service (ksvc) olarak çalışır → Scale-to-Zero aktif.
Trigger'dan gelen 'banking.transaction' tipindeki CloudEvent'leri
alır, yapılandırılmış JSON formatında loglar ve 200 OK döndürür.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from cloudevents.http import from_http
from fastapi import FastAPI, Request, status
from fastapi.responses import PlainTextResponse

# ─── Structured JSON Logger ──────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "level":      record.levelname,
            "service":    "transaction-logger",
            "message":    record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        return json.dumps(log_obj, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("transaction-logger")

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Transaction Logger Service",
    description="Knative ksvc — banking.transaction event consumer",
    version="1.0.0",
)

# ─── Event Counter & Idempotency ─────────────────────────────────────────────
event_counter = {"total": 0, "low": 0, "medium": 0}
seen_events = set() # Broker retry'larını filtrelemek için

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.post("/", summary="CloudEvent al ve logla")
async def receive_event(request: Request):
    """
    Knative Trigger bu endpoint'e CloudEvent gönderir.
    CloudEvents HTTP binding (structured veya binary mode) desteklenir.
    """
    headers = dict(request.headers)
    body = await request.body()

    try:
        event = from_http(headers, body)
    except Exception as e:
        logger.error("CloudEvent parse hatası: %s", str(e))
        return PlainTextResponse(
            content=f"CloudEvent parse hatası: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    data: dict = event.data or {}
    risk_level = data.get("risk_level", event.get("risklevel", "unknown"))
    tx_type    = data.get("transaction_type", event.get("transactiontype", "unknown"))
    amount     = data.get("amount", 0)
    currency   = data.get("currency", "TRY")
    customer   = data.get("customer_id", "N/A")
    merchant   = data.get("merchant_name", "N/A")

    event_id = event["id"]
    
    # ── Idempotency Check (Broker Retry'larını Yoksay) ──
    if event_id in seen_events:
        logger.info("Duplicate event ignored: %s", event_id)
        return PlainTextResponse(content="OK (Duplicate)", status_code=200)
    seen_events.add(event_id)
    if len(seen_events) > 1000:
        seen_events.clear()
        seen_events.add(event_id)

    event_counter["total"] += 1
    if risk_level == "low":    event_counter["low"] += 1
    if risk_level == "medium": event_counter["medium"] += 1

    # Yapılandırılmış log satırı
    logger.info(
        "İşlem kaydedildi",
        extra={
            "event_id":          event["id"],
            "event_type":        event["type"],
            "transaction_type":  tx_type,
            "risk_level":        risk_level,
            "amount":            amount,
            "currency":          currency,
            "customer_id":       customer,
            "merchant_name":     merchant,
            "account_iban":      data.get("account_iban", "N/A"),
            "origin_country":    data.get("origin_country", "N/A"),
            "dest_country":      data.get("destination_country", "N/A"),
            "card_last4":        data.get("card_last4", "****"),
            "branch_code":       data.get("branch_code", "N/A"),
            "is_recurring":      data.get("is_recurring", False),
            "event_source":      event["source"],
            "event_time":        str(event.get("time", "")),
            "total_processed":   event_counter["total"],
        },
    )

    # Konsolda okunabilir özet
    print(
        f"\n{'─'*60}\n"
        f"  📋 TRANSACTION LOGGER — İşlem #{event_counter['total']}\n"
        f"{'─'*60}\n"
        f"  Event ID   : {event['id']}\n"
        f"  Tip        : {tx_type.upper()} ({event['type']})\n"
        f"  Risk       : {risk_level.upper()}\n"
        f"  Tutar      : {amount:,} {currency}\n"
        f"  Müşteri    : {customer}\n"
        f"  Merchant   : {merchant}\n"
        f"  IBAN       : {data.get('account_iban', 'N/A')}\n"
        f"  Ülke       : {data.get('origin_country')} → {data.get('destination_country')}\n"
        f"  Zaman      : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"{'─'*60}\n",
        flush=True,
    )

    return PlainTextResponse(content="OK", status_code=status.HTTP_200_OK)

@app.get("/health", summary="Health check")
async def health():
    return {
        "status":   "healthy",
        "service":  "transaction-logger",
        "counters": event_counter,
        "time":     datetime.now(timezone.utc).isoformat(),
    }

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "transaction-logger-service", "counters": event_counter}

# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")
