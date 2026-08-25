@echo off
setlocal
cd /d "%~dp0"

echo [SignalLab] BPSK/Hamming performance gate...
call benchmark.bat --bits 4096 --frames 1000 --repeats 3 --modulation bpsk --coding hamming74 --min-speedup 2
if errorlevel 1 goto :error

echo [SignalLab] QPSK/Hamming performance gate...
call benchmark.bat --bits 4096 --frames 1000 --repeats 3 --modulation qpsk --coding hamming74 --min-speedup 2
if errorlevel 1 goto :error

echo [SignalLab] 16-QAM performance gate...
call benchmark.bat --bits 4096 --frames 1000 --repeats 3 --modulation qam16 --coding none --min-speedup 2
if errorlevel 1 goto :error

echo [SignalLab] All native performance gates passed.

echo [SignalLab] Python Custom Block performance gate...
call benchmark_python.bat --bits 65536 --frames 1024 --repeats 2 --workload fft --min-speedup 1.2
if errorlevel 1 goto :error

echo [SignalLab] All native and Python performance gates passed.
exit /b 0

:error
echo [SignalLab] Native performance regression detected.
exit /b 1
