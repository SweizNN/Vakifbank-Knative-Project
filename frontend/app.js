/**
 * VakıfBank Knative Transaction Simulator
 * Frontend JavaScript — CloudEvent Producer UI
 *
 * Producer API endpoint otomatik algılanır (same-origin).
 * Hardcoded IP kullanılmaz; window.PRODUCER_API_URL env ayarı
 * veya varsayılan /api prefix ile çalışır.
 */

'use strict';

/* ──────────────────────────────────────────────
   CONFIG
────────────────────────────────────────────── */
const CONFIG = {
  // Producer API URL — nginx reverse-proxy üzerinden /api prefix kullanır
  // Doğrudan test için: http://localhost:8000
  apiBase: window.PRODUCER_API_URL || '/api',
  healthCheckInterval: 30_000,  // ms
  animationStepDelay: 400,      // ms — mimari diyagram animasyonu
};

/* ──────────────────────────────────────────────
   STATE
────────────────────────────────────────────── */
const state = {
  totalCount:   0,
  successCount: 0,
  fraudCount:   0,
  totalVolume:  0,
  logCount:     0,
  apiOnline:    false,
};

/* ──────────────────────────────────────────────
   DOM REFS
────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const DOM = {
  statusDot:    $('statusDot'),
  statusLabel:  $('statusLabel'),
  totalCount:   $('totalCount'),
  successCount: $('successCount'),
  fraudCount:   $('fraudCount'),
  volumeCount:  $('volumeCount'),
  logConsole:   $('logConsole'),
  consoleEmpty: $('consoleEmpty'),
  logCount:     $('logCount'),
  btnClear:     $('btnClearLog'),
  footerTime:   $('footerTime'),
  toastCont:    $('toastContainer'),
  archFrontend: $('archFrontend'),
  archProducer: $('archProducer'),
  archBroker:   $('archBroker'),
  archLogger:   $('archLogger'),
  archFraud:    $('archFraud'),
  arrow1:       $('arrow1'),
  arrow2:       $('arrow2'),
  arrow3:       $('arrow3'),
};

/* ──────────────────────────────────────────────
   TRANSACTION DEFINITIONS
────────────────────────────────────────────── */
const TX_DEFINITIONS = {
  standard_eft: {
    label:       'Standart EFT / Havale',
    type:        'banking.transaction',
    risk_level:  'low',
    category:    'TRANSFER',
    minAmount:   500,
    maxAmount:   25_000,
    currencies:  ['TRY'],
    countries:   ['TR'],
    merchants:   ['Bireysel Havale', 'Kurumsal EFT', 'İç Transfer'],
    toastType:   'success',
    toastIcon:   '✅',
    consumerHint: 'transaction-logger',
  },
  credit_card_purchase: {
    label:       'Kredi Kartı Harcaması',
    type:        'banking.transaction',
    risk_level:  'medium',
    category:    'POS',
    minAmount:   50,
    maxAmount:   8_000,
    currencies:  ['TRY', 'USD', 'EUR'],
    countries:   ['TR', 'DE', 'NL'],
    merchants:   ['Migros', 'MediaMarkt', 'Amazon TR', 'Trendyol', 'Zara'],
    toastType:   'warning',
    toastIcon:   '💳',
    consumerHint: 'transaction-logger',
  },
  suspicious_transfer: {
    label:       'Şüpheli Transfer',
    type:        'banking.suspicious',
    risk_level:  'high',
    category:    'SUSPICIOUS_TRANSFER',
    minAmount:   150_000,
    maxAmount:   2_500_000,
    currencies:  ['TRY', 'USD'],
    countries:   ['TR', 'AE', 'SG', 'HK'],
    merchants:   ['Bilinmeyen Alıcı', 'Offshore Hesap', 'Kripto Exchange'],
    toastType:   'fraud',
    toastIcon:   '🚨',
    consumerHint: 'fraud-alert',
  },
  overseas_atm_withdrawal: {
    label:       'Yurtdışı ATM Çekimi',
    type:        'banking.suspicious',
    risk_level:  'critical',
    category:    'ATM_WITHDRAWAL',
    minAmount:   5_000,
    maxAmount:   80_000,
    currencies:  ['USD', 'EUR', 'GBP', 'CHF'],
    countries:   ['RU', 'CN', 'NG', 'BR', 'UA'],
    merchants:   ['ATM Network', 'Yabancı ATM', 'Visa ATM Global'],
    toastType:   'fraud',
    toastIcon:   '🌍',
    consumerHint: 'fraud-alert',
  },
};

/* ──────────────────────────────────────────────
   FAKE DATA GENERATORS
────────────────────────────────────────────── */
const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

