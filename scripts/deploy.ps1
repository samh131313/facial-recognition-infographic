<#
  Deploys Liquidity to Google Cloud Run (a *.run.app address).

  First time (imports your PythonAnywhere data):
    powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -ProjectId YOUR-PROJECT -Export C:\path\liquidity-export.tar.gz

  Later updates (after editing app\flask_app.py etc.):
    powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -ProjectId YOUR-PROJECT
#>
param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Export = "",
  [string]$Region = "us-central1",
  [string]$Service = "liquidity"
)

$ErrorActionPreference = "Continue"   # gcloud writes progress to stderr; we check exit codes ourselves
Set-Location (Split-Path -Parent $PSScriptRoot)

function Gc {
  & gcloud @args
  if ($LASTEXITCODE -ne 0) { throw "FAILED: gcloud $($args -join ' ')" }
}
function GcQuiet {
  & gcloud @args 2>&1 | Out-Null
  return ($LASTEXITCODE -eq 0)
}
function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
  throw "gcloud not found. Install the Google Cloud SDK first (see README), then open a NEW PowerShell window."
}

# ---------------------------------------------------------------- 1. unpack export
$ExportDir = ""
if ($Export) {
  if (-not (Test-Path $Export)) { throw "Export not found: $Export" }
  if ((Get-Item $Export).PSIsContainer) {
    $ExportDir = (Resolve-Path $Export).Path
  } else {
    Step "Unpacking $Export"
    $ExportDir = Join-Path (Get-Location) "export"
    if (Test-Path $ExportDir) { Remove-Item -Recurse -Force $ExportDir }
    New-Item -ItemType Directory $ExportDir | Out-Null
    tar -xzf $Export -C $ExportDir
    if ($LASTEXITCODE -ne 0) { throw "Could not unpack $Export" }
  }

  Step "Copying app code and games into app\"
  New-Item -ItemType Directory -Force app | Out-Null
  foreach ($item in "flask_app.py", "gpt_router.py", "minecraft_game", "fps_test") {
    $src = Join-Path $ExportDir $item
    if (Test-Path $src) {
      $dst = Join-Path "app" $item
      if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
      Copy-Item -Recurse $src $dst
      Write-Host "  $item"
    } else {
      Write-Host "  (missing in export: $item)" -ForegroundColor Yellow
    }
  }
}
if (-not (Test-Path "app\flask_app.py")) {
  throw "app\flask_app.py is missing. Run once with -Export path\to\liquidity-export.tar.gz"
}

