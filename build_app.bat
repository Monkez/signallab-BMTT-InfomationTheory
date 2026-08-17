@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b 1

echo [SignalLab] Installing desktop packager...
".venv\Scripts\python.exe" -m pip install -r backend\requirements-desktop.txt
if errorlevel 1 goto :error

echo [SignalLab] Building production frontend...
call npm --prefix frontend run build
if errorlevel 1 goto :error

echo [SignalLab] Running backend tests...
".venv\Scripts\python.exe" -m pytest backend\tests
if errorlevel 1 goto :error

echo [SignalLab] Creating application icon...
if not exist "assets" mkdir assets
".venv\Scripts\python.exe" tools\create_icon.py
if errorlevel 1 goto :error

echo [SignalLab] Packaging Windows desktop application...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean SignalLab.spec
if errorlevel 1 goto :error

echo.
echo Desktop build complete:
echo   %~dp0dist\SignalLab\SignalLab.exe
exit /b 0

:error
echo.
echo Desktop build failed. Review the message above.
exit /b 1
