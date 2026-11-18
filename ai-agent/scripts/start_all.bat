@echo off
title Universal AI Job Search Agent - Controller

echo ==============================================================================
echo [AI Job Agent] Launching Full Application Stack (Windows Local-First)
echo ==============================================================================

cd /d "%~dp0\.."

:: 1. Launch Backend
start "AI Agent Backend" cmd /k "scripts\start_backend.bat"

:: 2. Launch Frontend
start "AI Agent Frontend" cmd /k "scripts\start_frontend.bat"

:: 3. Await and Launch Browser
echo [INFO] Waiting for services to initialize...
timeout /t 5 >nul

echo [INFO] Opening Web Dashboard in default browser...
start http://localhost:5173

echo ==============================================================================
echo System running!
echo - Web Dashboard: http://localhost:5173
echo - API Documentation: http://127.0.0.1:8000/docs
echo - To stop all services: run scripts\stop_all.bat
echo ==============================================================================
