Param(
  [Parameter(Mandatory = $true)][string]$BaseUrl
)

$ErrorActionPreference = 'Stop'

Write-Host "Running smoke test against $BaseUrl/rest/v1 ..." -ForegroundColor Cyan
try {
  $res = Invoke-WebRequest -Uri "$BaseUrl/rest/v1" -Method GET -SkipCertificateCheck -TimeoutSec 20 -ErrorAction Stop
  if ($res.StatusCode -eq 200) {
    Write-Host "Smoke test passed (HTTP 200)." -ForegroundColor Green
    exit 0
  } else {
    Write-Host "Unexpected status: $($res.StatusCode)" -ForegroundColor Yellow
    exit 2
  }
}
catch {
  Write-Error "Smoke test failed: $($_.Exception.Message)"
  exit 1
}
