#!/bin/bash
# Update the K8s secret from .env without rebuilding the image.
# kind/Codespace path only (the sandbox uses deploy-spark.sh).
# Preserves the existing SECRET_KEY to avoid breaking encrypted SMTP passwords.
#
# Usage: bash scripts/update-secret.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${REPO_DIR}/.env"

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: .env file not found at ${ENV_FILE}"
  exit 1
fi

# Source .env
while IFS= read -r line; do
  line="${line//$'\r'/}"
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  value="${value%%#*}"
  value="${value#\"}" ; value="${value%\"}"
  value="${value#\'}" ; value="${value%\'}"
  value="${value%"${value##*[![:space:]]}"}"
  [[ -z "$key" || "$key" =~ [[:space:]] ]] && continue
  [[ -z "$value" && -n "${!key:-}" ]] && continue
  export "$key=$value"
done < "${ENV_FILE}"

LITELLM_BASE_URL="${LITELLM_BASE_URL:?ERROR: LITELLM_BASE_URL not set in .env or the environment}"
LITELLM_API_KEY="${LITELLM_API_KEY:?ERROR: LITELLM_API_KEY not set in .env or the environment}"
AUTH_PASSWORD="${AUTH_PASSWORD:-brainupgrade}"
LLM_PROVIDER="${LLM_PROVIDER:-litellm}"
LLM_MODEL="${LLM_MODEL:-${LITELLM_MODEL:-qwen36-35b-a3b-lab}}"

# Preserve existing SECRET_KEY to avoid breaking Fernet-encrypted values in DB
echo "==> Preserving existing SECRET_KEY from cluster..."
EXISTING_SECRET_KEY=$(kubectl get secret frontdeskai-secret \
  -o jsonpath='{.data.SECRET_KEY}' 2>/dev/null | base64 -d || echo "")

if [ -z "${EXISTING_SECRET_KEY}" ]; then
  echo "    No existing SECRET_KEY found — generating a new one"
  EXISTING_SECRET_KEY="$(head -c 32 /dev/urandom | base64)"
else
  echo "    SECRET_KEY preserved"
fi

SECRET_ARGS=(
  --from-literal=AUTH_PASSWORD="${AUTH_PASSWORD}"
  --from-literal=SECRET_KEY="${EXISTING_SECRET_KEY}"
  --from-literal=LLM_PROVIDER="${LLM_PROVIDER}"
  --from-literal=LLM_MODEL="${LLM_MODEL}"
  --from-literal=LITELLM_BASE_URL="${LITELLM_BASE_URL}"
  --from-literal=LITELLM_API_KEY="${LITELLM_API_KEY}"
  --from-literal=LLM_FALLBACK_PROVIDER="${LLM_FALLBACK_PROVIDER:-}"
  --from-literal=LLM_FALLBACK_MODEL="${LLM_FALLBACK_MODEL:-}"
)

# Langfuse — include only if all three vars are set
LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
LANGFUSE_HOST="${LANGFUSE_HOST:-}"

if [ -n "${LANGFUSE_SECRET_KEY}" ] && [ -n "${LANGFUSE_PUBLIC_KEY}" ] && [ -n "${LANGFUSE_HOST}" ]; then
  SECRET_ARGS+=(
    --from-literal=LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY}"
    --from-literal=LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY}"
    --from-literal=LANGFUSE_HOST="${LANGFUSE_HOST}"
  )
  echo "==> Langfuse keys included"
else
  echo "==> WARNING: Langfuse keys missing in .env — Langfuse will be disabled"
fi

echo "==> Updating secret frontdeskai-secret..."
kubectl create secret generic frontdeskai-secret \
  "${SECRET_ARGS[@]}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> Restarting deployment to pick up new secret..."
kubectl rollout restart deployment/frontdeskai

echo "==> Waiting for rollout..."
kubectl rollout status deployment/frontdeskai --timeout=120s

echo ""
echo "==> Verifying Langfuse status in logs..."
sleep 3
kubectl logs deployment/frontdeskai | grep -i langfuse || echo "    (no langfuse log line yet — try: kubectl logs deployment/frontdeskai | grep -i langfuse)"
