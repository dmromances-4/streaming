# Aplica configuración D: + recrea contenedores + verifica + lanza bulk-acquire.
param(
    [switch]$SkipBulk,
    [string]$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
)

$ErrorActionPreference = "Stop"
$Deploy = Join-Path $PSScriptRoot ".."
Set-Location $Deploy

Write-Host "==> 1. Forzar D:/Media en .env"
& (Join-Path $PSScriptRoot "resolve-media-path.ps1") -PreferDrive D -ForceDrive -UpdateEnv

Write-Host "==> 2. Crear carpetas D:\Media"
New-Item -ItemType Directory -Force -Path "D:\Media\movies", "D:\Media\series" | Out-Null

if (-not (Test-Path $DockerExe)) { $DockerExe = "docker" }

Write-Host "==> 3. Recrear contenedores con montaje D:"
& $DockerExe compose --env-file .env up -d --force-recreate qbittorrent catalog-metadata storage-hls
Start-Sleep -Seconds 20

Write-Host "==> 4. Verificar montaje"
& (Join-Path $PSScriptRoot "verify-d-mount.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> 5. Limpiar torrents con archivos faltantes (qBittorrent API)"
$loginBody = "username=admin&password=adminadmin"
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8080/api/v2/auth/login" -Method POST -Body $loginBody -UseBasicParsing -TimeoutSec 15
    $torrents = (Invoke-WebRequest -Uri "http://localhost:8080/api/v2/torrents/info" -UseBasicParsing -TimeoutSec 30).Content | ConvertFrom-Json
    $missing = @($torrents | Where-Object { $_.state -match 'missingFiles|error' })
    if ($missing.Count -gt 0) {
        $hashes = ($missing | ForEach-Object { $_.hash }) -join "|"
        Invoke-WebRequest -Uri "http://localhost:8080/api/v2/torrents/delete" -Method POST `
            -Body "hashes=$hashes&deleteFiles=false" -UseBasicParsing -TimeoutSec 30 | Out-Null
        Write-Host "Eliminados $($missing.Count) torrents rotos"
    } else {
        Write-Host "No hay torrents rotos"
    }
} catch {
    Write-Warning "No se pudo limpiar qBittorrent: $_"
}

if ($SkipBulk) {
    Write-Host "SkipBulk: no se lanza bulk-acquire"
    exit 0
}

Write-Host "==> 6. Import seed + bulk-acquire películas"
$py = @'
import urllib.request, json
def post(path, body):
    req = urllib.request.Request(
        f"http://localhost:8004/api/v1{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=3600).read().decode()
print("import:", post("/import", {"source": "seed"}))
print("bulk:", post("/bulk-acquire", {"content_type": "movie", "enrich_first": False, "dry_run": False}))
print("status:", urllib.request.urlopen("http://localhost:8004/api/v1/bulk-acquire/status").read().decode())
'@
& $DockerExe exec skill-catalog-metadata python -c $py

Write-Host ""
Write-Host "Listo. qBittorrent: http://localhost:8080"
Write-Host "Descargas en D:\Media"
