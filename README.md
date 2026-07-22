# 🏦 VakıfBank — Event-Driven Banking Transaction & Fraud Detection

**Kubernetes + Knative Serving & Eventing** tabanlı, olay güdümlü bankacılık işlem ve dolandırıcılık tespit sistemi.

![Architecture](https://img.shields.io/badge/Architecture-Event--Driven-6366f1?style=for-the-badge)
![Knative](https://img.shields.io/badge/Knative-v1.14-0865AD?style=for-the-badge&logo=knative)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=for-the-badge&logo=docker)

---

## 📐 Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                    banking-system namespace                      │
│                                                                  │
│  ┌──────────┐    HTTP     ┌──────────────┐                      │
│  │ Frontend │ ──POST───► │ Producer API │                      │
│  │  (nginx) │            │  (FastAPI)   │◄── K_SINK (SinkBinding)│
│  └──────────┘            └──────┬───────┘                      │
│                                 │ CloudEvent                    │
│                                 ▼                               │
│                    ┌────────────────────────┐                   │
│                    │   Knative Broker       │                   │
│                    │   (InMemory Channel)   │                   │
│                    └────────────┬───────────┘                   │
│                                 │                               │
│              ┌──────────────────┼──────────────────┐            │
│              │                  │                  │            │
│    type=banking.transaction  type=banking.suspicious │            │
│    risk=low/medium           risk=high/critical     │            │
│              │                                     │            │
│              ▼                                     ▼            │
│  ┌─────────────────────────┐       ┌──────────────────────────┐ │
│  │ transaction-logger-svc  │       │   fraud-alert-service    │ │
│  │  (Knative Service/ksvc) │       │  (Knative Service/ksvc)  │ │
│  │  ✓ Scale-to-Zero        │       │  ✓ Scale-to-Zero         │ │
│  │  ✓ Auto Scale-up        │       │  ✓ Renkli Alert Çıktısı  │ │
│  └─────────────────────────┘       └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Klasör Yapısı

```
Vakifbank-Knative-Project/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD Pipeline (GitHub Actions)
│
├── frontend/                       # Simülasyon Web Arayüzü
│   ├── index.html                  # Premium dark-mode UI
│   ├── style.css                   # Glassmorphism tasarım
│   ├── app.js                      # CloudEvent simülasyon mantığı
│   ├── nginx.conf                  # Reverse proxy + static server
│   └── Dockerfile                  # nginx:alpine image
│
├── producer/                       # Olay Üretici API
│   ├── main.py                     # FastAPI — CloudEvents SDK
│   ├── requirements.txt
│   └── Dockerfile                  # Multi-stage build
│
├── services/
│   ├── transaction-logger/         # Standart İşlem Tüketicisi
│   │   ├── main.py                 # JSON structured logging
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── fraud-alert/                # Fraud Tüketicisi
│       ├── main.py                 # Renkli ANSI terminal alert
│       ├── requirements.txt
│       └── Dockerfile
│
├── k8s/                            # Kubernetes & Knative Manifestoları
│   ├── namespace.yaml              # banking-system namespace
│   ├── broker.yaml                 # Knative InMemory Broker
│   ├── sinkbinding.yaml            # K_SINK otomatik inject
│   ├── triggers.yaml               # 3 adet event routing trigger
│   ├── ksvc.yaml                   # 2 Knative Service (scale-to-zero)
│   ├── producer-deployment.yaml    # Producer Deployment + Service
│   └── frontend-deployment.yaml   # Frontend Deployment + NodePort
│
└── scripts/
    ├── setup-minikube.sh           # Otomatik kurulum scripti
    └── port-forward.sh             # Geliştirme port-forward
```

---

## 🚀 Hızlı Başlangıç (Minikube)

### Ön Koşullar

```bash
# Versiyon kontrolleri
minikube version   # >= 1.33
kubectl version    # >= 1.28
docker version     # >= 24
```

### 1. Tek Tıkla Kurulum ve İzleme

Projenin tüm bağımlılıklarını kurup ardından logları ve port-forward'ları tek bir ekranda canlı izlemek için hazırladığımız `setup-and-run.sh` scriptini çalıştırın:

```bash
chmod +x scripts/setup-and-run.sh
./scripts/setup-and-run.sh
```

Bu script sırasıyla şunları yapar:
1. Knative Serving ve Eventing bileşenlerini kurar.
2. Projemize ait (Producer, Frontend, Broker vb.) tüm kaynakları uygular.
3. Uygulamalara (Frontend:3000 ve Producer:8000) **Port-forward** başlatır.
4. **Logları ve Pod değişikliklerini** canlı olarak ekrana basar.

İşlemi durdurmak istediğinizde `Ctrl + C` tuşlarına basmanız yeterlidir. (Kurulumlar kalıcıdır, sadece izleme durur).


### 2. Manuel Kurulum (Alternatif)

Eğer script kullanmak istemezseniz, aşağıdaki komutları terminalinizde **sırayla** çalıştırarak sistemi manuel olarak da kurabilirsiniz.

#### Adım 1 — Minikube Başlatma
```bash
minikube start --cpus=4 --memory=4096 --kubernetes-version=v1.30.0
```

#### Adım 2 — Knative Serving & Kourier (Network)
```bash
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-core.yaml

kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.14.0/kourier.yaml
kubectl patch configmap/config-network -n knative-serving \
  --type merge --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
```

#### Adım 3 — Knative Eventing & Broker
```bash
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-core.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/in-memory-channel.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/mt-channel-broker.yaml
```

#### Adım 4 — Proje Manifestoları
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/broker.yaml
kubectl apply -f k8s/ksvc.yaml
kubectl apply -f k8s/producer-deployment.yaml
kubectl apply -f k8s/sinkbinding.yaml
kubectl apply -f k8s/triggers.yaml
kubectl apply -f k8s/frontend-deployment.yaml
```
#### Adım 5 — Port-Forward (Manuel Erişim)
Terminalde aşağıdaki komutları çalıştırarak arayüzlere erişebilirsiniz. (Her biri için ayrı terminal açmanız gerekebilir veya komutların sonuna `&` ekleyebilirsiniz).

```bash
# Frontend arayüzü (localhost:3000)
kubectl port-forward svc/frontend-service 3000:80 -n banking-system

# Producer API (localhost:8000/api/docs)
kubectl port-forward svc/producer-api-service 8000:8000 -n banking-system
```

#### Adım 6 — Log İzleme
Servislerin loglarını ve podların otomatik oluşturulup silinmesini (scale-to-zero) izlemek için ayrı terminallerde şu komutları kullanabilirsiniz:

```bash
# Scale-to-zero pod değişimlerini canlı izle
kubectl get pods -n banking-system -w

# Standart/Orta riskli işlemleri loglayan servis
kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f

# Yüksek/Kritik riskli işlemleri (Fraud) loglayan servis
kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f
```

---

## ⚡ CloudEvent Akışı

| İşlem Tipi | CE Type | Risk Level | Consumer |
|---|---|---|---|
| Standart EFT/Havale | `banking.transaction` | `low` | `transaction-logger-service` |
| Kredi Kartı Harcaması | `banking.transaction` | `medium` | `transaction-logger-service` |
| Şüpheli Transfer | `banking.suspicious` | `high` | `fraud-alert-service` |
| Yurtdışı ATM Çekimi | `banking.suspicious` | `critical` | `fraud-alert-service` |

---

## 🔑 Temel Kavramlar

### SinkBinding — Hardcoded URL Yok
```yaml
# sinkbinding.yaml
spec:
  subject:
    kind: Deployment
    name: producer-api     # Bu deployment'a inject edilir
  sink:
    ref:
      kind: Broker
      name: banking-broker  # Broker URL'i → K_SINK olarak inject edilir
```

```python
# producer/main.py — K_SINK env variable'dan okunur
sink_url = os.environ.get("K_SINK")  # Knative inject eder
```

### Scale-to-Zero
```yaml
# ksvc.yaml
annotations:
  autoscaling.knative.dev/min-scale: "0"   # ← Scale-to-zero aktif
  autoscaling.knative.dev/max-scale: "3"
  autoscaling.knative.dev/target: "10"     # Concurrent request/pod
```

---

## ☁️ CI/CD (GitHub Actions)

### Gerekli Secrets

| Secret | Açıklama |
|---|---|
| `DOCKER_HUB_USER` | Docker Hub kullanıcı adı |
| `DOCKER_HUB_TOKEN` | Docker Hub access token |
| `KUBE_CONFIG_DATA` | `base64 -w0 ~/.kube/config` çıktısı |

### Pipeline Akışı

```
Push to main
    │
    ├─► test (parallel matrix: producer, tx-logger, fraud-alert)
    │       └─► flake8 lint + import smoke test
    │
    ├─► build-push (parallel: 4 Docker images)
    │       └─► multi-arch (amd64 + arm64) → Docker Hub
    │
    └─► deploy
            ├─► Image tag patch (SHA → manifests)
            ├─► kubectl apply (sıralı)
            └─► Rollout status verify
```

---

## 🧪 Test Rehberi

Sistem deploy edildikten sonra aşağıdaki adımları **sırayla** takip edin.

---

### Adım 1 — Bileşenler Hazır mı? (1 Terminal)

Önce her şeyin ayakta olup olmadığını kontrol edin:

```bash
kubectl get broker,trigger,ksvc,sinkbinding -n banking-system
```

Her satırda `READY = True` yazıyor olmalı. Henüz `False` görüyorsanız 30 saniye bekleyip tekrar çalıştırın.

---

### Adım 2 — Producer'ın K_SINK Aldığını Doğrula (1 Terminal)

SinkBinding çalışıyorsa producer pod'unun içinde `K_SINK` değişkeni otomatik set edilmiş olmalıdır:

```bash
kubectl exec -n banking-system deploy/producer-api -- env | grep K_SINK
```

Çıktı şöyle bir şey göstermelidir:

```
K_SINK=http://banking-broker-ingress.banking-system.svc.cluster.local/...
```

Eğer `K_SINK` çıktısı boşsa SinkBinding henüz işlenmemiş demektir — 1 dakika bekleyip tekrar deneyin.

---

### Adım 3 — Scale-to-Zero Başlangıç Kontrolü (1 Terminal)

Consumer servisler işlem gelmediğinde sıfır pod ile çalışır. Bunu doğrulamak için:

```bash
kubectl get pods -n banking-system
```

Listede yalnızca `producer-api-...` ve `frontend-...` pod'ları görünmeli.  
`transaction-logger` veya `fraud-alert` pod'ları **henüz olmamalı** — bu normal ve beklenen davranıştır.

---

### Adım 4 — 3 Terminal Penceresi Aç

Test sırasında aynı anda üç ayrı terminal penceresi açık olmalıdır:

**Terminal A — Pod değişimlerini canlı izle:**
```bash
kubectl get pods -n banking-system -w
```
> Bu terminali açık bırakın. Butona her tıkladığınızda yeni pod'ların `Running` durumuna geçtiğini burada göreceksiniz.

**Terminal B — Standart işlem logları (TX Logger):**
```bash
kubectl logs -n banking-system \
  -l serving.knative.dev/service=transaction-logger-service \
  --prefix -f
```
> `EFT` ve `Kredi Kartı` butonlarına bastığınızda bu terminalde JSON formatında log çıktısı gelecek.

**Terminal C — Fraud uyarı logları:**
```bash
kubectl logs -n banking-system \
  -l serving.knative.dev/service=fraud-alert-service \
  --prefix -f
```
> `Şüpheli Transfer` ve `Yurtdışı ATM` butonlarına bastığınızda bu terminalde kırmızı renkli FRAUD uyarısı çıkacak.

---

### Adım 5 — Web Arayüzünü Aç

Tarayıcıda aşağıdaki adrese gidin:

```bash
# Minikube IP'yi öğren:
minikube ip
```

```
http://<MINIKUBE_IP>:30080
```

Örneğin IP `192.168.49.2` ise adres: `http://192.168.49.2:30080`

---

### Adım 6 — İşlem Senaryolarını Test Et

#### Senaryo 1 — Standart EFT / Havale
1. Arayüzde **"Standart EFT / Havale"** butonuna tıklayın
2. **Terminal A'da:** `transaction-logger-service-...` adında yeni bir pod `0/1 Running → 1/1 Running` durumuna geçer
3. **Terminal B'de:** İşlemin JSON log çıktısı gelir (tutar, IBAN, müşteri ID vb.)
4. Sayfadaki stat kutularında `Toplam İşlem` ve `Başarılı Event` sayacı artar

#### Senaryo 2 — Kredi Kartı Harcaması
1. **"Kredi Kartı Harcaması"** butonuna tıklayın
2. **Terminal B'de:** `risk_level: medium` etiketli log çıktısı gelir
3. Eğer TX Logger pod'u hâlâ ayaktaysa (30 sn geçmemişse) anında yanıt verir

#### Senaryo 3 — Şüpheli Transfer (Fraud)
1. **"Yüklü Şüpheli Transfer"** butonuna tıklayın
2. **Terminal A'da:** `fraud-alert-service-...` pod'u ilk kez ayağa kalkar
3. **Terminal C'de:** Kırmızı çerçeveli `🚨 YÜKSEK RİSKLİ İŞLEM` uyarısı gelir
4. Sayfadaki `Fraud Uyarısı` sayacı artar

#### Senaryo 4 — Yurtdışı ATM Çekimi (Kritik)
1. **"Yurtdışı ATM Çekimi"** butonuna tıklayın
2. **Terminal C'de:** Kırmızı çerçeveli `🔴 KRİTİK FRAUD UYARISI` mesajı çıkar
3. Destination country, IP adresi ve device fingerprint bilgileri de loglanır

---

### Adım 7 — Scale-to-Zero Geri Dönüşünü İzle

Hiçbir butona **2 dakika** basmayın. **Terminal A'da** şunu görürsünüz:

```
fraud-alert-service-...   1/1   Running     →   Terminating   →   (silindi)
transaction-logger-...    1/1   Running     →   Terminating   →   (silindi)
```

Pod'lar kapanır, `kubectl get pods` çıktısı yeniden sadece `producer-api` ve `frontend` gösterir.  
Sonraki işlemde pod tekrar sıfırdan ayağa kalkar — bu Knative'in **Scale-to-Zero** özelliğidir.

---

### Adım 8 — curl ile Doğrudan API Testi (Opsiyonel)

Tarayıcı olmadan terminal üzerinden de test edebilirsiniz:

```bash
# Önce port-forward başlat (ayrı bir terminal):
kubectl port-forward svc/producer-api-service 8000:8000 -n banking-system

# Standart işlem testi:
curl -s -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"transaction_type": "standard_eft", "payload": {"amount": 5000, "currency": "TRY"}}' | python -m json.tool

# Fraud testi:
curl -s -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"transaction_type": "overseas_atm_withdrawal", "payload": {"amount": 75000, "currency": "USD"}}' | python -m json.tool
```

Başarılı yanıt şu şekilde görünür:

```json
{
  "status": "accepted",
  "event_type": "banking.suspicious",
  "risk_level": "critical",
  "sink": "http://banking-broker-ingress..."
}
```

Ayrıca Swagger UI üzerinden de test edebilirsiniz: `http://localhost:8000/api/docs`


