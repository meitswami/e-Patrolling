# Shakti - the 3rd Eye — Portable Windows .exe build (no Docker, no install)
# GenXAI Analytics Pvt. Ltd. | MEIT SWAMI | Jaipur, Rajasthan
#
# Output: build\windows\release\Shakti - the 3rd Eye\
#
# Prerequisites: Python 3.12+, Node.js 20+, Windows SDK (optional, for signing)

param(
    [switch]$SkipFrontend,
    [switch]$SkipSign,
    [switch]$SkipObfuscate
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BuildDir = Join-Path $PSScriptRoot "dist"
$ReleaseDir = Join-Path $PSScriptRoot "release"
$VenvDir = Join-Path $PSScriptRoot ".venv-build"
$UiOut = Join-Path $PSScriptRoot "dist-ui"
$AppName = (Get-Content (Join-Path $PSScriptRoot "app_name.txt") -Raw).Trim()
$ExeName = "$AppName.exe"

Write-Host "=== $AppName Portable Build ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

# ── 1. Python venv + deps ─────────────────────────────────
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}
$python = Join-Path $VenvDir "Scripts\python.exe"
$pip = Join-Path $VenvDir "Scripts\pip.exe"

& $python -m pip install -U pip wheel 2>$null | Out-Null
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements-portable.txt")

# Playwright Chromium (kept beside exe, not inside — keeps size manageable)
$browserDir = Join-Path $BuildDir "playwright-browsers"
New-Item -ItemType Directory -Force -Path $browserDir | Out-Null
$env:PLAYWRIGHT_BROWSERS_PATH = $browserDir
& $python -m playwright install chromium

# ── 2. Frontend static export ───────────────────────────────
if (-not $SkipFrontend) {
    Write-Host "Building frontend static export..." -ForegroundColor Yellow
    Push-Location (Join-Path $RepoRoot "frontend")
    if (-not (Test-Path "node_modules")) {
        npm ci
    }
    Copy-Item -Force "next.config.portable.js" "next.config.js"
    $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8765"
    npm run build
    if (Test-Path "out") {
        Remove-Item -Recurse -Force $UiOut -ErrorAction SilentlyContinue
        Copy-Item -Recurse "out" $UiOut
    } else {
        throw "Next.js export failed - out folder missing"
    }
    Pop-Location
}

# ── 3. Optional PyArmor obfuscation ─────────────────────────
$BackendSrc = Join-Path $RepoRoot "backend"
$BackendBuild = Join-Path $BuildDir "backend-obf"
if (-not $SkipObfuscate) {
  $pyarmor = Join-Path $VenvDir "Scripts\pyarmor.exe"
  if (-not (Test-Path $pyarmor)) {
    & $pip install pyarmor 2>$null
  }
  if (Test-Path $pyarmor) {
    Write-Host "Obfuscating backend with PyArmor..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BackendBuild -ErrorAction SilentlyContinue
    & $pyarmor gen -O $BackendBuild -r $BackendSrc --exclude "__pycache__" 2>$null
    if (Test-Path $BackendBuild) {
      Write-Host "PyArmor obfuscation applied."
    }
  } else {
    Write-Host "PyArmor not available - shipping compiled bytecode only (PyInstaller)." -ForegroundColor DarkYellow
  }
}

# ── 3b. App icon (.ico from logo) ───────────────────────────
Write-Host "Generating Windows icon from logo..." -ForegroundColor Yellow
& $python (Join-Path $PSScriptRoot "make_icon.py")

# ── 4. PyInstaller ──────────────────────────────────────────
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
$DistApp = Join-Path $PSScriptRoot "dist\$AppName"
Remove-Item -Recurse -Force $DistApp -ErrorAction SilentlyContinue
& $python -m PyInstaller (Join-Path $PSScriptRoot "patrol.spec") --noconfirm --distpath (Join-Path $PSScriptRoot "dist") --workpath (Join-Path $BuildDir "pyi-work")

$ExeFolder = $DistApp
$BuiltExe = Join-Path $ExeFolder $ExeName
if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller failed - $ExeName not found"
}

# ── 5. Assemble release folder ──────────────────────────────
$ReleaseApp = Join-Path $ReleaseDir $AppName
Remove-Item -Recurse -Force $ReleaseApp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ReleaseApp | Out-Null
Copy-Item -Recurse "$ExeFolder\*" $ReleaseApp
if (Test-Path $browserDir) {
    Copy-Item -Recurse $browserDir (Join-Path $ReleaseApp "playwright-browsers")
}

# Portable .env template
Copy-Item -Force (Join-Path $PSScriptRoot ".env.portable") (Join-Path $ReleaseApp ".env.example")
if (-not (Test-Path (Join-Path $ReleaseApp ".env"))) {
    Copy-Item -Force (Join-Path $PSScriptRoot ".env.portable") (Join-Path $ReleaseApp ".env")
}

# Storage seed
$storageDest = Join-Path $ReleaseApp "storage"
New-Item -ItemType Directory -Force -Path $storageDest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $storageDest "sessions") | Out-Null

# ── 6. Code signing ─────────────────────────────────────────
$ReleaseExe = Join-Path $ReleaseApp $ExeName
if (-not $SkipSign) {
    & (Join-Path $PSScriptRoot "sign-exe.ps1") -ExePath $ReleaseExe
    Copy-Item -Force (Join-Path $PSScriptRoot "certs\e-patrol-codesign.cer") (Join-Path $ReleaseApp "GenXAI-Shakti-CodeSign.cer") -ErrorAction SilentlyContinue
}

# ── 7. README ───────────────────────────────────────────────
@'
Shakti - the 3rd Eye | Portable Edition
========================================
GenXAI Analytics Pvt. Ltd. | Created by MEIT SWAMI | Jaipur, Rajasthan

QUICK START (no installation):
1. Edit .env - set DATABASE_URL (Supabase) and JWT_SECRET_KEY
2. Double-click "Shakti - the 3rd Eye.exe"
3. Browser opens automatically - login at /admin

VIEW CRAWLING:
Targets -> View Crawling -> Run Crawl / Crawl History / Pause / Resume

REDUCE WINDOWS SMARTSCREEN WARNING:
Install GenXAI-Shakti-CodeSign.cer into Trusted Root + Trusted Publishers.

SIZE: ~800 MB (Chromium included). No Docker required.
'@ | Set-Content -Encoding UTF8 (Join-Path $ReleaseApp "README.txt")

Write-Host ""
Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "Release folder: $ReleaseApp"
Write-Host "Run: $ReleaseExe"
$sizeMb = [math]::Round((Get-ChildItem -Recurse $ReleaseApp | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "Total size: ${sizeMb} MB"
