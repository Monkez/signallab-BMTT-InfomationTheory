@echo off
setlocal
cd /d "%~dp0"

rem Pick the newest packaged release. dist-update is used when Windows keeps the
rem canonical EXE locked while a freshly built SignalLab instance is still open.
set "SIGNALLAB_EXE="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$paths = @('dist\SignalLab\SignalLabLauncher.exe', 'dist-update\SignalLab\SignalLabLauncher.exe', 'dist\SignalLab-systematic\SignalLabLauncher.exe'); $candidates = Get-Item -LiteralPath $paths -ErrorAction SilentlyContinue; $latest = $candidates | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1; if ($latest) { $latest.FullName }"`) do set "SIGNALLAB_EXE=%%I"

if not defined SIGNALLAB_EXE (
  echo SignalLab desktop has not been built. Building it now...
  call build_app.bat
  if errorlevel 1 exit /b 1
  set "SIGNALLAB_EXE=%~dp0dist\SignalLab\SignalLabLauncher.exe"
)

if /i "%~1"=="--print-path" (
  echo %SIGNALLAB_EXE%
  exit /b 0
)

start "" "%SIGNALLAB_EXE%"
