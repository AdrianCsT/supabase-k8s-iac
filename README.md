# supabase-k8s-iac
Automated, production-grade deployment of Supabase on Kubernetes using code-based IaC (CDKTF) for Azure. Includes modular infrastructure, secure secrets management, Helm-based app provisioning, and scalable cloud-native architecture.

## Repo Structure
- `infra/` — CDKTF (Python) skeleton for Azure infra (VNet, AKS, PostgreSQL Flexible Server, Storage, Key Vault)
- `k8s/` — Kubernetes manifests (External Secrets, HPA, NetworkPolicy, Ingress, Namespace)
- `helm/` — Supabase Helm values tailored for AKS + external services
- `scripts/` — PowerShell scripts for deploy/destroy and smoke testing
- `docs/implementation/` — Implementation plan and deployment flow
- `docs/diagrams/` — Mermaid diagram placeholders

See `docs/implementation/azure-supabase-implementation-plan.md` for the full end-to-end steps.
