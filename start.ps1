# AI Agent Workflow - Local Start Script
Set-Location $PSScriptRoot

Write-Host "=== 0/3 Start Docker containers ===" -ForegroundColor Green
$dockerAvailable = $false
try {
    docker compose up -d 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker containers started (PostgreSQL + Redis + Chroma)" -ForegroundColor Green
        $dockerAvailable = $true
    }
} catch {
    Write-Host "Docker not available, using fallback mode" -ForegroundColor Yellow
}

# Write-Host "=== 1/3 Install backend dependencies ===" -ForegroundColor Green
# .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
# if ($LASTEXITCODE -ne 0) {
#     Write-Host "ERROR: Dependency install failed!" -ForegroundColor Red
#     exit 1
# }

Write-Host "=== 2/3 Start backend (FastAPI) ===" -ForegroundColor Green
$backendJob = Start-Job -Name "Backend" -ScriptBlock {
    Set-Location $using:PSScriptRoot
    Set-Location backend
    & "$using:PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}
Write-Host "Backend starting (Job ID: $($backendJob.Id))..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 3 -UseBasicParsing
    Write-Host "Backend is ready!" -ForegroundColor Green
} catch {
    Write-Host "Backend may still be starting..." -ForegroundColor Yellow
}

Write-Host "=== 3/3 Start frontend (Vue3) ===" -ForegroundColor Green
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}

$frontendJob = Start-Job -Name "Frontend" -ScriptBlock {
    Set-Location "$using:PSScriptRoot\frontend"
    npm run dev
}
Start-Sleep -Seconds 3
Write-Host "Frontend starting (Job ID: $($frontendJob.Id))..." -ForegroundColor Yellow

Write-Host ""
Write-Host "=== All services started ===" -ForegroundColor Green
Write-Host "  Backend API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
if ($dockerAvailable) {
    Write-Host "Production mode (Docker):" -ForegroundColor Green
    Write-Host "  - Database:   PostgreSQL" -ForegroundColor Green
    Write-Host "  - Chroma:     HTTP (:8001)" -ForegroundColor Green
    Write-Host "  - Redis:      Redis (:6379)" -ForegroundColor Green
} else {
    Write-Host "Fallback mode (no Docker):" -ForegroundColor Yellow
    Write-Host "  - Database:   SQLite" -ForegroundColor Yellow
    Write-Host "  - Chroma:     Local" -ForegroundColor Yellow
    Write-Host "  - Redis:      In-memory only" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Logs:  Receive-Job -Id $($backendJob.Id) -Keep" -ForegroundColor DarkGray
Write-Host "Stop:  Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor DarkGray