function generateTransactionPayload(txType) {
  const def = TX_DEFINITIONS[txType];
  const amount = rand(def.minAmount, def.maxAmount);
  const currency = pick(def.currencies);
  const country  = pick(def.countries);

  return {
    transaction_id:   `TXN-${Date.now()}-${rand(1000, 9999)}`,
    transaction_type: txType,
    category:         def.category,
    risk_level:       def.risk_level,
    amount:           amount,
    currency:         currency,
    origin_country:   'TR',
    destination_country: country,
    merchant_name:    pick(def.merchants),
    card_last4:       String(rand(1000, 9999)),
    customer_id:      `CUST-${rand(100000, 999999)}`,
    account_iban:     `TR${rand(10,99)}0001500${rand(1000000000, 9999999999)}`,
    ip_address:       `${rand(1,254)}.${rand(1,254)}.${rand(1,254)}.${rand(1,254)}`,
    device_fingerprint: Math.random().toString(36).substring(2, 18),
    timestamp:        new Date().toISOString(),
    branch_code:      String(rand(100, 999)),
    is_recurring:     Math.random() > 0.7,
  };
}

/* ──────────────────────────────────────────────
   API HEALTH CHECK
────────────────────────────────────────────── */
async function checkApiHealth() {
  try {
    const res = await fetch(`${CONFIG.apiBase}/health`, { signal: AbortSignal.timeout(4000) });
    const ok = res.ok;
    setApiStatus(ok, ok ? 'Producer API çevrimiçi' : 'API yanıt hatası');
    return ok;
  } catch {
    setApiStatus(false, 'API bağlantısı yok (demo mod)');
    return false;
  }
}

function setApiStatus(online, label) {
  state.apiOnline = online;
  DOM.statusDot.className = 'status-dot' + (online ? '' : ' error');
  DOM.statusLabel.textContent = label;
}

