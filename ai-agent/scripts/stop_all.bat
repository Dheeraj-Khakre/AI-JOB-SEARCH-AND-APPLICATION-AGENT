@echo off
title Universal AI Job Search Agent - Shutdown

echo ==============================================================================
echo [AI Job Agent] Gracefully Shutting Down All Services...
echo ==============================================================================

:: Terminate named windows
taskkill /FI "WINDOWTITLE eq AI Agent Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AI Agent Frontend*" /T /F >nul 2>&1

:: Terminate running server processes safely
taskkill /IM uvicorn.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1

echo [OK] All services and background processes have been stopped.
timeout /t 2 >nul
