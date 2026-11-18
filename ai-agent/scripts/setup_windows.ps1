# ==============================================================================
# Universal AI Job Search and Application Agent - Windows Automated Setup Script
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  UNIVERSAL AI JOB SEARCH & APPLICATION AGENT - ENVIRONMENT SETUP" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 1. Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Host "Python not found. Attempting install via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Python 3.12 installation complete. Please restart terminal if needed." -ForegroundColor Green
} else {
    $PyVersion = & python --version
    Write-Host "  Found: $PyVersion" -ForegroundColor Green
}

# 2. Check Ollama
Write-Host "`n[2/6] Checking Ollama installation..." -ForegroundColor Yellow
$OllamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $OllamaCmd) {
    Write-Host "Ollama not found. Attempting install via winget..." -ForegroundColor Yellow
    winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
    Write-Host "Ollama installed. Launching Ollama in system tray..." -ForegroundColor Green
    Start-Process ollama -ArgumentList "serve"
} else {
    Write-Host "  Ollama detected in PATH." -ForegroundColor Green
}

# 3. Pull Recommended Ollama Models
Write-Host "`n[3/6] Pulling recommended local models in Ollama..." -ForegroundColor Yellow
Write-Host "  - Pulling qwen2.5:7b-instruct (reasoning engine)..." -ForegroundColor Gray
ollama pull qwen2.5:7b-instruct
Write-Host "  - Pulling nomic-embed-text (dense vector embeddings)..." -ForegroundColor Gray
ollama pull nomic-embed-text

# 4. Create Isolated Python Virtual Environment
Write-Host "`n[4/6] Initializing isolated virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  Created virtual environment in .venv" -ForegroundColor Green
} else {
    Write-Host "  Virtual environment .venv already exists." -ForegroundColor Green
}

# 5. Install Backend Dependencies
Write-Host "`n[5/6] Installing backend dependencies into .venv..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r backend\requirements.txt

# 6. Install Playwright Chromium Browser
Write-Host "`n[6/6] Installing isolated Playwright browser binaries..." -ForegroundColor Yellow
& .\.venv\Scripts\playwright.exe install chromium

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE! System is fully prepared in local-first mode." -ForegroundColor Green
Write-Host "  To start the application, run: .\scripts\start_all.bat" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
