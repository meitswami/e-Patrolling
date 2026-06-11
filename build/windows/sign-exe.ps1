# Sign Shakti portable exe with self-signed certificate

param(
    [string]$ExePath
)

if (-not $ExePath) {
    $AppName = (Get-Content (Join-Path $PSScriptRoot "app_name.txt") -Raw).Trim()
    $ExePath = Join-Path $PSScriptRoot "dist\$AppName\$AppName.exe"
}

$ErrorActionPreference = "Stop"
$pfxPath = Join-Path $PSScriptRoot "certs\e-patrol-codesign.pfx"

if (-not (Test-Path $ExePath)) {
    Write-Error "Executable not found: $ExePath"
}

if (-not (Test-Path $pfxPath)) {
    & (Join-Path $PSScriptRoot "create-cert.ps1")
}

$signtool = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $signtool) {
    Write-Warning "signtool.exe not found. Install Windows SDK (Signing Tools)."
    Write-Host "Certificate created at $pfxPath - sign manually when SDK is available."
    exit 0
}

$pwd = "ePatrol2026!"
& $signtool.FullName sign `
    /f $pfxPath `
    /p $pwd `
    /fd SHA256 `
    /tr http://timestamp.digicert.com `
    /td SHA256 `
    /d "Shakti - the 3rd Eye by GenXAI Analytics Pvt. Ltd." `
    /du "https://github.com" `
    $ExePath

Write-Host "Signed: $ExePath"
