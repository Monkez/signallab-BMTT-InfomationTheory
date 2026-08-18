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
set "SIGNALLAB_RELEASE=%~dp0dist\SignalLab\SignalLab.exe"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean SignalLab.spec
if errorlevel 1 (
  echo [SignalLab] The standard release may be locked. Building a side-by-side update...
  ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath dist-update --workpath build-update SignalLab.spec
  if errorlevel 1 goto :error
  set "SIGNALLAB_RELEASE=%~dp0dist-update\SignalLab\SignalLab.exe"
)

echo.
echo Desktop build complete:
echo   %SIGNALLAB_RELEASE%
exit /b 0

:error
echo.
echo Desktop build failed. Review the message above.
exit /b 1
