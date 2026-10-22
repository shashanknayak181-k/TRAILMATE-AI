$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Venv = Join-Path $Backend '.venv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'

function Invoke-Native {
  param([string]$Label, [scriptblock]$Command)
  Write-Host "`n== $Label ==" -ForegroundColor Cyan
  & $Command
  if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE. Fix the error above, then rerun this script." }
}

Write-Host 'TRAILMATE AI local setup' -ForegroundColor Green
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python was not found. Install Python 3.11+ and enable Add Python to PATH.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js/npm was not found. Install Node.js 20+ and reopen PowerShell.' }
$PyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) { throw 'Unable to run Python. Check your Python installation.' }
$PyParts = $PyVersion.Split('.')
if ([int]$PyParts[0] -lt 3 -or ([int]$PyParts[0] -eq 3 -and [int]$PyParts[1] -lt 11)) { throw "Python 3.11+ required; found $PyVersion." }
$NodeVersion = node -p "process.versions.node"
if ($LASTEXITCODE -ne 0) { throw 'Unable to run Node.js.' }

if (-not (Test-Path $VenvPython)) { Invoke-Native 'Create backend virtual environment' { python -m venv $Venv } }
Invoke-Native 'Upgrade pip' { & $VenvPython -m pip install --upgrade pip }
Invoke-Native 'Install backend dependencies' { & $VenvPython -m pip install -r (Join-Path $Backend 'requirements-local.txt') }
Invoke-Native 'Verify backend imports' { & $VenvPython -c "import alembic, uvicorn, fastapi; print('Backend imports OK')" }

if (-not (Test-Path (Join-Path $Root '.env'))) {
  Copy-Item (Join-Path $Root '.env.example') (Join-Path $Root '.env')
  Write-Host 'Created .env from .env.example. Defaults are for local development only.' -ForegroundColor Yellow
}

Write-Host "`n== Install frontend dependencies ==" -ForegroundColor Cyan
Push-Location $Frontend
try {
  if (Test-Path 'package-lock.json') { npm ci } else { npm install }
  if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed with exit code $LASTEXITCODE. Check network/npm output, then rerun setup." }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed. Resolve the reported TypeScript/build errors before presenting.' }
} finally { Pop-Location }

Write-Host "`n== Apply database migrations and run backend tests ==" -ForegroundColor Cyan
Push-Location $Backend
try {
  & $VenvPython -m alembic -c alembic.ini upgrade head
  if ($LASTEXITCODE -ne 0) { throw 'Database migration failed. Resolve the migration error above.' }
  & $VenvPython -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed. Resolve the failing tests above.' }
} finally { Pop-Location }
Write-Host "`nSetup and verification completed." -ForegroundColor Green
Write-Host 'Terminal 1: .\start-backend.ps1'
Write-Host 'Terminal 2: .\start-frontend.ps1'
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Backend docs: http://127.0.0.1:8000/docs'
