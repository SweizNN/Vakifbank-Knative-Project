"""
VakıfBank Knative — Fraud Alert Service
=========================================
Knative Service (ksvc) olarak çalışır → Scale-to-Zero aktif.
Trigger'dan gelen 'banking.suspicious' tipindeki veya
risk_level=high/critical CloudEvent'leri alır.
Terminalde renkli UYARI mesajları ve detaylı fraud raporu basar.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from cloudevents.http import from_http
from fastapi import FastAPI, Request, status
from fastapi.responses import PlainTextResponse

# ─── ANSI Renk Kodları ────────────────────────────────────────────────────────
RED      = "\033[91m"
YELLOW   = "\033[93m"
CYAN     = "\033[96m"
MAGENTA  = "\033[95m"
WHITE    = "\033[97m"
BOLD     = "\033[1m"
BLINK    = "\033[5m"
RESET    = "\033[0m"
BG_RED   = "\033[41m"
BG_DARK  = "\033[40m"

# ─── Structured JSON Logger ──────────────────────────────────────────────────
class FraudJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "service":   "fraud-alert-service",
            "alert":     True,
            "message":   record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        return json.dumps(log_obj, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(FraudJsonFormatter())
logging.basicConfig(level=logging.WARNING, handlers=[handler])
logger = logging.getLogger("fraud-alert")

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fraud Alert Service",
    description="Knative ksvc — banking.suspicious event consumer",
    version="1.0.0",
)

# ─── Alert Counter & Idempotency ─────────────────────────────────────────────
alert_counter = {"total": 0, "high": 0, "critical": 0}
seen_events = set() # Broker retry'larını filtrelemek için

# ─── Risk Mesaj Şablonları ────────────────────────────────────────────────────
RISK_MESSAGES = {
    "high": {
        "emoji":  "🚨",
        "title":  "YÜKSEK RİSKLİ İŞLEM",
        "action": "Müşteri aranmalı, işlem onay bekliyor",
        "color":  RED,
    },
    "critical": {
        "emoji":  "🔴",
        "title":  "KRİTİK FRAUD UYARISI",
        "action": "İşlem DURDURULDU — Acil Fraud ekibi devrede",
        "color":  MAGENTA,
    },
}

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.post("/", summary="Fraud CloudEvent al ve uyar")
async def receive_fraud_event(request: Request):
    """
    Knative Trigger bu endpoint'e yüksek riskli CloudEvent'leri yönlendirir.
    """
    headers = dict(request.headers)
    body    = await request.body()

    try:
        event = from_http(headers, body)
    except Exception as e:
        logger.error("CloudEvent parse hatası: %s", str(e))
        return PlainTextResponse(
            content=f"CloudEvent parse hatası: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    data: dict    = event.data or {}
    risk_level    = data.get("risk_level", event.get("risklevel", "high"))
    tx_type       = data.get("transaction_type", event.get("transactiontype", "unknown"))
    amount        = data.get("amount", 0)
    currency      = data.get("currency", "TRY")
    customer      = data.get("customer_id", "N/A")
    account_iban  = data.get("account_iban", "N/A")
    ip_address    = data.get("ip_address", "N/A")
    dest_country  = data.get("destination_country", "N/A")
    merchant      = data.get("merchant_name", "N/A")
    device_fp     = data.get("device_fingerprint", "N/A")
    card_last4    = data.get("card_last4", "****")
    risk_score    = data.get("risk_score", event.get("riskscore", 0))

    risk_info = RISK_MESSAGES.get(risk_level, RISK_MESSAGES["high"])
    clr = risk_info["color"]

    event_id = event["id"]
    
    # ── Idempotency Check (Broker Retry'larını Yoksay) ──
    if event_id in seen_events:
        logger.info("Duplicate event ignored: %s", event_id)
        return PlainTextResponse(content="", status_code=200)
    seen_events.add(event_id)
    # Bellek şişmesini önlemek için basit temizlik (1000'den fazlaysa boşalt)
    if len(seen_events) > 1000:
        seen_events.clear()
        seen_events.add(event_id)

    alert_counter["total"] += 1
    if risk_level == "high":     alert_counter["high"] += 1
    if risk_level == "critical": alert_counter["critical"] += 1

    # Yapılandırılmış fraud log (JSON)
    logger.warning(
        "FRAUD UYARISI — %s",
        risk_info["title"],
        extra={
            "alert_number":     alert_counter["total"],
            "event_id":         event["id"],
            "event_type":       event["type"],
            "transaction_type": tx_type,
            "risk_level":       risk_level,
            "risk_score":       risk_score,
            "amount":           amount,
            "currency":         currency,
            "customer_id":      customer,
            "account_iban":     account_iban,
            "destination":      dest_country,
            "merchant":         merchant,
            "ip_address":       ip_address,
            "device_fp":        device_fp,
            "card_last4":       card_last4,
            "recommended_action": risk_info["action"],
        },
    )

    # ─── Renkli Terminal Çıktısı ──────────────────────────────────────────
    border = f"{clr}{'█'*62}{RESET}"
    print(f"\n{border}", flush=True)
    print(
        f"{clr}{BOLD}  {risk_info['emoji']}  {BG_RED} {risk_info['title']} {RESET}{clr}{BOLD}"
        f"  — Alert #{alert_counter['total']}{RESET}",
        flush=True,
    )
    print(border, flush=True)
    print(
        f"\n{BOLD}{WHITE}  ⚠  FRAUD TESPIT SİSTEMİ — VakıfBank Security Operations{RESET}\n",
        flush=True,
    )

    fields = [
        ("Event ID",          event["id"]),
        ("Olay Tipi",         f"{event['type']} ({tx_type.upper()})"),
        ("Risk Seviyesi",     f"{clr}{BOLD}{risk_level.upper()}{RESET}  (Skor: {risk_score}/100)"),
        ("İşlem Tutarı",      f"{BOLD}{amount:,} {currency}{RESET}"),
        ("Müşteri",           customer),
        ("IBAN",              account_iban),
        ("Kart Son 4",        f"**** **** **** {card_last4}"),
        ("Hedef Ülke",        f"{clr}{dest_country}{RESET}"),
        ("IP Adresi",         ip_address),
        ("Device FP",         device_fp[:16] + "..."),
        ("Merchant",          merchant),
        ("Zaman",             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
    ]
    for label, value in fields:
        print(f"  {CYAN}{label:<20}{RESET} : {value}", flush=True)

    print(f"\n  {YELLOW}{BOLD}⚡ ÖNERİLEN EYLEM: {risk_info['action']}{RESET}", flush=True)
    print(
        f"\n  {WHITE}Toplam Fraud Uyarısı: {alert_counter['total']} "
        f"(High: {alert_counter['high']}, Critical: {alert_counter['critical']}){RESET}",
        flush=True,
    )
    print(f"{border}\n", flush=True)

    return PlainTextResponse(content="", status_code=status.HTTP_200_OK)

@app.get("/health", summary="Health check")
async def health():
    return {
        "status":   "healthy",
        "service":  "fraud-alert-service",
        "counters": alert_counter,
        "time":     datetime.now(timezone.utc).isoformat(),
    }

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "fraud-alert-service", "counters": alert_counter}

# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="warning")
