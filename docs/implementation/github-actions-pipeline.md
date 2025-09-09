**Title: Production GitHub Actions Pipeline**

This project includes CI/CD workflows that fully automate the same flow as the PowerShell scripts (10/20/30/40), using Azure OIDC for passwordless cloud auth.

Workflows
- .github/workflows/ci.yml
  - Runs on PRs: installs tools, runs `cdktf get/synth`, validates synthesized Terraform.
- .github/workflows/deploy.yml
  - Runs on push to main or manual dispatch; environment = `production`.
  - Steps: Azure login (OIDC) → install tools → `./scripts/10-deploy-infra.ps1` → `./scripts/20-configure-aks.ps1` → `./scripts/30-deploy-app.ps1` → `./scripts/40-smoke-test.ps1 -Internal`.
  - Uses `az aks command invoke` so it works with private AKS.
- .github/workflows/destroy.yml
  - Manual teardown: Azure login (OIDC) → `./scripts/90-destroy-infra.ps1`.

Required GitHub Secrets (Repository or Environment: production)
- `AZURE_CLIENT_ID`: AAD app registration (federated) Client ID
- `AZURE_TENANT_ID`: Tenant ID
- `AZURE_SUBSCRIPTION_ID`: Subscription ID
- `PG_ADMIN_LOGIN`: Postgres admin login name
- `PG_ADMIN_PASSWORD`: Postgres admin password

Azure OIDC (Federated Credentials)
1) Create an App Registration (or use existing) for the pipeline identity.
2) Add a Federated Credential with issuer `https://token.actions.githubusercontent.com` and subject matching your repo (e.g., `repo:ORG/REPO:environment:production` or `repo:ORG/REPO:ref:refs/heads/main`).
3) Assign least-privilege roles at the target Resource Group scope (e.g., `Contributor`, `User Access Administrator` if needed for specific operations).

Notes
- Scripts auto-detect Azure CLI authentication; no client secret is required in CI.
- Terraform state is synthesized by CDKTF and applied in a single job; if you later introduce a remote backend, add its bootstrap steps before `cdktf deploy`.
- By default, NGINX is installed as an internal LoadBalancer (private). External smoke tests require exposing NGINX publicly or use `-Internal`.

