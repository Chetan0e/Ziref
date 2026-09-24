Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "               ZIREF DEVELOPER PLATFORM                    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Attempt Docker datastores boot (graceful fallback if Docker Desktop isn't active)
Write-Host "==> Checking background datastores (MongoDB & Redis)..." -ForegroundColor Yellow
try {
    docker compose up -d mongodb redis 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker datastores running." -ForegroundColor Green
    } else {
        Write-Host "ℹ Docker not detected or inactive. Ziref embedded datastores will activate automatically." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "ℹ Using embedded MemoryDatabase and MemoryRedis." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "==> Launch Commands for Local Development:" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"
Write-Host "Terminal 1 (API):         .\.venv\Scripts\uvicorn services.api.main:app --port 8000 --reload" -ForegroundColor White
Write-Host "Terminal 2 (Worker):      .\.venv\Scripts\python -m services.worker.main" -ForegroundColor White
Write-Host "Terminal 3 (Site Router): .\.venv\Scripts\python -m services.deployer.main" -ForegroundColor White
Write-Host "Terminal 4 (Dashboard):   pnpm --filter dashboard dev" -ForegroundColor White
Write-Host "----------------------------------------------------------"
Write-Host ""
Write-Host "Platform Endpoints:" -ForegroundColor Green
Write-Host "  • Web Dashboard:  http://localhost:3000" -ForegroundColor White
Write-Host "  • API Backend:    http://localhost:8000" -ForegroundColor White
Write-Host "  • OpenAPI Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • Site Router:    http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "CLI Quickstart:" -ForegroundColor Cyan
Write-Host "  .\scripts\ziref.ps1 login" -ForegroundColor White
Write-Host "  .\scripts\ziref.ps1 deploy" -ForegroundColor White
Write-Host "  .\scripts\ziref.ps1 appify <project-slug>" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
