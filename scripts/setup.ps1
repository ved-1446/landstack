<#
.SYNOPSIS
  One-command setup for LandStack on Windows PowerShell (Linux/macOS: scripts/setup.sh).

.DESCRIPTION
  Run from anywhere:   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  Steps: check tools -> .env -> start the database (Docker) -> Python packages -> create the schema -> seed the fake data
         -> seed the demo users -> build the Land Guide corpus -> run the checks -> install the web app packages.

  What it will NOT do without telling you:
    * Applying db/schema.sql DROPS and recreates every table (demo data, users, the audit log, issued-passport records).
      If the database already has tables, the script stops and asks first. -Yes answers that question "yes".
    * It never overwrites an existing .env, never prints a secret, and never runs git commit.
  The Land Guide step downloads 6 public pages politely (about 30 seconds). -SkipCorpus skips the download.

.PARAMETER Yes         Do not ask before re-creating existing tables.
.PARAMETER SkipCorpus  Do not download the Land Guide pages (the Guide then answers from its glossary only).
.PARAMETER SkipFrontend  Do not run npm ci.
#>
param([switch]$Yes, [switch]$SkipCorpus, [switch]$SkipFrontend)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "STOPPED: $text" -ForegroundColor Red; exit 1 }
function Need($cmd, $hint) { if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Fail "$cmd was not found. $hint" } }
function RandomText($bytes) { $b = New-Object byte[] $bytes; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); ([Convert]::ToBase64String($b) -replace '[^A-Za-z0-9]', '') }
function EnvValue($name, $default) {
  $line = Select-String -Path ".env" -Pattern "^\s*$name\s*=(.*)$" | Select-Object -First 1
  if ($line) { $v = $line.Matches[0].Groups[1].Value.Trim(); if ($v) { return $v } }
  return $default
}

Step 1 "Checking tools"
Need docker "Install Docker Desktop and start it."
Need python "Install Python 3.14 (what the pinned versions were tested on; 3.11 to 3.13 may work)."
& docker info *> $null; if ($LASTEXITCODE -ne 0) { Fail "Docker is installed but not running. Start Docker Desktop and run this again." }
if (-not $SkipFrontend) { Need npm "Install Node.js 20.19 or newer (24 was tested), or run with -SkipFrontend." }

Step 2 "Checking .env"
if (-not (Test-Path ".env")) {
  $pw = RandomText 24; $jwt = RandomText 48
  # POSTGRES_PORT and LANDSTACK_DB_CONTAINER from your environment win (use them if 5432 or the name "landstack-db" is taken)
  $port = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
  $extra = if ($env:LANDSTACK_DB_CONTAINER) { "LANDSTACK_DB_CONTAINER=$($env:LANDSTACK_DB_CONTAINER)`n" } else { "" }
  @"
# Made by scripts/setup.ps1. Never commit this file (it is git-ignored).
POSTGRES_USER=landstack
POSTGRES_PASSWORD=$pw
POSTGRES_DB=landstack
POSTGRES_HOST=localhost
${extra}POSTGRES_PORT=$port
JWT_SECRET=$jwt
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
"@ | Set-Content -Path ".env" -Encoding ascii
  Write-Host "Created .env with a random database password and a random login secret (values not shown)."
} else {
  Write-Host ".env already exists and is left alone."
  foreach ($k in "POSTGRES_PASSWORD", "JWT_SECRET") {
    if (-not (Select-String -Path ".env" -Pattern "^\s*$k\s*=\s*\S" -Quiet)) { Fail "$k is missing or empty in .env. Add it (see .env.example), then run this again." }
  }
}
$User = EnvValue "POSTGRES_USER" "landstack"; $Db = EnvValue "POSTGRES_DB" "landstack"
$Container = EnvValue "LANDSTACK_DB_CONTAINER" "landstack-db"

