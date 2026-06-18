$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Create it first with: python -m venv .venv"
}

Set-Location $ProjectRoot

& $Python -m pip install -r requirements-build.txt
& $Python -m PyInstaller --clean --noconfirm etl_dashboard.spec

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist\etl-dashboard\etl-dashboard.exe"
Write-Host ""
Write-Host "Place a .env file next to the exe with DATABASE_URL before running it."
