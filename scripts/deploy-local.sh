#!/usr/bin/env bash
# ==============================================================================
#  scripts/deploy-local.sh
#  VakıfBank Knative — Local Deploy Script
#
#  GitHub Actions CI tamamlandıktan sonra bu script çalıştırılır.
#  Docker Hub'daki yeni image'ları Minikube'a çeker ve deploy eder.
#
#  Kullanım:
#    ./scripts/deploy-local.sh <IMAGE_TAG>
#
#  Örnekler:
#    ./scripts/deploy-local.sh sha-a1b2c3d
#    ./scripts/deploy-local.sh latest
# ==============================================================================
set -euo pipefail

# Windows Bash Compatibility
if ! command -v kubectl &>/dev/null && command -v kubectl.exe &>/dev/null; then kubectl() { kubectl.exe "$@"; }; fi
if ! command -v minikube &>/dev/null && command -v minikube.exe &>/dev/null; then minikube() { minikube.exe "$@"; }; fi


CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
log_step()    { echo -e "\n${BOLD}${GREEN}━━━ $* ━━━${NC}\n"; }

# ── Argüman Kontrolü ──────────────────────────────────────────────────────────
if [[ $# -gt 1 ]]; then
  echo -e "${BOLD}Kullanım:${NC} $0 [IMAGE_TAG]"
  echo ""
  echo "Örnekler:"
  echo "  $0 sha-a1b2c3d    # CI'dan gelen SHA tag"
  echo "  $0                # latest tag (varsayılan)"
  exit 1
fi

DOCKER_HUB_USER="sweizn"
IMAGE_TAG="${1:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TMP_DIR="${PROJECT_ROOT}/.deploy-tmp"

echo -e "\n${BOLD}${CYAN}VakıfBank Knative — Local Deploy${NC}"
echo -e "  Docker Hub User : ${CYAN}${DOCKER_HUB_USER}${NC}"
echo -e "  Image Tag       : ${CYAN}${IMAGE_TAG}${NC}\n"

# ── 1. Minikube Kontrol ───────────────────────────────────────────────────────
log_step "Minikube durumu atlanıyor (kubectl üzerinden devam edilecek)"

# ── 2. Temp Klasör ve YAML Kopyalama ─────────────────────────────────────────
log_step "YAML dosyaları image tag ile hazırlanıyor"

rm -rf "$TMP_DIR"
cp -r "$PROJECT_ROOT/k8s" "$TMP_DIR"

# ksvc.yaml — transaction-logger ve fraud-alert
sed -i \
  "s|docker.io/sweizn/transaction-logger:latest|docker.io/${DOCKER_HUB_USER}/transaction-logger:${IMAGE_TAG}|g" \
  "${TMP_DIR}/ksvc.yaml"
sed -i \
  "s|docker.io/sweizn/fraud-alert:latest|docker.io/${DOCKER_HUB_USER}/fraud-alert:${IMAGE_TAG}|g" \
  "${TMP_DIR}/ksvc.yaml"

# producer-deployment.yaml
sed -i \
  "s|docker.io/sweizn/producer-api:latest|docker.io/${DOCKER_HUB_USER}/producer-api:${IMAGE_TAG}|g" \
  "${TMP_DIR}/producer-deployment.yaml"

# frontend-deployment.yaml
sed -i \
  "s|docker.io/sweizn/frontend:latest|docker.io/${DOCKER_HUB_USER}/frontend:${IMAGE_TAG}|g" \
  "${TMP_DIR}/frontend-deployment.yaml"

log_success "YAML'lar güncellendi (${TMP_DIR})"

# ── 3. Manifoları Deploy Et ───────────────────────────────────────────────────
log_step "Kubernetes & Knative manifoları uygulanıyor"

pushd "$TMP_DIR" > /dev/null

log_info "Namespace..."
kubectl apply -f namespace.yaml

log_info "ConfigMap..."
kubectl apply -f configmap.yaml

log_info "Broker..."
kubectl apply -f broker.yaml

log_info "Knative Services (scale-to-zero)..."
kubectl apply -f ksvc.yaml

log_info "Producer Deployment..."
kubectl apply -f producer-deployment.yaml

log_info "SinkBinding (K_SINK inject)..."
kubectl apply -f sinkbinding.yaml

log_info "Triggers (event routing)..."
kubectl apply -f triggers.yaml

log_info "Frontend..."
kubectl apply -f frontend-deployment.yaml

popd > /dev/null

# ── 4. Rollout Bekle ──────────────────────────────────────────────────────────
log_step "Producer rollout bekleniyor"
kubectl rollout status deployment/producer-api \
  -n banking-system --timeout=120s

log_step "Frontend rollout bekleniyor"
kubectl rollout status deployment/frontend \
  -n banking-system --timeout=120s

# ── 5. Broker & Trigger Durumu ────────────────────────────────────────────────
log_step "Sistem durumu"

echo -e "${BOLD}Broker & Trigger:${NC}"
kubectl get broker,trigger -n banking-system 2>/dev/null || true

echo -e "\n${BOLD}Knative Services (ksvc):${NC}"
kubectl get ksvc -n banking-system 2>/dev/null || true

echo -e "\n${BOLD}SinkBinding:${NC}"
kubectl get sinkbinding -n banking-system 2>/dev/null || true

echo -e "\n${BOLD}Podlar:${NC}"
kubectl get pods -n banking-system 2>/dev/null || true

# ── 6. Erişim Bilgileri ───────────────────────────────────────────────────────
MINIKUBE_IP=$(minikube.exe ip 2>/dev/null || minikube ip 2>/dev/null || echo "localhost")

echo ""
log_success "Deploy tamamlandı!"
echo ""
echo -e "${BOLD}Erişim Adresleri:${NC}"
echo -e "  🌐 Frontend   → ${CYAN}http://${MINIKUBE_IP}:30080${NC}"
echo ""
echo -e "${BOLD}Log İzleme (3 ayrı terminal aç):${NC}"
echo -e "  ${CYAN}kubectl get pods -n banking-system -w${NC}"
echo -e "  ${CYAN}kubectl logs -n banking-system -l serving.knative.dev/service=transaction-logger-service --prefix -f${NC}"
echo -e "  ${CYAN}kubectl logs -n banking-system -l serving.knative.dev/service=fraud-alert-service --prefix -f${NC}"
echo ""

# ── Temp klasörü temizle ──────────────────────────────────────────────────────
rm -rf "$TMP_DIR"
