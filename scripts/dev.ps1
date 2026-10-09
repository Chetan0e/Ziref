# ==========================================================
#                  ZIREF -- ONE-COMMAND DEV LAUNCHER
#  Starts all 4 services in parallel background jobs and
#  tails their combined output in this terminal window.
#  Press Ctrl+C to stop everything cleanly.
# ==========================================================

$Root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "              ZIREF DEVELOPER PLATFORM                     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# -- Port conflict check & auto-resolve for SiteRouter ------
$ports = @(8000, 8080, 3000)
foreach ($port in $ports) {
    $inUse = netstat -ano 2>$null | Select-String ":$port " | Select-String "LISTENING"
    if ($inUse) {
        Write-Host "[WARN] Port $port is already in use. Another process may be running." -ForegroundColor Yellow
    }
}

# Find a free port for the SiteRouter (start at 8080, increment until free)
$siteRouterPort = 8080
while ($true) {
    $taken = netstat -ano 2>$null | Select-String ":$siteRouterPort " | Select-String "LISTENING"
    if (-not $taken) { break }
    $siteRouterPort++
}
if ($siteRouterPort -ne 8080) {
    Write-Host "[INFO] Port 8080 in use -- SiteRouter will bind to port $siteRouterPort instead." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "==> Checking Docker datastores (MongoDB & Redis)..." -ForegroundColor Yellow
try {
    docker compose up -d mongodb redis 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Docker datastores started (MongoDB :27017, Redis :6379)" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Docker not detected -- embedded in-memory datastores will activate automatically." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "[INFO] Using embedded MemoryDatabase and MemoryRedis (no Docker required)." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "==> Launching all services..." -ForegroundColor Cyan
Write-Host ""

# -- Start each service as a background job ------------------
$venv = Join-Path $Root ".venv\Scripts"

$jobs = @(
    Start-Job -Name "API"        -ScriptBlock { param($r,$v) Set-Location $r; & "$v\uvicorn" services.api.main:app --port 8000 --reload --reload-dir services 2>&1 } -ArgumentList $Root, $venv
    Start-Job -Name "Worker"     -ScriptBlock { param($r,$v) Set-Location $r; & "$v\python" -m services.worker.main 2>&1 }                     -ArgumentList $Root, $venv
    Start-Job -Name "SiteRouter" -ScriptBlock { param($r,$v,$p) Set-Location $r; $env:SITE_ROUTER_PORT=$p; & "$v\python" -m services.deployer.main 2>&1 } -ArgumentList $Root, $venv, $siteRouterPort
    Start-Job -Name "Dashboard"  -ScriptBlock { param($r)    Set-Location $r; pnpm --filter dashboard dev 2>&1 }                                -ArgumentList $Root
)

Write-Host "[OK] API Gateway     -> http://localhost:8000" -ForegroundColor Green
Write-Host "[OK] API Docs        -> http://localhost:8000/docs" -ForegroundColor Green
Write-Host "[OK] Worker Daemon   -> (background)" -ForegroundColor Green
Write-Host "[OK] Site Router     -> http://localhost:$siteRouterPort" -ForegroundColor Green
Write-Host "[OK] Dashboard UI    -> http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services." -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# -- Color map per service ------------------------------------
$colors = @{
    "API"        = "Cyan"
    "Worker"     = "Magenta"
    "SiteRouter" = "Yellow"
    "Dashboard"  = "Blue"
}

# -- Stream combined output until Ctrl+C ----------------------
try {
    while ($true) {
        foreach ($job in $jobs) {
            $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($output) {
                $col = $colors[$job.Name]
                foreach ($line in $output) {
                    Write-Host "[$($job.Name.PadRight(10))] $line" -ForegroundColor $col
                }
            }
        }

        # If any job stopped unexpectedly, report it
        $stoppedJobs = $jobs | Where-Object { $_.State -eq "Failed" -or $_.State -eq "Completed" }
        foreach ($job in $stoppedJobs) {
            Write-Host "[ERROR] Service '$($job.Name)' stopped unexpectedly. Check logs above." -ForegroundColor Red
            $jobs = $jobs | Where-Object { $_.Id -ne $job.Id }
        }

        Start-Sleep -Milliseconds 300
    }
} finally {
    # -- Cleanup on Ctrl+C ------------------------------------
    Write-Host ""
    Write-Host "==> Stopping all Ziref services..." -ForegroundColor Yellow
    $jobs | Stop-Job -ErrorAction SilentlyContinue
    $jobs | Remove-Job -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] All services stopped." -ForegroundColor Green
    Write-Host ""
}
