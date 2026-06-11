# Create a shareable ZIP of Shakti — no secrets, no personal session data.
# Usage: powershell -ExecutionPolicy Bypass -File build\windows\package-for-distribution.ps1

$ErrorActionPreference = "Stop"
$AppName = (Get-Content (Join-Path $PSScriptRoot "app_name.txt") -Raw).Trim()
$Source = Join-Path $PSScriptRoot "release\$AppName"
$OutDir = Join-Path $PSScriptRoot "release"
$Stamp = Get-Date -Format "yyyy-MM-dd"
$ZipPath = Join-Path $OutDir "$AppName-portable-$Stamp.zip"

if (-not (Test-Path $Source)) {
    throw "Release folder not found: $Source`nRun build-portable.ps1 first."
}

$Stage = Join-Path $env:TEMP "shakti-dist-$(Get-Random)"
$StageApp = Join-Path $Stage $AppName
New-Item -ItemType Directory -Force -Path $StageApp | Out-Null

Write-Host "Staging from: $Source" -ForegroundColor Cyan
robocopy $Source $StageApp /E /XD ".git" /XF "instagram_state.json" "instagram_meta.json" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }

# Strip secrets from staged copy; ship template only
$StageAppData = Join-Path $StageApp "app_data"
$StageDocs = Join-Path $StageAppData "docs"
New-Item -ItemType Directory -Force -Path $StageDocs | Out-Null
Remove-Item -Force (Join-Path $StageAppData ".env") -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $PSScriptRoot ".env.portable") (Join-Path $StageDocs "env.example")
@"
Shakti - the 3rd Eye | Distribution package
============================================

1. Unzip this entire folder (do NOT move only the .exe).
2. Show hidden items in File Explorer (View -> Hidden items).
3. Copy app_data\docs\env.example to app_data\.env and edit DATABASE_URL + JWT_SECRET_KEY.
4. Double-click "Shakti - the 3rd Eye.exe"
5. Settings -> Connect Instagram (once per PC)

Release root contains only:
  Shakti - the 3rd Eye.exe | _internal\ | playwright-browsers\ | storage\ | app_data\
"@ | Set-Content -Encoding UTF8 (Join-Path $StageDocs "README-DISTRIBUTION.txt")
cmd /c "attrib +h `"$StageAppData`"" 2>$null | Out-Null

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $StageApp -DestinationPath $ZipPath -CompressionLevel Optimal

Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Created: $ZipPath" -ForegroundColor Green
Write-Host "Size: ${sizeMb} MB (send this ZIP)" -ForegroundColor Green
Write-Host "Excluded: .env, instagram session files" -ForegroundColor Yellow
