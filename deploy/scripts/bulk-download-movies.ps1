# Fase 1: importar watchlist y lanzar descarga masiva de películas.
param(
    [int]$Limit = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..\..")
$EnvFile = Join-Path $Root "deploy\.env"
$Docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

Write-Host "==> Ruta de descargas + Prowlarr local"
& (Join-Path $ScriptDir "setup-keyless.ps1") -UpdateEnv | Out-Host

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            Set-Item -Path "env:$($Matches[1].Trim())" -Value $Matches[2].Trim()
        }
    }
}

$Base = if ($env:CATALOG_URL) { $env:CATALOG_URL } else { "http://127.0.0.1/api/catalog/api/v1" }

Write-Host "==> Levantar stack (si hace falta)"
Push-Location (Join-Path $Root "deploy")
& $Docker compose --env-file .env up -d --build catalog-metadata qbittorrent prowlarr nginx 2>&1 | Out-Host
Pop-Location

Write-Host "==> Regenerar YAML de la watchlist"
python (Join-Path $ScriptDir "build-watchlist-json.py") 2>$null
python (Join-Path $ScriptDir "generate-watchlist-seed.py")

function Invoke-Catalog {
    param([string]$Method, [string]$Path, [string]$Body = $null)
    $uri = "$Base$Path"
    if ($Body) {
        return Invoke-RestMethod -Uri $uri -Method $Method -Body $Body -ContentType "application/json" -TimeoutSec 3600
    }
    return Invoke-RestMethod -Uri $uri -Method $Method -TimeoutSec 120
}

Write-Host "==> Salud del catálogo"
Invoke-Catalog GET "/health" | ConvertTo-Json

Write-Host "==> Importar semilla"
Invoke-Catalog POST "/import" '{"source":"seed"}' | ConvertTo-Json

$payload = @{
    content_type = "movie"
    enrich_first = $true
    dry_run = [bool]$DryRun
}
if ($Limit -gt 0) { $payload.limit = $Limit }

Write-Host "==> Descarga masiva de películas"
$result = Invoke-Catalog POST "/bulk-acquire" ($payload | ConvertTo-Json -Compress)
$result | ConvertTo-Json -Depth 6

Write-Host "==> Estado"
Invoke-Catalog GET "/bulk-acquire/status" | ConvertTo-Json

$reportPath = Join-Path $Root "media\bulk-acquire-report.json"
$result | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding utf8
Write-Host "Informe guardado en $reportPath"
Write-Host "qBittorrent: http://localhost:8080"
