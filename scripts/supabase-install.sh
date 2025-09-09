#!/usr/bin/env bash
set -euo pipefail
NS="supabase"
REL="supabase"
CHART="/command-files/supabase-0.1.3.tgz"
VALS="/command-files/supabase-aks-values.yaml"

kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -

set -x
helm upgrade --install "$REL" "$CHART" \
  --namespace "$NS" \
  --create-namespace \
  -f "$VALS" \
  --timeout=15m \
  --wait \
  --debug || INSTALL_ERR=$?
set +x

if [ -n "${INSTALL_ERR:-}" ]; then
  echo "--- Helm Status ---"; helm -n "$NS" status "$REL" || true
  echo "--- Pods ---"; kubectl -n "$NS" get pods || true
  echo "--- Events ---"; kubectl -n "$NS" get events --sort-by='.lastTimestamp' | tail -20 || true
  exit 1
fi

helm -n "$NS" status "$REL"
kubectl -n "$NS" get pods
