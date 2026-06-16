#!/bin/bash
# build_push.sh — Build and push WAF-GUARD images to Azure Container Registry
# Usage:
#   ./build_push.sh <acr-name>           # build + push all services
#   ./build_push.sh <acr-name> fastapi   # build + push a single service
set -e

ACR_NAME="${1:?Usage: ./build_push.sh <acr-name> [service]}"
SERVICE="$2"

declare -A SERVICES=(
  [fastapi]="docker/fastapi_dockerfile"
  [streamlit]="docker/streamlit_dockerfile"
  [waf]="docker/waf_dockerfile"
  [analyzer]="docker/analyzer_dockerfile"
  [chatbot]="docker/chatbot_dockerfile"
  # [postgres]="docker/postgres_dockerfile"
)

az acr login --name "$ACR_NAME"

for name in "${!SERVICES[@]}"; do
  [[ -n "$SERVICE" && "$name" != "$SERVICE" ]] && continue
  echo ">>> Building and pushing $name..."
  docker build -t "${ACR_NAME}.azurecr.io/${name}:latest" -f "${SERVICES[$name]}" .
  docker push "${ACR_NAME}.azurecr.io/${name}:latest"
done

echo "Done. All requested images pushed to ${ACR_NAME}.azurecr.io"
