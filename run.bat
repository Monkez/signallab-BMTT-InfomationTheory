@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\SignalLab\SignalLab.exe" (
  echo SignalLab desktop has not been built. Building it now...
  call build_app.bat
  if errorlevel 1 exit /b 1
)
start "" "%~dp0dist\SignalLab\SignalLab.exe"

