# Verifica que D:\Media está montado correctamente en Docker (no el bug de 137 MB).
param(
    [string]$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    [double]$MinFreeGbHost = 50,
    [double]$MinFreeGbContainer = 100
)

$ErrorActionPreference = "Stop"

Write-Host "==> Verificación montaje D:\Media"

if (-not (Test-Path "D:\")) {
    Write-Error "La unidad D: no está disponible. Conecta el disco EXTERNAL_USB."
}

New-Item -ItemType Directory -Force -Path "D:\Media\movies", "D:\Media\series" | Out-Null

$vol = Get-Volume -DriveLetter D -ErrorAction SilentlyContinue
if ($vol) {
    $hostFreeGb = [math]::Round($vol.SizeRemaining / 1GB, 1)
    $hostTotalGb = [math]::Round($vol.Size / 1GB, 1)
    Write-Host "Host D: $hostFreeGb GB libres de $hostTotalGb GB"
    if ($hostFreeGb -lt $MinFreeGbHost) {
        Write-Warning "Poco espacio en D: en Windows ($hostFreeGb GB)"
    }
} else {
    Write-Warning "No se pudo leer Get-Volume D:"
    $hostFreeGb = 0
}

if (-not (Test-Path $DockerExe)) {
    Write-Error "Docker no encontrado en $DockerExe"
}

$running = & $DockerExe ps --format "{{.Names}}" 2>$null | Select-String "skill-qbittorrent"
if (-not $running) {
    Write-Error "Contenedor skill-qbittorrent no está en ejecución. Ejecuta: docker compose up -d qbittorrent"
}

$mount = & $DockerExe inspect skill-qbittorrent --format '{{range .Mounts}}{{if eq .Destination "/downloads"}}{{.Source}}{{end}}{{end}}' 2>&1
Write-Host "Montaje bind: $mount"
if ($mount -notmatch '[Dd]:[/\\]Media') {
    Write-Warning "El bind no apunta a D:\Media. Revisa MEDIA_HOST_PATH en deploy/.env"
}

$df = & $DockerExe exec skill-qbittorrent df -h /downloads 2>&1
Write-Host "df dentro del contenedor:"
Write-Host $df

$containerFreeGb = 0.0
if ($df -match '(\d+(?:\.\d+)?)([KMGT])?\s+\d+(?:\.\d+)?[KMGT]?\s+(\d+(?:\.\d+)?)([KMGT])?\s+') {
    # Parse last column (Avail) from df line - simplified: look for G in Avail
}
$dfLine = ($df | Select-String '/downloads' | Select-Object -First 1).Line
if ($dfLine -match '(\d+(?:\.\d+)?)([KMGT])\s+\d+(?:\.\d+)?[KMGT]\s+\d+(?:\.\d+)?[KMGT]\s+(\d+(?:\.\d+)?)([KMGT])') {
    $availNum = [double]$Matches[3]
    $availUnit = $Matches[4]
    $containerFreeGb = switch ($availUnit) {
        'G' { $availNum }
        'M' { $availNum / 1024 }
        'K' { $availNum / 1024 / 1024 }
        'T' { $availNum * 1024 }
        default { 0 }
    }
} elseif ($dfLine -match '137M|54M|128M') {
    $containerFreeGb = 0.05
}

Write-Host "Espacio libre estimado en contenedor: $([math]::Round($containerFreeGb, 2)) GB"

if ($containerFreeGb -ge $MinFreeGbContainer) {
    Write-Host "OK: Docker ve el disco D: completo."
    exit 0
}

Write-Host ""
Write-Host "FALLO: Docker solo ve ~$([math]::Round($containerFreeGb, 2)) GB en /downloads (bug USB)."
Write-Host ""
Write-Host "Pasos manuales:"
Write-Host "  1. Docker Desktop -> Settings -> Resources -> File sharing"
Write-Host "  2. Marca la unidad D: y Apply & Restart"
Write-Host "  3. Desde deploy/: docker compose --env-file .env up -d --force-recreate qbittorrent catalog-metadata storage-hls"
Write-Host "  4. Vuelve a ejecutar: powershell -File scripts/verify-d-mount.ps1"
exit 1
