# 🏦 VakıfBank — Event-Driven Banking Transaction & Fraud Detection

**Kubernetes + Knative Serving & Eventing** tabanlı, olay güdümlü bankacılık işlem ve dolandırıcılık tespit sistemi. TEST

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
│       ├── deploy.yml              # CI Pipeline (GitHub Actions)
│       └── cd.yml                  # Remote CD Pipeline (DigitalOcean Droplet Deploy)
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
│   ├── configmap.yaml              # Centralized environment ConfigMap
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

## 🌍 Canlı Ortam (DigitalOcean Prodüksiyon)

Sistem, GitHub Actions üzerinden tam otomatik CD (Continuous Deployment) ile DigitalOcean sunucunuzda (IP: `http://134.122.61.206:30080`) çalışmak üzere yapılandırılmıştır.

### Sistemi Canlıya Alma
Sistemin güncellenmesi ve canlıya alınması için **sunucuda manuel hiçbir işlem yapmanıza gerek yoktur**. Kodlarınızı GitHub'a gönderdiğinizde her şey otomatik gerçekleşir:
```bash
git add .
git commit -m "update"
git push origin main
```

### Canlı Sistemi Test Etme ve İzleme
Uygulamanızın canlı arayüzüne her zaman şu adresten erişebilirsiniz:
👉 **[http://134.122.61.206:30080](http://134.122.61.206:30080)**

Sunucu üzerinde arka planda dönen olayları (Knative Scale-to-Zero tetiklenmeleri, loglar vb.) izlemek için sunucunuza SSH ile bağlanın (`ssh root@134.122.61.206`) ve aşağıdaki komutları kullanın:

- **Podların otomatik çoğalıp kapanmasını izlemek için:** 
  `kubectl get pods -n banking-system -w`
- **İşlem loglarını canlı (tail) izlemek için:** 
  `kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f`
- **Şüpheli (Fraud) işlem uyarısı loglarını izlemek için:** 
  `kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f`

---

## 💻 Yerel Geliştirme (Kendi Bilgisayarınızda Hızlı Başlangıç)

Sistemi ayağa kaldırmak ve test etmek için iki seçeneğiniz vardır: Otomatik veya Manuel.
Öncelikle aşağıdaki araçların sisteminizde yüklü olduğundan emin olun:

```bash
# Versiyon kontrolleri
minikube version   # >= 1.33
kubectl version    # >= 1.28
docker version     # >= 24
```

---

### 🟢 SEÇENEK A: Otomatik Kurulum ve İzleme (Tavsiye Edilen)

Bu yöntem tüm gereksinimleri kurar ve logları izlemek için otomatik olarak 3 yeni terminal (PowerShell) penceresi açar.

**1. Scripti Çalıştırın**
```bash
chmod +x scripts/setup-and-run.sh
bash ./scripts/setup-and-run.sh
```

**2. Test Arayüzüne Girin**
Tarayıcınızda şu adresi açın: `http://localhost:3000`

**3. Logları İzleyin ve Test Edin**
- Script, logları izlemeniz için 3 ayrı renkli terminal penceresi açacaktır (Terminal A, B ve C).
- Web sayfasındaki butonlara ("EFT", "Fraud" vb.) tıkladıkça bu pencerelerde logların anlık olarak aktığını göreceksiniz.
- İşlemi bitirmek için ana terminalde `Ctrl+C` yapabilirsiniz.

*(Not: CI/CD sürecini test etmek istiyorsanız, kodlarınızı GitHub'a push attıktan sonra `bash ./scripts/deploy-local.sh sha-XXXX` komutunu çalıştırarak Kubernetes'i güncelleyebilirsiniz).*

---

### 🟡 SEÇENEK B: Manuel Kurulum ve Adım Adım Test

Eğer arka planda neler olduğunu görmek ve her şeyi kendi kontrolünüzde (manuel komutlarla) yapmak istiyorsanız bu adımları izleyin.

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
Tarayıcıdan erişmek için yeni bir terminalde çalıştırın (kapatmayın):
```bash
kubectl port-forward svc/frontend-service 3000:80 -n banking-system
kubectl port-forward svc/producer-api-service 8000:8000 -n banking-system
```
Artık tarayıcıdan `http://localhost:3000` adresine girebilirsiniz.

#### Adım 6 — Manuel Log İzleme (3 Terminal)
Test sırasında aynı anda üç ayrı terminal penceresi açın:

**Terminal A — Pod değişimlerini canlı izle (Scale-to-Zero):**
```bash
kubectl get pods -n banking-system -w
```
**Terminal B — Standart işlem logları (TX Logger):**
```bash
kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f
```
**Terminal C — Fraud uyarı logları:**
```bash
kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f
```

---

## 🧪 Test Senaryoları (İki Kurulum İçin de Geçerlidir)

Arayüz (`http://localhost:3000`) üzerinden aşağıdaki senaryoları test edebilirsiniz:

#### Senaryo 1 — Standart EFT / Havale
1. Arayüzde **"Standart EFT / Havale"** butonuna tıklayın.
2. **Terminal A'da:** `transaction-logger-service-...` pod'u 0'dan 1'e çıkarak ayağa kalkar.
3. **Terminal B'de:** İşlemin detaylı JSON log çıktısı görünür.

#### Senaryo 2 — Kredi Kartı Harcaması
1. **"Kredi Kartı Harcaması"** butonuna tıklayın.
2. **Terminal B'de:** `risk_level: medium` etiketli JSON log çıktısı görünür.
3. Pod zaten ayaktaysa işlem sıfır gecikmeyle (milisaniyeler içinde) gerçekleşir.

#### Senaryo 3 — Şüpheli Transfer (Fraud)
1. **"Yüklü Şüpheli Transfer"** butonuna tıklayın.
2. **Terminal A'da:** `fraud-alert-service-...` pod'u ilk kez ayağa kalkar.
3. **Terminal C'de:** Kırmızı renkli `🚨 YÜKSEK RİSKLİ İŞLEM` uyarısı çıkar.

#### Senaryo 4 — Yurtdışı ATM Çekimi (Kritik)
1. **"Yurtdışı ATM Çekimi"** butonuna tıklayın.
2. **Terminal C'de:** Kırmızı renkli `🔴 KRİTİK FRAUD UYARISI` mesajı çıkar.

---
