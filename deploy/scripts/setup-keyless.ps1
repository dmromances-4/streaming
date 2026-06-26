# Configuración sin cuentas externas (sin TMDB, sin registrarse en indexers)

param(
    [switch]$UpdateEnv,
    [string]$EnvFile = (Join-Path $PSScriptRoot "..\.env"),
    [string]$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "==> Resolviendo ruta de descargas (solo D:)"
& (Join-Path $PSScriptRoot "resolve-media-path.ps1") -ForceDrive D -UpdateEnv:$UpdateEnv -EnvFile $EnvFile | Out-Host

Write-Host ""
Write-Host "==> API key local de Prowlarr (si el contenedor está levantado)"
$apiKey = ""
if (Test-Path $DockerExe) {
    try {
        $xml = & $DockerExe exec skill-prowlarr cat /config/config.xml 2>$null
        if ($xml -match '<ApiKey>([^<]+)</ApiKey>') {
            $apiKey = $Matches[1].Trim()
            Write-Host "OK: clave leída del config.xml de Prowlarr"
        } else {
            Write-Host "AVISO: Prowlarr aún no tiene config.xml (primera vez que arranca)"
        }
    } catch {
        Write-Host "AVISO: contenedor skill-prowlarr no disponible todavía"
    }
}

if ($UpdateEnv -and $apiKey -and (Test-Path $EnvFile)) {
    $lines = Get-Content $EnvFile -Encoding utf8
    $out = foreach ($line in $lines) {
        if ($line -match '^\s*INDEXER_API_KEY=') { "INDEXER_API_KEY=$apiKey" } else { $line }
    }
    if (-not ($out -match '^\s*INDEXER_API_KEY=')) {
        $out = @("INDEXER_API_KEY=$apiKey") + $out
    }
    Set-Content -Path $EnvFile -Value $out -Encoding utf8
    Write-Host "Actualizado INDEXER_API_KEY en $EnvFile"
}

Write-Host ""
Write-Host "==> Resumen modo sin claves"
Write-Host "- TMDB: opcional (vacío = búsqueda por título + alias)"
Write-Host "- Prowlarr: clave local automática; indexers opcionales"
Write-Host "- YTS: respaldo público si Prowlarr no encuentra nada"
Write-Host "- Limitación: YTS cubre sobre todo cine internacional en inglés"
Write-Host "- Películas españolas/catalanas: dependen de alias en search_queries"
