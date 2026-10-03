@echo off
setlocal
cd /d "%~dp0\.."
if not exist backend\.venv\Scripts\python.exe (
  echo Run scripts\setup-windows.bat first.
  exit /b 1
)
powershell -NoProfile -Command "$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 8001,3000 }; if ($listeners) { $listeners | Select-Object LocalPort,OwningProcess | Format-Table; exit 1 }"
if errorlevel 1 (
  echo Ports 8001 or 3000 are occupied. Stop the old application terminals before retrying.
  exit /b 1
)
set DEMO_MODE=true
set SCHEDULER_ENABLED=false
start "VTAB Acceptance Backend - DEMO" /D "%CD%\backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
start "VTAB Acceptance Frontend" /D "%CD%\frontend" cmd /k "npm run dev -- --port 3000"
echo Open http://localhost:3000/login and confirm the DEMO MODE banner.
echo Microsoft OTP delivery and inbox reads remain real when configured.
echo Customer sends are simulated. Scheduled jobs are disabled.
endlocal
