# One-time: clean release root — config/docs in hidden app_data/
# Usage: powershell -ExecutionPolicy Bypass -File build\windows\migrate-release-layout.ps1

$ErrorActionPreference = "Stop"
$AppName = (Get-Content (Join-Path $PSScriptRoot "app_name.txt") -Raw).Trim()
$Release = Join-Path $PSScriptRoot "release\$AppName"
if (-not (Test-Path $Release)) { throw "Release not found: $Release" }

$AppData = Join-Path $Release "app_data"
$Docs = Join-Path $AppData "docs"
New-Item -ItemType Directory -Force -Path $Docs | Out-Null

# Move .env (keep existing secrets)
$rootEnv = Join-Path $Release ".env"
$appEnv = Join-Path $AppData ".env"
if ((Test-Path $rootEnv) -and -not (Test-Path $appEnv)) {
    Move-Item -Force $rootEnv $appEnv
    Write-Host "Moved .env -> app_data\.env"
} elseif (-not (Test-Path $appEnv)) {
    Copy-Item -Force (Join-Path $PSScriptRoot ".env.portable") $appEnv
    Write-Host "Created app_data\.env from template"
}

# Move docs
foreach ($name in @("SETUP-DATABASE.txt", "README.txt", "README-DISTRIBUTION.txt", ".env.example")) {
    $src = Join-Path $Release $name
    if (Test-Path $src) {
        Move-Item -Force $src (Join-Path $Docs $name)
        Write-Host "Moved $name -> app_data\docs\"
    }
}
Copy-Item -Force (Join-Path $PSScriptRoot ".env.portable") (Join-Path $Docs "env.example") -ErrorAction SilentlyContinue

# Remove launcher scripts from release root (exe runs directly)
foreach ($name in @("Start Shakti.cmd", "Start-Shakti.ps1", "Test-Database.ps1")) {
    $p = Join-Path $Release $name
    if (Test-Path $p) { Remove-Item -Force $p; Write-Host "Removed $name" }
}

# Patch runtime settings (loads app_data\.env without rebuild)
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$settingsSrc = Join-Path $RepoRoot "backend\configs\settings.py"
$settingsDst = Join-Path $Release "_internal\backend\configs\settings.py"
if (Test-Path $settingsDst) {
    Copy-Item -Force $settingsSrc $settingsDst
    Write-Host "Patched _internal\backend\configs\settings.py"
}

cmd /c "attrib +h `"$AppData`""
Write-Host ""
Write-Host "Done. Release root should show only:" -ForegroundColor Green
Write-Host "  $AppName.exe, _internal\, playwright-browsers\, storage\, app_data\ (hidden)"
Write-Host "Edit config: $appEnv" -ForegroundColor Yellow
Write-Host "Double-click the .exe to run." -ForegroundColor Yellow
