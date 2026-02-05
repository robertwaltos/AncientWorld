# AncientWorld Discovery Launcher
# Run this script to start the Wikimedia Commons discovery spider

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AncientWorld Discovery Spider" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "[OK] Virtual environment active" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Virtual environment not active" -ForegroundColor Yellow
    Write-Host "Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Navigate to ancientgeo directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptPath\ancientgeo"

Write-Host "Starting discovery spider..." -ForegroundColor Green
Write-Host "This will search Wikimedia Commons for ancient architecture images" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Run scrapy
& python -m scrapy crawl commons_discover

Write-Host ""
Write-Host "Discovery complete!" -ForegroundColor Green
Write-Host "Check database with: streamlit run src\ui\web\dashboard.py" -ForegroundColor Cyan
