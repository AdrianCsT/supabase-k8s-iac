Param(
  [Parameter(Mandatory = $true)][string]$ProjectDir = "infra"
)

$ErrorActionPreference = 'Stop'
Write-Host "Synthesizing CDKTF..." -ForegroundColor Cyan
Push-Location $ProjectDir
try {
  cdktf synth
  Write-Host "Deploying CDKTF..." -ForegroundColor Cyan
  cdktf deploy -auto-approve
}
finally {
  Pop-Location
}
