@echo off
setlocal
cd /d "%~dp0"
echo [SignalLab] Preparing Python environment...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :error
echo [SignalLab] Installing frontend packages...
call npm --prefix frontend install
if errorlevel 1 goto :error
echo.
echo Setup complete. Run run.bat to start SignalLab.
exit /b 0
:error
echo.
echo Setup failed. Review the message above.
exit /b 1

