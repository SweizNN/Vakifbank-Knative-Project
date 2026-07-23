#!/usr/bin/env bash
# ==============================================================================
#  scripts/setup-and-run.sh
#  VakıfBank Knative — Tek Tıkla Kurulum ve İzleme
#  Kullanım: bash ./scripts/setup-and-run.sh
# ==============================================================================
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

# Windows Git Bash uyumluluğu (.exe wrappers)
if ! command -v kubectl &>/dev/null && command -v kubectl.exe &>/dev/null; then
  kubectl() { kubectl.exe "$@"; }; export -f kubectl
fi
if ! command -v minikube &>/dev/null && command -v minikube.exe &>/dev/null; then
  minikube() { minikube.exe "$@"; }; export -f minikube
fi

echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║   VakıfBank Knative — Sistem Başlatılıyor  ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${NC}\n"

# ── 1. Knative (sadece ilk seferinde kurulur) ──────────────────────────────
if ! kubectl get ns knative-serving &>/dev/null; then
  echo -e "${YELLOW}[1/4] Knative Serving + Kourier kuruluyor (ilk kurulum)...${NC}"
  kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-crds.yaml
  kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-core.yaml
  kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.14.0/kourier.yaml
  kubectl patch configmap/config-network -n knative-serving \
    --type merge --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
  echo -e "${YELLOW}[1/4] Knative Eventing kuruluyor...${NC}"
  kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-crds.yaml
  kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-core.yaml
  kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/in-memory-channel.yaml
  kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/mt-channel-broker.yaml
  echo -e "${GREEN}[1/4] Knative kuruldu!${NC}"
else
  echo -e "${GREEN}[1/4] Knative zaten kurulu — atlanıyor.${NC}"
fi

# ── 2. Yerel kodları Minikube'a derle ──────────────────────────────────────
echo -e "${YELLOW}[2/4] Yerel kodlar derleniyor...${NC}"
LOCAL_TAG="local-$(date +%s)"
minikube image build -t sweizn/frontend:${LOCAL_TAG} ./frontend
minikube image build -t sweizn/producer-api:${LOCAL_TAG} ./producer
minikube image build -t sweizn/transaction-logger:${LOCAL_TAG} ./services/transaction-logger
minikube image build -t sweizn/fraud-alert:${LOCAL_TAG} ./services/fraud-alert
echo -e "${GREEN}[2/4] Derleme tamamlandı!${NC}"

# ── 3. Kubernetes manifestolarını uygula ───────────────────────────────────
echo -e "${YELLOW}[3/4] Kubernetes manifestoları uygulanıyor...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/broker.yaml

# Dinamik tag ataması (cache sorununu çözer)
sed "s/:latest/:${LOCAL_TAG}/g" k8s/ksvc.yaml | kubectl apply -f -
sed "s/:latest/:${LOCAL_TAG}/g" k8s/producer-deployment.yaml | kubectl apply -f -
sed "s/:latest/:${LOCAL_TAG}/g" k8s/frontend-deployment.yaml | kubectl apply -f -

kubectl apply -f k8s/sinkbinding.yaml
kubectl apply -f k8s/triggers.yaml

# Podların hazır olmasını bekle
echo -e "${YELLOW}Podlar hazır olana kadar bekleniyor...${NC}"
kubectl rollout status deploy/frontend -n banking-system --timeout=120s
kubectl rollout status deploy/producer-api -n banking-system --timeout=120s
echo -e "${GREEN}[3/4] Tüm manifestolar uygulandı!${NC}"

# ── 4. Port-forward başlat ─────────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Port-forwarding başlatılıyor...${NC}"

# Önce varsa eski port-forward işlemlerini temizle
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

# Otomatik yeniden bağlanmalı port-forward döngüleri
(while true; do kubectl port-forward svc/frontend-service 3000:80 -n banking-system 2>/dev/null || true; sleep 2; done) &
(while true; do kubectl port-forward svc/producer-api-service 8000:8000 -n banking-system 2>/dev/null || true; sleep 2; done) &

sleep 3
echo -e "${GREEN}[4/4] Port-forwarding aktif!${NC}"

# ── Bilgi Ekranı ───────────────────────────────────────────────────────────
echo -e "\n${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║           SİSTEM HAZIR!                    ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
echo -e "  🌐 Frontend Arayüzü : ${CYAN}http://localhost:3000${NC}"
echo -e "  📖 Producer API Docs: ${CYAN}http://localhost:8000/api/docs${NC}"
echo -e ""
echo -e "${YELLOW}Log izleme pencereleri açılıyor...${NC}"
echo -e "${CYAN}Bu terminali KAPATMA — bağlantı bu terminalde çalışıyor.${NC}"
echo -e "${CYAN}Durdurmak için Ctrl+C yapın.${NC}\n"

# İzleme pencerelerini aç
cmd.exe /c start powershell -NoExit -Command "Write-Host '=== POD IZLEME ===' -ForegroundColor Cyan; kubectl get pods -n banking-system -w"
cmd.exe /c start powershell -NoExit -Command "Write-Host '=== TX LOGGER ===' -ForegroundColor Yellow; while (\$true) { kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f 2>\$null; Start-Sleep -Seconds 2 }"
cmd.exe /c start powershell -NoExit -Command "Write-Host '=== FRAUD ALERT ===' -ForegroundColor Red; while (\$true) { kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f 2>\$null; Start-Sleep -Seconds 2 }"

# Ctrl+C ile her şeyi temizle
trap 'echo -e "\n${RED}Durduruluyor...${NC}"; pkill -f "kubectl port-forward" 2>/dev/null; exit 0' SIGINT SIGTERM

# Port-forward döngüsü çalışmaya devam etsin
wait
