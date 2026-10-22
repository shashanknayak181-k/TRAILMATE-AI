$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Backend environment missing. Run .\setup-local.ps1 from the project root and resolve any setup errors.' }
Push-Location $Backend
try {
  & $Python -c "import alembic, uvicorn, fastapi; print('Backend dependencies OK')"
  if ($LASTEXITCODE -ne 0) { throw 'Backend dependencies are missing. Run .\setup-local.ps1 and make sure it completes successfully.' }
  & $Python -m alembic -c alembic.ini upgrade head
  if ($LASTEXITCODE -ne 0) { throw 'Database migration failed; backend was not started.' }
  & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  if ($LASTEXITCODE -ne 0) { throw "Uvicorn exited with code $LASTEXITCODE." }
} finally { Pop-Location }
