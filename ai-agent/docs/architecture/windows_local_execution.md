# Windows Local Execution & Environment Setup Guide

## 1. System Requirements

- **Operating System**: Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **CPU**: Modern x64 processor (Intel Core i5/i7/i9 10th Gen+ or AMD Ryzen 5/7/9 3000+).
- **RAM**: Minimum 16 GB (Recommended 32 GB for concurrent 7B LLM inference and Playwright browser execution).
- **GPU (Optional)**: NVIDIA GPU with 6GB+ VRAM (GTX 1660 Ti, RTX 2060/3060/4060+) for hardware-accelerated local inference.

---

## 2. Software Prerequisites Installation

### A. Python 3.12+
Download and run the Windows 64-bit installer from [python.org](https://www.python.org/downloads/):
- **Crucial**: Check the box **"Add Python to PATH"** during installation.
- Verify:
  ```powershell
  python --version
  ```

### B. Node.js 20+ LTS
Download and install from [nodejs.org](https://nodejs.org/):
- Verify:
  ```powershell
  node --version
  npm --version
  ```

### C. Ollama for Windows
Download and install the native Windows package from [ollama.ai](https://ollama.ai/download/windows).
Ollama runs in the system tray and exposes `http://127.0.0.1:11434`.
- Pull the required models:
  ```cmd
  ollama pull qwen2.5:7b-instruct
  ollama pull nomic-embed-text
  ```
- Test Ollama:
  ```cmd
  ollama run qwen2.5:7b-instruct "Respond with 'Ollama is operational'"
  ```

---

## 3. Automation Scripts Blueprint

All service management scripts are located in `scripts/`:

### `scripts\start_backend.bat`
```batch
@echo off
title AI Job Agent - Backend Service
echo [1/3] Checking Python virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r backend\requirements.txt
    playwright install chromium
) else (
    call .venv\Scripts\activate.bat
)

echo [2/3] Checking Ollama health...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Ollama is not running on 127.0.0.1:11434. Starting in background...
    start /b ollama serve
    timeout /t 3 >nul
)

echo [3/3] Starting FastAPI Backend on http://127.0.0.1:8000...
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### `scripts\start_frontend.bat`
```batch
@echo off
title AI Job Agent - Frontend UI
cd frontend
if not exist "node_modules\" (
    echo Installing frontend dependencies...
    call npm install
)
echo Starting React Vite Dev Server on http://localhost:5173...
call npm run dev
```

### `scripts\start_all.bat`
```batch
@echo off
title AI Job Agent - Startup Controller
echo =========================================================
echo Launching Universal AI Job Search and Application Agent
echo =========================================================
start "AI Agent Backend" cmd /c "scripts\start_backend.bat"
start "AI Agent Frontend" cmd /c "scripts\start_frontend.bat"

echo Waiting for services to initialize...
timeout /t 5 >nul
echo Launching web browser...
start http://localhost:5173
echo System operational.
```

### `scripts\stop_all.bat`
```batch
@echo off
title AI Job Agent - Shutdown
echo Stopping services...
taskkill /FI "WINDOWTITLE eq AI Agent Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AI Agent Frontend*" /T /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
echo All AI Job Agent services stopped cleanly.
```
