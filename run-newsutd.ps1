$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found at $venvPython"
}

$backendCommand = @(
    "Set-Location '$backendDir'"
    "& '$venvPython' -m pip install -r requirements.txt"
    "& '$venvPython' -m uvicorn alert_server:app --reload --host 127.0.0.1 --port 8000"
) -join "; "

$frontendCommand = @(
    "Set-Location '$frontendDir'"
    "npm install"
    "npm run dev"
) -join "; "

Write-Host "Starting NewsUTD Market Signal Monitor..."
Write-Host "Home:    http://127.0.0.1:5173/"
Write-Host "Monitor: http://127.0.0.1:5173/monitor"
Write-Host "API:     http://127.0.0.1:8000/health"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand
