@echo off
cd /d "%~dp0"
echo Starting SOUL from: %cd%
echo.
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv\Scripts\python.exe was not found.
  pause
  exit /b 1
)
echo Starting the SOUL server. Keep this window open.
start "" /b cmd /c "timeout /t 8 /nobreak >nul & start chrome --app=http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
echo.
echo SOUL stopped. Read the lines above for the reason.
pause