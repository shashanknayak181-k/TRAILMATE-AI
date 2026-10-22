$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Frontend = Join-Path $Root 'frontend'
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) { throw 'Frontend dependencies missing. Run .\setup-local.ps1 from the project root and resolve any setup errors.' }
Push-Location $Frontend
try {
  npm run dev -- --host 127.0.0.1
  if ($LASTEXITCODE -ne 0) { throw "Vite exited with code $LASTEXITCODE." }
} finally { Pop-Location }
