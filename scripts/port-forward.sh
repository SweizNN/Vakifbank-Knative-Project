#!/usr/bin/env bash
# ==============================================================================
#  scripts/port-forward.sh
#  Geliştirme ortamında port-forward başlatır (arka planda)
#
#  Kullanım: ./scripts/port-forward.sh
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }

echo -e "\n${BOLD}VakıfBank Knative — Port Forward${NC}\n"

# Önceki port-forward process'leri temizle
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

# Frontend
log_info "Frontend: http://localhost:3000"
kubectl port-forward svc/frontend-service 3000:80 \
  -n banking-system &>/tmp/pf-frontend.log &

# Producer API
log_info "Producer API: http://localhost:8000"
kubectl port-forward svc/producer-api-service 8000:8000 \
  -n banking-system &>/tmp/pf-producer.log &

# Knative Kourier (Serving gateway)
log_info "Knative Gateway: http://localhost:8080"
kubectl port-forward svc/kourier \
  -n kourier-system 8080:80 &>/tmp/pf-kourier.log &

sleep 2
log_success "Port-forward başlatıldı!"
echo ""
echo -e "  🌐 Frontend    → ${CYAN}http://localhost:3000${NC}"
echo -e "  ⚡ Producer    → ${CYAN}http://localhost:8000/health${NC}"
echo -e "  📖 API Docs    → ${CYAN}http://localhost:8000/api/docs${NC}"
echo -e "  📡 Knative GW  → ${CYAN}http://localhost:8080${NC}"
echo ""
echo -e "${YELLOW}Durdurmak için: pkill -f 'kubectl port-forward'${NC}"
echo ""

# Log izleme (opsiyonel)
echo -e "Log izlemek ister misiniz? (${CYAN}y${NC}/n)"
read -r ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  echo ""
  echo -e "${BOLD}TX Logger & Fraud Alert logları (Ctrl+C ile çık):${NC}"
  kubectl logs -n banking-system \
    -l "app.kubernetes.io/part-of=vakifbank-knative-demo" \
    --prefix --all-containers -f 2>/dev/null || \
  echo -e "${YELLOW}Henüz pod yok (scale-to-zero). İşlem gönderince pod ayağa kalkacak.${NC}"
fi
