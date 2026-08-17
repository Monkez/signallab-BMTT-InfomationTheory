@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pytest backend\tests
if errorlevel 1 exit /b 1
call npm --prefix frontend run build