Step 3 "Starting the database (Docker, PostGIS)"
$old = (& docker ps -a --format "{{.Names}}" 2>$null) -contains "landstack-db"
if ($old -and $Container -ne "landstack-db") { Write-Host "Note: an OLD container named landstack-db exists (from before the rename). It is left alone; this script starts $Container with a new, empty database. Remove the old one yourself when you no longer need it." -ForegroundColor Yellow }
docker compose up -d
if ($LASTEXITCODE -ne 0) { Fail "docker compose up failed. If the name or port is taken, set LANDSTACK_DB_CONTAINER or POSTGRES_PORT in .env." }
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  & docker exec $Container pg_isready -U $User -d $Db *> $null
  if ($LASTEXITCODE -eq 0) { $ready = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ready) { Fail "the database did not become ready in 2 minutes. Look at: docker logs $Container" }
Write-Host "Database is ready."

Step 4 "Python environment and packages"
if (-not (Test-Path ".venv")) { python -m venv .venv; if ($LASTEXITCODE -ne 0) { Fail "could not create .venv" } }
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py -m pip install --quiet --disable-pip-version-check -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "pip install failed (the pinned versions were tested on Python 3.14; an older Python may lack a wheel)." }

Step 5 "Creating the schema"
$has = (& docker exec $Container psql -U $User -d $Db -tAc "SELECT to_regclass('public.plots') IS NOT NULL").Trim()
if ($has -eq "t") {
  Write-Host "The database already has LandStack tables. Applying the schema DROPS and recreates every table:" -ForegroundColor Yellow
  Write-Host "  all plots, demo users, the audit log and issued-passport records will be deleted (they are rebuilt by the next steps)."
  if (-not $Yes) {
    $answer = Read-Host "Type YES to continue (anything else stops here)"
    if ($answer -ne "YES") { Fail "left the existing tables untouched, as you asked." }
  }
}
Get-Content db/schema.sql | docker exec -i $Container psql -U $User -d $Db -v ON_ERROR_STOP=1 -q
if ($LASTEXITCODE -ne 0) { Fail "applying db/schema.sql failed." }

Step 6 "Seeding the fake data (fixed seed: same data every time) and the demo users"
& $Py db/seed.py; if ($LASTEXITCODE -ne 0) { Fail "db/seed.py failed." }
& $Py db/seed_users.py; if ($LASTEXITCODE -ne 0) { Fail "db/seed_users.py failed." }

Step 7 "Building the Land Guide corpus"
if ($SkipCorpus) { & $Py -m chatbot.build --index-only }
else { Write-Host "(Downloads 6 public pages politely, 4 seconds apart. Skip with -SkipCorpus.)"; & $Py -m chatbot.build }
if ($LASTEXITCODE -ne 0) { Write-Host "The corpus step had a problem. The Land Guide still works from its glossary. Continuing." -ForegroundColor Yellow }

Step 8 "Running the checks (flagged problems against the planted ones)"
& $Py -m backend.app.checks
if ($LASTEXITCODE -ne 0) { Fail "the checks failed." }

if (-not $SkipFrontend) {
  Step 9 "Installing the web app packages"
  Push-Location frontend
  npm ci --no-audit --no-fund
  $code = $LASTEXITCODE
  if ($code -eq 0 -and -not (Test-Path ".env")) {
    "VITE_DEMO_ACCOUNTS=true" | Set-Content -Path ".env" -Encoding ascii
    Write-Host "Created frontend/.env with VITE_DEMO_ACCOUNTS=true (shows the demo login buttons; use false in any real deployment)."
  }
  Pop-Location
  if ($code -ne 0) { Fail "npm ci failed." }
}

Write-Host "`nDone. To run it, open two terminals in $Root :" -ForegroundColor Green
Write-Host "  1)  .venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload"
Write-Host "  2)  cd frontend ; npm run dev        then open http://localhost:5173"
Write-Host "Demo logins and the 6-click tour: docs/DEMO.md"
