@echo off
setlocal
cd /d "%~dp0\.."
echo [1/3] Preparing backend dependencies...
if not exist backend\.venv py -3 -m venv backend\.venv
if errorlevel 1 exit /b 1
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
if not exist backend\.env copy backend\.env.example backend\.env >nul

echo [2/3] Installing locked frontend dependencies...
pushd frontend
if not exist .env.local copy .env.local.example .env.local >nul
call npm ci
if errorlevel 1 (popd & exit /b 1)
popd

echo [3/3] Dependencies ready. No database was created or reset.
echo Copy your working private .env files into this NEW folder if needed.
echo Then, from backend, run .venv\Scripts\python.exe adopt_baseline.py
 echo This compares the existing schema without changing customer data.
echo Follow README.md for reviewed baseline adoption and additive Alembic migrations.
echo Use scripts\start-acceptance-windows.bat after schema_check.py passes.
endlocal
