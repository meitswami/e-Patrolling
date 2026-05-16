# Start PATROL API from repo root (main.py lives in backend/)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Root "backend"

$Python = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    Write-Host "No venv found. Create one and install deps:" -ForegroundColor Yellow
    Write-Host "  cd $Root"
    Write-Host "  python -m venv backend\.venv"
    Write-Host "  .\backend\.venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

Set-Location $Backend
Write-Host "Starting PATROL API at http://127.0.0.1:8000 (cwd: $Backend)" -ForegroundColor Green
& $Python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
