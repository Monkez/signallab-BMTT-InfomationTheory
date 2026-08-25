@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b 1
call build_native.bat
if errorlevel 1 exit /b 1
echo [SignalLab] Running backend tests...
".venv\Scripts\python.exe" -m pytest backend\tests
if errorlevel 1 exit /b 1
echo [SignalLab] Building production frontend...
call npm --prefix frontend run build
if errorlevel 1 exit /b 1
echo [SignalLab] Build completed successfully.
