@echo off
setlocal
cd /d "%~dp0\.."
if not exist backend\.venv\Scripts\python.exe (
  echo Run scripts\setup-windows.bat first.
  exit /b 1
)
start "VTAB Backend" /D "%CD%\backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
start "VTAB Frontend" /D "%CD%\frontend" cmd /k "npm run dev -- --port 3000"
echo Frontend: http://localhost:3000
 echo API docs: http://localhost:8001/docs
endlocal
