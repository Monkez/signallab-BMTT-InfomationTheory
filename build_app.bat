@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b 1

call build_native.bat
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
echo [SignalLab] Creating instant native launcher...
set "SIGNALLAB_DIR=%~dp0dist\SignalLab"
for %%I in ("%SIGNALLAB_RELEASE%") do set "SIGNALLAB_DIR=%%~dpI"
if exist "%SIGNALLAB_DIR%\SignalLab.exe" move /Y "%SIGNALLAB_DIR%\SignalLab.exe" "%SIGNALLAB_DIR%\SignalLabCore.exe" >nul
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /out:"%SIGNALLAB_DIR%\SignalLabLauncher.exe" /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll tools\SignalLabLauncher.cs
if errorlevel 1 goto :error
move /Y "%SIGNALLAB_DIR%\SignalLabLauncher.exe" "%SIGNALLAB_DIR%\SignalLab.exe" >nul
echo   %SIGNALLAB_DIR%\SignalLab.exe (instant native launcher)
echo   %SIGNALLAB_DIR%\SignalLabCore.exe (Python runtime)
exit /b 0

:error
echo.
echo Desktop build failed. Review the message above.
exit /b 1
