# Relanza descargas masivas en D:\Media (ejecutar cuando Docker responda).
param(
    [string]$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
)

$ErrorActionPreference = "Stop"
$Deploy = Join-Path $PSScriptRoot ".."
Set-Location $Deploy

Write-Host "==> Forzar D:/Media"
& (Join-Path $PSScriptRoot "resolve-media-path.ps1") -ForceDrive D -UpdateEnv

Write-Host "==> Recrear contenedores con montaje D:"
& $DockerExe compose --env-file .env up -d --build --force-recreate qbittorrent catalog-metadata storage-hls

Start-Sleep -Seconds 20

Write-Host "==> Verificar montaje"
& (Join-Path $PSScriptRoot "verify-d-mount.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Corrige Docker File sharing para D: antes de continuar."
    exit 1
}

Write-Host "==> Import seed"
& $DockerExe exec skill-catalog-metadata python -c @"
import urllib.request, json
req = urllib.request.Request(
    'http://localhost:8004/api/v1/import',
    data=json.dumps({'source': 'seed'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST')
print(urllib.request.urlopen(req).read().decode())
"@

Write-Host "==> Bulk acquire películas"
& $DockerExe exec skill-catalog-metadata python -c @"
import urllib.request, json
body = {'content_type': 'movie', 'enrich_first': False, 'dry_run': False}
req = urllib.request.Request(
    'http://localhost:8004/api/v1/bulk-acquire',
    data=json.dumps(body).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST')
print(urllib.request.urlopen(req, timeout=3600).read().decode())
"@

Write-Host "==> Estado"
& $DockerExe exec skill-catalog-metadata python -c @"
import urllib.request
print(urllib.request.urlopen('http://localhost:8004/api/v1/bulk-acquire/status').read().decode())
"@

Write-Host "==> qBittorrent: http://localhost:8080"
Write-Host "==> Descargas en D:\Media"
