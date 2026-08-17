@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo SignalLab is not set up yet. Running setup first...
  call setup.bat
  if errorlevel 1 exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1"

