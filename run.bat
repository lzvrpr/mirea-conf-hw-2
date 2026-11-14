@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import aiohttp" 2>nul
if errorlevel 1 (
    echo aiohttp is not installed for this interpreter: %PY%
    echo Install it with: "%PY%" -m pip install -r requirements.txt
    pause
    exit /b 1
)
"%PY%" main.py %*