# ---------------------------------------------------------------- 2. project + APIs
Step "Selecting project $ProjectId and enabling APIs (first time takes a minute)"
Gc config set project $ProjectId
Gc services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com iam.googleapis.com
$ProjectNumber = (& gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()

# ---------------------------------------------------------------- 3. service account
$SaName = "liquidity-run"
$Sa = "$SaName@$ProjectId.iam.gserviceaccount.com"
if (-not (GcQuiet iam service-accounts describe $Sa)) {
  Step "Creating service account $Sa"
  Gc iam service-accounts create $SaName --display-name "Liquidity Cloud Run"
  Start-Sleep -Seconds 10   # IAM needs a moment before the account can be granted roles
}
# New projects build with the default compute account, which needs this role for `--source` deploys.
GcQuiet projects add-iam-policy-binding $ProjectId --member "serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com" --role roles/run.builder --condition=None | Out-Null

# ---------------------------------------------------------------- 4. buckets
$Prefix = "$ProjectId-liq"
$Buckets = @{ media = "$Prefix-media"; pages = "$Prefix-pages"; downloads = "$Prefix-downloads"; db = "$Prefix-db" }
foreach ($b in $Buckets.Values) {
  if (-not (GcQuiet storage buckets describe "gs://$b")) {
    Step "Creating bucket gs://$b"
    Gc storage buckets create "gs://$b" --location $Region --uniform-bucket-level-access --public-access-prevention
  }
  GcQuiet storage buckets add-iam-policy-binding "gs://$b" --member "serviceAccount:$Sa" --role roles/storage.admin | Out-Null
}

# ---------------------------------------------------------------- 5. secrets
function Set-Secret($name, $file) {
  if (-not (GcQuiet secrets describe $name)) {
    Gc secrets create $name --replication-policy automatic --data-file $file
  } else {
    Gc secrets versions add $name --data-file $file
  }
  GcQuiet secrets add-iam-policy-binding $name --member "serviceAccount:$Sa" --role roles/secretmanager.secretAccessor | Out-Null
}
if ($ExportDir) {
  Step "Storing secret.py and the session key in Secret Manager"
  $secretPy = Join-Path $ExportDir "secret.py"
  if (-not (Test-Path $secretPy)) { throw "secret.py missing from export" }
  Set-Secret "liquidity-secret-py" $secretPy

  $keyFile = Join-Path $ExportDir "flask_session_key.txt"
  $key = if (Test-Path $keyFile) { (Get-Content $keyFile -Raw).Trim() } else { -join ((1..48) | ForEach-Object { "{0:x}" -f (Get-Random -Max 16) }) }
  $tmp = New-TemporaryFile
  [IO.File]::WriteAllText($tmp.FullName, $key)
  Set-Secret "liquidity-session-key" $tmp.FullName
  Remove-Item $tmp
}
foreach ($s in "liquidity-secret-py", "liquidity-session-key") {
  if (-not (GcQuiet secrets describe $s)) { throw "Secret $s does not exist yet. Run once with -Export." }
}

# ---------------------------------------------------------------- 6. import data
if ($ExportDir) {
  Step "Uploading uploaded files (media / pages / downloads) to Cloud Storage"
  foreach ($folder in "media", "pages", "downloads") {
    $src = Join-Path $ExportDir $folder
    if (Test-Path $src) { Gc storage rsync --recursive $src "gs://$($Buckets[$folder])" }
  }
  Step "Uploading databases (used only on the very first start)"
  foreach ($db in "chat.db", "gpt.db") {
    $src = Join-Path $ExportDir $db
    if (Test-Path $src) { Gc storage cp $src "gs://$($Buckets.db)/seed/$db" }
  }
  if (GcQuiet storage ls "gs://$($Buckets.db)/litestream/") {
    Write-Host "NOTE: a live database backup already exists, so the uploaded chat.db/gpt.db will be IGNORED." -ForegroundColor Yellow
    Write-Host "      To replace live data with this export, delete it first:  gcloud storage rm -r gs://$($Buckets.db)/litestream" -ForegroundColor Yellow
  }
}

# ---------------------------------------------------------------- 7. build + deploy
Step "Building and deploying (5-10 minutes the first time)"
$mounts = @()
if (GcQuiet run services describe $Service --region $Region) { $mounts += "--clear-volumes"; $mounts += "--clear-volume-mounts" }
foreach ($folder in "media", "pages", "downloads") {
  $mounts += "--add-volume=name=$folder,type=cloud-storage,bucket=$($Buckets[$folder])"
  $mounts += "--add-volume-mount=volume=$folder,mount-path=/home/gerb/mysite/$folder"
}
Gc run deploy $Service --source . --region $Region --quiet `
  --service-account $Sa `
  --execution-environment gen2 `
  --cpu 1 --memory 1Gi --concurrency 80 `
  --min-instances 0 --max-instances 1 `
  --cpu-throttling --timeout 3600 `
  --allow-unauthenticated `
  --set-env-vars "LIQUIDITY_DB_BUCKET=$($Buckets.db)" `
  --set-secrets "/secrets/secret.py=liquidity-secret-py:latest,FLASK_SESSION_KEY=liquidity-session-key:latest" `
  @mounts

$url = (& gcloud run services describe $Service --region $Region --format="value(status.url)").Trim()
Write-Host "`nLiquidity is live at:  $url" -ForegroundColor Green
Write-Host "Open it on your Chromebook. Eaglercraft relay address:  $($url -replace '^https','wss')/eagler-relay"
