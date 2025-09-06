Param(
  [Parameter(Mandatory = $true)][string]$Namespace = "supabase",
  [Parameter(Mandatory = $true)][string]$ReleaseName = "supabase",
  [Parameter(Mandatory = $true)][string]$ValuesFile = "helm/values/supabase-aks-values.yaml"
)

$ErrorActionPreference = 'Stop'

Write-Host "Adding chart repo..." -ForegroundColor Cyan
helm repo add supabase-community https://supabase-community.github.io/charts/ | Out-Null
helm repo update | Out-Null

Write-Host "Deploying Supabase Helm release..." -ForegroundColor Cyan
helm upgrade --install $ReleaseName supabase-community/supabase --namespace $Namespace --create-namespace -f $ValuesFile

Write-Host "Applying Ingress for AGIC..." -ForegroundColor Cyan
kubectl apply -f k8s/ingress/supabase-ingress.yaml | Out-Null
