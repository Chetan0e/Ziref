Write-Host "==> Starting Ziref Infrastructure with Docker Compose..." -ForegroundColor Cyan
docker compose up -d mongodb redis

Write-Host ""
Write-Host "Ziref Datastores are UP:" -ForegroundColor Green
Write-Host " - MongoDB: mongodb://localhost:27017/ziref"
Write-Host " - Redis:   redis://localhost:6379/0"
Write-Host ""
Write-Host "To launch services individually for development:" -ForegroundColor Yellow
Write-Host " 1. API:        .\.venv\Scripts\uvicorn services.api.main:app --port 8000 --reload"
Write-Host " 2. Worker:     .\.venv\Scripts\python -m services.worker.main"
Write-Host " 3. Deployer:   .\.venv\Scripts\python -m services.deployer.main"
Write-Host " 4. Dashboard:  pnpm --filter dashboard dev"
Write-Host ""
Write-Host "Or launch the entire platform containerized:" -ForegroundColor Cyan
Write-Host " docker compose up -d"
