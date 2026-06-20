$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"

function Test-Port5432 {
    $result = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
    return [bool]$result.TcpTestSucceeded
}

Set-Location $Root

if (-not (Test-Port5432)) {
    Write-Host "Postgres is not listening on localhost:5432. Trying Docker Compose postgres..." -ForegroundColor Yellow

    try {
        docker info *> $null
        $dockerExitCode = $LASTEXITCODE
    }
    catch {
        $dockerExitCode = 1
    }

    if ($dockerExitCode -ne 0) {
        Write-Host "Docker Desktop is not running. Start Docker Desktop, then run this script again." -ForegroundColor Red
        exit 1
    }

    docker compose up -d postgres

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Port5432) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        Write-Host "Postgres did not become ready on localhost:5432 within 30 seconds." -ForegroundColor Red
        exit 1
    }
}

Set-Location $Backend
python -m uvicorn app.main:app --reload
