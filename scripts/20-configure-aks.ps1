Param(
  [Parameter(Mandatory = $true)][string]$ResourceGroup,
  [Parameter(Mandatory = $true)][string]$ClusterName
)

$ErrorActionPreference = 'Stop'

Write-Host "Fetching AKS credentials..." -ForegroundColor Cyan
az aks get-credentials --resource-group $ResourceGroup --name $ClusterName --overwrite-existing | Out-Null

Write-Host "Creating namespace 'supabase'..." -ForegroundColor Cyan
kubectl apply -f k8s/namespaces/supabase-namespace.yaml | Out-Null

Write-Host "Installing External Secrets Operator (ESO)..." -ForegroundColor Cyan
helm repo add external-secrets https://charts.external-secrets.io | Out-Null
helm upgrade --install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace | Out-Null

Write-Host "Configuring SecretStore for Azure Key Vault..." -ForegroundColor Cyan
kubectl apply -f k8s/eso/secretstore.yaml | Out-Null

Write-Host "Applying ExternalSecret mapping..." -ForegroundColor Cyan
kubectl apply -f k8s/eso/externalsecret.yaml | Out-Null

Write-Host "Installing AGIC (Application Gateway Ingress Controller)..." -ForegroundColor Cyan
helm repo add application-gateway-kubernetes-ingress https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/ | Out-Null
helm upgrade --install ingress-azure application-gateway-kubernetes-ingress/ingress-azure -n agic --create-namespace | Out-Null

Write-Host "Applying baseline HPA and NetworkPolicy..." -ForegroundColor Cyan
kubectl apply -f k8s/hpa/postgrest-hpa.yaml | Out-Null
kubectl apply -f k8s/hpa/realtime-hpa.yaml | Out-Null
kubectl apply -f k8s/networkpolicy/supabase-networkpolicy.yaml | Out-Null
