@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" call setup.bat --skip-native
if errorlevel 1 goto :error

echo [SignalLab] Installing native build dependencies...
".venv\Scripts\python.exe" -m pip install -r backend\requirements-native.txt
if errorlevel 1 goto :error

set "PYBIND11_CMAKE=%CD%\.venv\Lib\site-packages\pybind11\share\cmake\pybind11"
set "TBB_CMAKE=%CD%\.venv\Library\lib\cmake\tbb"
set "PREFIX_PATH=%PYBIND11_CMAKE%;%TBB_CMAKE%"

echo [SignalLab] Configuring native CPU engine...
".venv\Scripts\cmake.exe" -S native -B build-native -G "Visual Studio 17 2022" -A x64 -DPython_EXECUTABLE="%CD%\.venv\Scripts\python.exe" -DCMAKE_PREFIX_PATH="%PREFIX_PATH%"
if errorlevel 1 goto :error

echo [SignalLab] Building native CPU engine...
".venv\Scripts\cmake.exe" --build build-native --config Release --parallel
if errorlevel 1 goto :error

".venv\Scripts\python.exe" -c "from backend.app.native_engine import native_status; status=native_status(); print('[SignalLab] Native engine:', status); raise SystemExit(0 if status.get('available') else 1)"
if errorlevel 1 goto :error

echo [SignalLab] Native CPU engine is ready.
exit /b 0

:error
echo.
echo Native build failed. Install Visual Studio 2022 C++ Build Tools and review the message above.
exit /b 1
