@echo off
setlocal enabledelayedexpansion
title Universal AI Job Search Agent - Backend Service

echo ==============================================================================
echo [AI Job Agent] Initializing Backend Service...
echo ==============================================================================

cd /d "%~dp0\.."

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.12+ and ensure 'Add Python to PATH' is checked.
    pause
    exit /b 1
)

:: Virtual environment check
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo [INFO] Installing required backend packages...
    python -m pip install --upgrade pip
    if exist "backend\requirements.txt" (
        pip install -r backend\requirements.txt
    )
) else (
    call .venv\Scripts\activate.bat
)

:: Ollama availability check
echo [INFO] Verifying local Ollama connectivity (http://127.0.0.1:11434)...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama is not detected at http://127.0.0.1:11434.
    echo Please ensure Ollama is installed and running for local AI features.
) else (
    echo [OK] Ollama is online and responsive.
)

:: Run Backend Server
echo [INFO] Starting FastAPI application on http://127.0.0.1:8000...
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
