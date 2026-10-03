@echo off
setlocal
cd /d "%~dp0\..\backend"
if not exist .venv\Scripts\python.exe (
  echo Run scripts\setup-windows.bat first.
  exit /b 1
)
.venv\Scripts\python.exe validate_live.py
exit /b %errorlevel%
