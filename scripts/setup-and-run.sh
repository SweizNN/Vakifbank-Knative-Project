#!/usr/bin/env bash
# ==============================================================================
#  scripts/setup-and-run.sh
#  VakıfBank Knative — Tek Tıkla Kurulum ve İzleme
# ==============================================================================
set -e

# Windows Git Bash için .exe alias ayarları
shopt -s expand_aliases
if ! command -v kubectl &> /dev/null && command -v kubectl.exe &> /dev/null; then
  alias kubectl="kubectl.exe"
fi

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "\n${BOLD}${CYAN}VakıfBank Knative — Otomatik Kurulum ve İzleme Başlıyor...${NC}\n"

# 1. Knative Kurulumu
echo -e "${YELLOW}Knative ve Kourier (Network) Kuruluyor...${NC}"
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.14.0/serving-core.yaml
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.14.0/kourier.yaml
kubectl patch configmap/config-network -n knative-serving \
  --type merge --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

echo -e "${YELLOW}Knative Eventing ve In-Memory Channel Kuruluyor...${NC}"
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-core.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/in-memory-channel.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/mt-channel-broker.yaml

# 2. Proje Kurulumu
echo -e "${YELLOW}Banking System Manifestoları Kuruluyor...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/broker.yaml
kubectl apply -f k8s/ksvc.yaml
kubectl apply -f k8s/producer-deployment.yaml
kubectl apply -f k8s/sinkbinding.yaml
kubectl apply -f k8s/triggers.yaml
kubectl apply -f k8s/frontend-deployment.yaml

echo -e "\n${GREEN}Tüm manifestolar uygulandı. İzleme moduna geçiliyor...${NC}"
echo -e "${CYAN}(Durdurmak için Ctrl+C'ye basabilirsiniz)${NC}\n"

# Ctrl+C yapıldığında arka plandaki işlemleri de kapatması için trap
trap 'echo -e "\n${RED}İşlemler durduruluyor...${NC}"; kill $(jobs -p) 2>/dev/null; exit' SIGINT SIGTERM

# 3. Arka Planda Port-Forward
echo -e "${BOLD}Port-Forwarding başlatılıyor...${NC}"
kubectl port-forward svc/frontend-service 3000:80 -n banking-system &
kubectl port-forward svc/producer-api-service 8000:8000 -n banking-system &

# Biraz bekle (Port-forward'ın oturması için)
sleep 2

# 4. İzleme Terminallerini Başlat (Windows PowerShell üzerinden 3 ayrı pencere açar)
echo -e "\n${BOLD}================ İzleme Ekranı =================${NC}"
echo -e "🌐 Frontend Arayüzü : http://localhost:3000"
echo -e "📖 Producer API Docs: http://localhost:8000/api/docs"
echo -e "${BOLD}================================================${NC}\n"

echo -e "${YELLOW}Logları izlemek için 3 yeni PowerShell penceresi açılıyor...${NC}\n"
echo -e "${CYAN}Lütfen açılan siyah/mavi pencereleri kapatmayın ve yan yana dizin.${NC}\n"

# Pod değişimleri
cmd.exe /c start powershell -NoExit -Command "[console]::BackgroundColor='Black'; [console]::ForegroundColor='White'; Clear-Host; Write-Host '--- TERMINAL A (Pod İzleme) ---' -ForegroundColor Cyan; kubectl get pods -n banking-system -w"

# Transaction logger
cmd.exe /c start powershell -NoExit -Command "[console]::BackgroundColor='Black'; [console]::ForegroundColor='White'; Clear-Host; Write-Host '--- TERMINAL B (Standart Islemler) ---' -ForegroundColor Yellow; while (\$true) { kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f; Start-Sleep -Seconds 2 }"

# Fraud alert
cmd.exe /c start powershell -NoExit -Command "[console]::BackgroundColor='Black'; [console]::ForegroundColor='White'; Clear-Host; Write-Host '--- TERMINAL C (Fraud - Supheli Islemler) ---' -ForegroundColor Red; while (\$true) { kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f; Start-Sleep -Seconds 2 }"

# Ana script sadece port-forward işlemlerini tutar
wait
