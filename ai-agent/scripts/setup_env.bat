@echo off
title AI Job Agent - Windows Bootstrap
echo ==============================================================================
echo [AI Job Agent] Launching Windows Setup PowerShell Script...
echo ==============================================================================
powershell -ExecutionPolicy Bypass -File "%~dp0\setup_windows.ps1"
pause
