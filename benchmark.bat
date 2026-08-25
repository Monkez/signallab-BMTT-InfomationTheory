@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b 1
if not exist "backend\app\_native_core*.pyd" call build_native.bat
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m tools.benchmark_native %*
