<#
  Deploys the Liquidity backup address on Google Cloud Run (*.run.app).
  It only forwards traffic to your Appliku site; all data stays on the Hetzner server.

  First time:
    powershell -ExecutionPolicy Bypass -File mirror\deploy-mirror.ps1 -ProjectId YOUR-PROJECT -Target liquidity.applikuapp.com

  It prints a PROXY SECRET. Put it in Appliku as LIQ_PROXY_SECRET and redeploy the app.
  To redeploy later without changing the secret, pass -Secret THE-SAME-SECRET.
#>
param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [Parameter(Mandatory = $true)][string]$Target,
  [string]$Secret = "",
  [string]$Region = "us-central1",
  [string]$Service = "liquidity-mirror"
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Gc {
  & gcloud @args
  if ($LASTEXITCODE -ne 0) { throw "FAILED: gcloud $($args -join ' ')" }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
  throw "gcloud not found. Install the Google Cloud SDK, then open a NEW PowerShell window."
}
$Target = $Target -replace '^https?://', '' -replace '/.*$', ''
if (-not $Secret) { $Secret = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N") }

Write-Host "`n==> Project $ProjectId, enabling APIs (first time takes a minute)" -ForegroundColor Cyan
Gc config set project $ProjectId
Gc services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
$ProjectNumber = (& gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()
& gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com" --role roles/run.builder --condition=None 2>&1 | Out-Null

Write-Host "`n==> Building and deploying the mirror (3-5 minutes)" -ForegroundColor Cyan
Gc run deploy $Service --source . --region $Region --quiet `
  --allow-unauthenticated `
  --cpu 1 --memory 256Mi --concurrency 250 `
  --min-instances 0 --max-instances 3 `
  --cpu-throttling --timeout 3600 `
  --set-env-vars "TARGET=$Target,PROXY_SECRET=$Secret"

$url = (& gcloud run services describe $Service --region $Region --format="value(status.url)").Trim()
Write-Host "`nBackup address:  $url" -ForegroundColor Green
Write-Host "`nNOW, in Appliku -> liquidity -> Environment Variables, add:" -ForegroundColor Yellow
Write-Host "  LIQ_PROXY_SECRET = $Secret" -ForegroundColor Yellow
Write-Host "then redeploy the app. Keep this secret private (do not paste it in chats)."
