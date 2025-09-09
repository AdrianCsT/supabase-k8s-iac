# Devcontainer Setup – Supabase K8s IaC (Azure)

This document describes the implementation plan and structure for a cross‑platform VS Code Dev Container that standardizes the environment for the Supabase on Kubernetes IaC assignment (Azure focus). It installs and validates the essential tools while keeping builds fast and reproducible.

## Goals

- Provide a ready‑to‑use environment for Azure‑based CDKTF (Python), Terraform, AKS, and Helm workflows.
- Install Terraform from official binaries (no source builds).
- Avoid unnecessary container settings and keep configuration minimal and professional.
- Post‑create script validates the toolchain to ensure the environment is ready.

## Implementation Plan

1. Base image and features
2. Core tooling via Dev Containers Features
3. Post‑create provisioning (cdktf-cli, kubelogin)
4. Environment verification (PowerShell)
5. Developer UX (VS Code extensions)

```mermaid
flowchart TD
    A[Base Image: mcr.microsoft.com/devcontainers/base:ubuntu-22.04] --> B[Dev Containers Features]
    B --> B1[Azure CLI]
    B --> B2[Terraform (binary, 1.9.6)]
    B --> B3[kubectl]
    B --> B4[Helm]
    B --> B5[Python 3.11 + pip]
    B --> B6[Node.js 20]
    B --> B7[PowerShell 7]
    B --> C[Container Ready]
    C --> D[postCreate.sh]
    D --> D1[npm i -g cdktf-cli]
    D --> D2[az aks install-cli  (kubelogin)]
    D --> E[pwsh scripts/verify-tools.ps1]
    E --> F{All tools present?}
    F -- Yes --> G[Developer Ready]
    F -- No --> H[Fail with missing tool list]
```

## Files Added

- `.devcontainer/devcontainer.json`: Uses features to install Azure CLI, Terraform (binary), kubectl, Helm, Python, Node.js, PowerShell. Adds a post‑create hook and VS Code extensions.
- `.devcontainer/postCreate.sh`: Installs `cdktf-cli` (global) and ensures `kubelogin` via `az aks install-cli`, then runs verification.
- `scripts/verify-tools.ps1`: PowerShell verifier that checks versions for: Terraform, CDKTF, Python/pip, Node/npm, PowerShell, kubectl, kubelogin, Helm, Azure CLI, Git.

## Why This Approach

- Speed and simplicity: Dev Containers Features are optimized and cache well, avoiding slow bespoke apt steps.
- Terraform via binary: The Terraform feature pulls official HashiCorp binaries as requested.
- Azure alignment: Installs Azure CLI, AKS tooling (`kubelogin`), kubectl, and Helm for cluster operations.
- Cross‑platform consistency: Container encapsulates versions; host OS differences are abstracted away.

## Usage

1. Open the repo in VS Code and “Reopen in Container”.
2. Wait for features to install and the post‑create script to run.
3. Confirm success: the verification output must end with “Environment verification passed…”.
4. Sign in to Azure: `az login` (device login) or `az login --tenant <TENANT_ID>`.
5. Connect to AKS when ready: `az aks get-credentials --resource-group <rg> --name <aks>`.
6. Proceed with IaC:
   - `cdktf synth`
   - `cdktf deploy`
   - Deploy Helm chart overrides for Supabase as per the assignment.

## Notes

- No default ports or extraneous container settings are configured.
- Python is installed via apt (no source builds). CDKTF uses Node.js 20 and Python 3.11 as a stable baseline.
- `az aks install-cli` is used to provision `kubelogin`, keeping the AKS auth path standard.

