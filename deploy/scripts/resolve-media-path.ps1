# Resuelve MEDIA_HOST_PATH. Por defecto solo D:\Media; -ForceDrive D sin fallback.
param(
    [switch]$UpdateEnv,
    [string]$EnvFile = (Join-Path $PSScriptRoot "..\.env"),
    [ValidateSet('E', 'D', 'C')]
    [string]$PreferDrive = 'D',
    [ValidateSet('E', 'D', 'C')]
    [string]$ForceDrive
)

$ErrorActionPreference = "Stop"

$candidates = @(
    @{ Path = "E:\Media"; Label = "WD Elements (E:)"; Drive = 'E' },
    @{ Path = "D:\Media"; Label = "External USB (D:)"; Drive = 'D' },
    @{ Path = "C:\Users\Administrator\OneDrive\Documents\streaming\media"; Label = "Local project media (C:)"; Drive = 'C' }
)

function Test-WritableMediaPath {
    param([string]$MediaPath)
    $root = Split-Path $MediaPath -Parent
    if (-not (Test-Path $root)) {
        return $false
    }
    try {
        New-Item -ItemType Directory -Force -Path $MediaPath -ErrorAction Stop | Out-Null
        $testFile = Join-Path $MediaPath ".write-test"
        "ok" | Set-Content -Path $testFile -Encoding ascii -ErrorAction Stop
        Remove-Item -Force $testFile -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

if ($ForceDrive) {
    $chosen = $candidates | Where-Object { $_.Drive -eq $ForceDrive } | Select-Object -First 1
    if (-not $chosen) {
        Write-Error "Unknown ForceDrive: $ForceDrive"
    }
    if (-not (Test-WritableMediaPath -MediaPath $chosen.Path)) {
        Write-Error "ForceDrive ${ForceDrive}: no se puede escribir en $($chosen.Path). Comprueba que el disco está conectado."
    }
} else {
    if ($PreferDrive) {
        $preferred = $candidates | Where-Object { $_.Drive -eq $PreferDrive }
        $rest = $candidates | Where-Object { $_.Drive -ne $PreferDrive }
        $candidates = @($preferred) + @($rest)
    }
    $chosen = $null
    foreach ($c in $candidates) {
        if (Test-WritableMediaPath -MediaPath $c.Path) {
            $chosen = $c
            break
        }
    }
    if (-not $chosen) {
        Write-Error "No writable media path found among E:, D:, or C: fallback."
    }
}

$dockerPath = ($chosen.Path -replace '\\', '/')
Write-Output "MEDIA_HOST_PATH=$dockerPath"
Write-Output "BULK_ACQUIRE_HOST_MEDIA_PATH=$dockerPath"
Write-Output "# Selected: $($chosen.Label)"

if ($UpdateEnv) {
    if (-not (Test-Path $EnvFile)) {
        Write-Error "Env file not found: $EnvFile"
    }
    $lines = Get-Content $EnvFile -Encoding utf8
    $foundMedia = $false
    $foundBulk = $false
    $out = foreach ($line in $lines) {
        if ($line -match '^\s*MEDIA_HOST_PATH=') {
            $foundMedia = $true
            "MEDIA_HOST_PATH=$dockerPath"
        } elseif ($line -match '^\s*BULK_ACQUIRE_HOST_MEDIA_PATH=') {
            $foundBulk = $true
            "BULK_ACQUIRE_HOST_MEDIA_PATH=$dockerPath"
        } else {
            $line
        }
    }
    if (-not $foundMedia) {
        $out = @("MEDIA_HOST_PATH=$dockerPath") + $out
    }
    if (-not $foundBulk) {
        $out = @("BULK_ACQUIRE_HOST_MEDIA_PATH=$dockerPath") + $out
    }
    Set-Content -Path $EnvFile -Value $out -Encoding utf8
    Write-Output "Updated $EnvFile"
}

return $dockerPath
