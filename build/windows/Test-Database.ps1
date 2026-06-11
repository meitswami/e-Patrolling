# Test Supabase DATABASE_URL from portable app_data\.env
param(
    [string]$ReleaseDir = ""
)
$ErrorActionPreference = "Stop"
if (-not $ReleaseDir) {
    $AppName = (Get-Content (Join-Path $PSScriptRoot "app_name.txt") -Raw).Trim()
    $ReleaseDir = Join-Path $PSScriptRoot "release\$AppName"
}
$EnvFile = Join-Path $ReleaseDir "app_data\.env"
if (-not (Test-Path $EnvFile)) { $EnvFile = Join-Path $ReleaseDir ".env" }
if (-not (Test-Path $EnvFile)) { Write-Error "No .env in app_data\ or release root"; exit 1 }

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line -match "=") {
        $name, $value = $line -split "=", 2
        Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim().Trim('"')
    }
}

$url = $env:DATABASE_URL
if (-not $url) { Write-Error "DATABASE_URL missing"; exit 1 }
if ($url -match "YOUR_PASSWORD") { Write-Error "Replace YOUR_PASSWORD in app_data\.env"; exit 1 }

$py = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

& $py -c @"
import asyncio, os, re, sys
import asyncpg

raw = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
m = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)', raw)
if not m:
    print('Invalid DATABASE_URL format'); sys.exit(1)
user, password, host, port, db = m.groups()
print(f'Host: {host}')
print(f'User: {user}')
print(f'Port: {port}')

async def main():
    try:
        conn = await asyncpg.connect(host=host, port=int(port), user=user, password=password, database=db, ssl='require')
        val = await conn.fetchval('select 1')
        await conn.close()
        print('SUCCESS: Database connected (select 1 =', val, ')')
    except Exception as e:
        print('FAILED:', e)
        sys.exit(1)

asyncio.run(main())
"@
