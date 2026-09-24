Write-Host "==> Building Docker Sandbox Image (ziref-sandbox-node)..." -ForegroundColor Cyan
docker build -t ziref-sandbox-node:latest -f infrastructure/docker/sandbox-node/Dockerfile .
if ($LASTEXITCODE -eq 0) {
    Write-Host "Sandbox image built successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to build sandbox image." -ForegroundColor Red
}
