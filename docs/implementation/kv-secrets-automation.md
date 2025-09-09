# Key Vault Secrets Automation for Supabase on AKS

## Goal
Automate provisioning of all Supabase secrets into Azure Key Vault and grant the AKS kubelet identity permissions, so External Secrets Operator (ESO) can sync them into Kubernetes without manual `az keyvault secret` commands.

## Flow
```mermaid
flowchart LR
  A[final-working-deployment.ps1] --> B[Ensure ESO + CRDs]
  A --> C[Sync Key Vault Secrets]
  C -->|RBAC| D[Grant kubelet MI: KV Secrets User]
  D --> E[ESO reads Key Vault]
  E --> F[K8s Secret supabase-env]
  F --> G[Helm Install Supabase]
```

## Commands
- Main wrapper now accepts `-KeyVaultName` and can load secrets from a JSON file or generate safe defaults:

```powershell
./final-working-deployment.ps1 `
  -ResourceGroup 'supabase-dev-rg' `
  -ClusterName 'supabase-dev-aks' `
  -Namespace 'supabase' `
  -ValuesFile '.\helm\values\supabase-aks-values.yaml' `
  -ReleaseName 'supabase' `
  -KeyVaultName 'supabase-dev-kv' `
  -GenerateDefaults
```

Alternatively, provide a file:

```json
// config/secrets.local.json (NOT committed)
{
  "jwt-secret": "<your jwt secret>",
  "anon-key": "<your anon key>",
  "service-role-key": "<your service role key>",
  "postgres-connection-string": "postgresql://postgres:postgres@supabase-supabase-db:5432/postgres",
  "storage-connection-string": "UseMinIO",
  "supabase-storage-creds": "{\"keyId\":\"minioadmin\",\"accessKey\":\"minioadmin\"}"
}
```

Then run:

```powershell
./final-working-deployment.ps1 ... -KeyVaultName supabase-dev-kv -SecretsFile .\config\secrets.local.json
```

## Notes
- ESO manifests were updated to `external-secrets.io/v1`.
- Helm values enable MinIO for S3-compatible storage to satisfy the storage requirement; credentials come from Key Vault via ESO.
- The wrapper installs ESO (idempotent), syncs secrets to Key Vault, grants kubelet identity RBAC, then deploys Supabase.

