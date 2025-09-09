#!/bin/bash

# Dev Container post-create setup script
set -euo pipefail

echo "[devcontainer] Setting up development environment..."

# Ensure Node/NPM present from features, then install CDKTF CLI
echo "[devcontainer] Installing CDKTF CLI..."
npm install -g cdktf-cli@latest

echo "[devcontainer] Tool versions:"
echo "Azure CLI: $(az --version | head -n 1 || true)"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "Python: $(python --version)"
echo "pip: $(python -m pip --version)"
echo "kubectl: $(kubectl version --client --short 2>/dev/null || echo 'not installed')"
echo "Helm: $(helm version --short 2>/dev/null || echo 'not installed')"
echo "Terraform: $(terraform version | head -n 1)"
echo "CDKTF: $(cdktf --version)"

# Python deps for infra
echo "[devcontainer] Installing Python deps..."
python -m pip install --upgrade pip
python -m pip install -r infra/requirements.txt

# Note: 'cdktf get' is not required for Python providers (installed via pip)

# Default TFVARS_FILE to dev if not provided
if [ -z "${TFVARS_FILE:-}" ]; then
  echo "[devcontainer] TFVARS_FILE not set; defaulting to vars/dev.tfvars"
  echo "TFVARS_FILE=vars/dev.tfvars" >> ~/.bashrc
  export TFVARS_FILE=vars/dev.tfvars
fi

# Validate SP env; perform non-interactive az login if available, otherwise warn
missing=()
for v in ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID ARM_SUBSCRIPTION_ID; do
  if [ -z "${!v:-}" ]; then missing+=("$v"); fi
done
if [ ${#missing[@]} -eq 0 ]; then
  echo "[devcontainer] Logging in to Azure with Service Principal..."
  az login --service-principal -u "$ARM_CLIENT_ID" -p "$ARM_CLIENT_SECRET" --tenant "$ARM_TENANT_ID" >/dev/null || true
  az account set --subscription "$ARM_SUBSCRIPTION_ID" || true
else
  echo "[devcontainer] WARNING: Missing Service Principal env vars: ${missing[*]}" >&2
  echo "[devcontainer] You can still work locally; set these to run deploy scripts."
fi

# Warn if PG admin credentials not provided
if [ -z "${PG_ADMIN_LOGIN:-}" ] || [ -z "${PG_ADMIN_PASSWORD:-}" ]; then
  echo "[devcontainer] WARNING: PG_ADMIN_LOGIN/PG_ADMIN_PASSWORD not set. 'cdktf deploy' will fail until provided."
fi

# .terraformrc for better UX
if [ ! -f /home/vscode/.terraformrc ]; then
  echo "[devcontainer] Creating ~/.terraformrc"
  cat > /home/vscode/.terraformrc << 'EOF'
plugin_cache_dir = "$HOME/.terraform.d/plugin-cache"
disable_checkpoint = true
EOF
  mkdir -p /home/vscode/.terraform.d/plugin-cache
  chown -R vscode:vscode /home/vscode/.terraform.d
fi

echo "[devcontainer] Setup complete."
echo "- cd infra && cdktf synth"
echo "- export PG_ADMIN_LOGIN=...; export PG_ADMIN_PASSWORD=...; cd infra && cdktf deploy --auto-approve"
echo "- Auth configured via Service Principal (non-interactive)."