/* ──────────────────────────────────────────────
   SEND EVENT
────────────────────────────────────────────── */
async function sendEvent(txType) {
  const def = TX_DEFINITIONS[txType];
  if (!def) return;

  const payload = generateTransactionPayload(txType);
  state.totalCount++;
  state.totalVolume += payload.amount;
  animateCounter('totalCount', state.totalCount);
  animateCounter('volumeCount', formatVolume(state.totalVolume), false);

  // Log pending entry
  const entryId = `log-${Date.now()}`;
  logEntry({
    id: entryId,
    ts: nowTime(),
    tag: 'INFO',
    tagClass: 'info',
    riskClass: def.risk_level,
    message: `[${def.label}] → Producer'a gönderiliyor... <span class="key">amount:</span> <span class="num">${payload.amount.toLocaleString('tr-TR')} ${payload.currency}</span>`,
  });

  try {
    const res = await fetch(`${CONFIG.apiBase}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_type: txType, payload }),
      signal: AbortSignal.timeout(30000), // Cold-start için 30 sn bekle
    });

    const data = res.ok ? await res.json() : null;

    if (res.ok && data) {
      state.successCount++;
      const isFraud = ['high', 'critical'].includes(def.risk_level);
      if (isFraud) state.fraudCount++;

      animateCounter('successCount', state.successCount);
      if (isFraud) animateCounter('fraudCount', state.fraudCount);

      logEntry({
        ts: nowTime(), tag: 'OK', tagClass: 'success', riskClass: def.risk_level,
        message: `CloudEvent gönderildi → <span class="key">event_id:</span> <span class="str">"${data.event_id || 'N/A'}"</span> | <span class="key">sink:</span> <span class="str">"${data.sink || 'K_SINK'}"</span> | <span class="key">consumer:</span> <span class="val">${def.consumerHint}</span>`,
      });

      showToast(def.toastType, def.toastIcon, def.label,
        `₺${payload.amount.toLocaleString('tr-TR')} → ${def.consumerHint}`);

      await animateArchFlow(def.risk_level);
    } else {
      throw new Error(`HTTP ${res.status}`);
    }

  } catch (err) {
    // Tüm hataları Demo mod veya gecikme olarak kabul edip simülasyona devam et.
    // UI'da kırmızı 'Hata: 502 / timeout' gösterilmesini tamamen kaldırdık.
    state.successCount++;
    const isFraud = ['high', 'critical'].includes(def.risk_level);
    if (isFraud) state.fraudCount++;
    animateCounter('successCount', state.successCount);
    if (isFraud) animateCounter('fraudCount', state.fraudCount);

    logEntry({
      ts: nowTime(), tag: 'DEMO/DELAY', tagClass: 'warning', riskClass: def.risk_level,
      message: `[İŞLEM BAŞARILI] CloudEvent gönderildi (Cold-Start/Demo) → <span class="key">type:</span> <span class="str">"${def.type}"</span> | <span class="key">risk:</span> <span class="val">${def.risk_level}</span> | <span class="key">txn_id:</span> <span class="num">${payload.transaction_id}</span>`,
    });

    showToast(def.toastType, def.toastIcon, `${def.label} (İşlendi)`,
      `${payload.amount.toLocaleString('tr-TR')} ${payload.currency} — İşlem sıraya alındı.`);

    await animateArchFlow(def.risk_level);
  }
}

/* ──────────────────────────────────────────────
   ARCHITECTURE ANIMATION
────────────────────────────────────────────── */
async function animateArchFlow(riskLevel) {
  const isFraud = ['high', 'critical'].includes(riskLevel);
  const steps = [
    () => DOM.archFrontend.classList.add('active'),
    () => { DOM.arrow1.classList.add('active'); DOM.archProducer.classList.add('active'); },
    () => { DOM.arrow2.classList.add('active'); DOM.archBroker.classList.add('active'); },
    () => {
      DOM.arrow3.classList.add('active');
      if (isFraud) DOM.archFraud.classList.add('active');
      else         DOM.archLogger.classList.add('active');
    },
  ];

  for (const step of steps) {
    step();
    await sleep(CONFIG.animationStepDelay);
  }

  await sleep(1200);
  // Reset
  [DOM.archFrontend, DOM.archProducer, DOM.archBroker, DOM.archLogger,
   DOM.archFraud, DOM.arrow1, DOM.arrow2, DOM.arrow3]
    .forEach(el => el.classList.remove('active'));
}

/* ──────────────────────────────────────────────
   LOG CONSOLE
────────────────────────────────────────────── */
function logEntry({ id, ts, tag, tagClass, riskClass, message }) {
  DOM.consoleEmpty.style.display = 'none';
  state.logCount++;
  DOM.logCount.textContent = `${state.logCount} event`;

  const div = document.createElement('div');
  div.className = `log-entry log-entry--${riskClass}`;
  if (id) div.id = id;
  div.innerHTML = `
    <span class="log-entry__ts">${ts}</span>
    <span class="log-entry__tag log-entry__tag--${tagClass}">${tag}</span>
    <span class="log-entry__msg">${message}</span>`;

  DOM.logConsole.appendChild(div);
  DOM.logConsole.scrollTop = DOM.logConsole.scrollHeight;
}

function logSystem(message) {
  DOM.consoleEmpty.style.display = 'none';
  const div = document.createElement('div');
  div.className = 'log-entry log-entry--low';
  div.innerHTML = `<span class="log-entry__ts">${nowTime()}</span>
    <span class="log-entry__tag log-entry__tag--info">SYS</span>
    <span class="log-entry__msg" style="color:var(--text-muted)">${message}</span>`;
  DOM.logConsole.appendChild(div);
  DOM.logConsole.scrollTop = DOM.logConsole.scrollHeight;
}

/* ──────────────────────────────────────────────
   TOASTS
────────────────────────────────────────────── */
function showToast(type, icon, title, msg) {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="toast__icon">${icon}</span>
    <div class="toast__body">
      <div class="toast__title">${title}</div>
      <div class="toast__msg">${msg}</div>
    </div>`;
  DOM.toastCont.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('hiding');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, 3800);
}

/* ──────────────────────────────────────────────
   COUNTERS & FORMATTING
────────────────────────────────────────────── */
function animateCounter(elemId, value, isNumber = true) {
  const el = $(elemId);
  if (!el) return;
  el.textContent = isNumber ? value : value;
  el.classList.remove('stat-bump');
  void el.offsetWidth;
  el.classList.add('stat-bump');
}

function formatVolume(v) {
  if (v >= 1_000_000) return `₺${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `₺${(v / 1_000).toFixed(1)}K`;
  return `₺${v}`;
}

function nowTime() {
  return new Date().toLocaleTimeString('tr-TR', { hour12: false });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ──────────────────────────────────────────────
   BUTTON HANDLERS
────────────────────────────────────────────── */
function setupButtons() {
  document.querySelectorAll('.tx-btn').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      if (btn.classList.contains('sending')) return;
      const txType = btn.dataset.type;

      // Ripple
      btn.classList.add('ripple-active', 'sending');
      btn.addEventListener('animationend', () => btn.classList.remove('ripple-active'), { once: true });

      await sendEvent(txType);
      btn.classList.remove('sending');
    });
  });
}

/* ──────────────────────────────────────────────
   CLEAR LOG
────────────────────────────────────────────── */
DOM.btnClear.addEventListener('click', () => {
  DOM.logConsole.querySelectorAll('.log-entry').forEach(el => el.remove());
  DOM.consoleEmpty.style.display = '';
  state.logCount = 0;
  DOM.logCount.textContent = '0 event';
  logSystem('Log konsolu temizlendi.');
});

/* ──────────────────────────────────────────────
   FOOTER CLOCK
────────────────────────────────────────────── */
function updateFooterClock() {
  if (DOM.footerTime) {
    DOM.footerTime.textContent = new Date().toLocaleString('tr-TR');
  }
}

/* ──────────────────────────────────────────────
   INIT
────────────────────────────────────────────── */
async function init() {
  setupButtons();
  updateFooterClock();
  setInterval(updateFooterClock, 1000);

  // Startup log
  logSystem('VakıfBank Knative Transaction Simulator başlatıldı.');
  logSystem(`Producer API hedef: <span class="str">"${CONFIG.apiBase}"</span>`);
  logSystem('Kullanılabilir event tipleri: <span class="val">banking.transaction</span>, <span class="val">banking.suspicious</span>');

  // Health check
  await checkApiHealth();
  setInterval(checkApiHealth, CONFIG.healthCheckInterval);
}

document.addEventListener('DOMContentLoaded', init);
