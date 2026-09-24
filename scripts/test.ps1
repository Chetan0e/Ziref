Write-Host "==> Running Python Unit & Integration Tests..." -ForegroundColor Cyan
.\.venv\Scripts\python -m pytest tests/
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "==> Verifying Dashboard Build & Types..." -ForegroundColor Cyan
pnpm --filter dashboard build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dashboard build failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "==> All Tests and Builds Passed Successfully!" -ForegroundColor Green
