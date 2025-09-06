Param(
  [Parameter(Mandatory = $true)][string]$ProjectDir = "infra"
)

$ErrorActionPreference = 'Stop'
Write-Host "Destroying CDKTF-managed infrastructure..." -ForegroundColor Cyan
Push-Location $ProjectDir
try {
  cdktf destroy -auto-approve
}
finally {
  Pop-Location
}
