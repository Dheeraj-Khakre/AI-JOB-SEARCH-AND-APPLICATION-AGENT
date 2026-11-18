@echo off
title Universal AI Job Search Agent - Frontend UI

echo ==============================================================================
echo [AI Job Agent] Initializing Frontend Application...
echo ==============================================================================

cd /d "%~dp0\..\frontend"

:: Check Node.js
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js 20+ LTS from https://nodejs.org/
    pause
    exit /b 1
)

:: Check node_modules
if not exist "node_modules\" (
    echo [INFO] Installing frontend dependencies...
    call npm install
)

echo [INFO] Starting Vite Development Server on http://localhost:5173...
call npm run dev
