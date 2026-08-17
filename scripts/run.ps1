$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

Write-Host '[SignalLab] Starting API on http://127.0.0.1:8000' -ForegroundColor Cyan
$ApiJob = Start-Job -ScriptBlock {
    param($Root, $Python)
    Set-Location -LiteralPath $Root
    & $Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
} -ArgumentList $ProjectRoot, $PythonExe

Write-Host '[SignalLab] Starting studio on http://127.0.0.1:5173' -ForegroundColor Magenta
$UiJob = Start-Job -ScriptBlock {
    param($Root)
    Set-Location -LiteralPath (Join-Path $Root 'frontend')
    & npm run dev
} -ArgumentList $ProjectRoot

try {
    Start-Sleep -Seconds 2
    Start-Process 'http://127.0.0.1:5173'
    Write-Host 'SignalLab is ready. Press Ctrl+C to stop both services.' -ForegroundColor Green
    while ($true) {
        # Uvicorn writes normal startup/access logs to stderr. PowerShell remotes
        # those records as non-terminating errors, so they must not stop dev mode.
        Receive-Job -Job $ApiJob, $UiJob -ErrorAction SilentlyContinue
        if ($ApiJob.State -in @('Failed', 'Stopped', 'Completed') -or $UiJob.State -in @('Failed', 'Stopped', 'Completed')) {
            Write-Host 'A SignalLab service stopped unexpectedly.' -ForegroundColor Red
            Receive-Job -Job $ApiJob, $UiJob -ErrorAction SilentlyContinue
            break
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Stop-Job -Job $ApiJob, $UiJob -ErrorAction SilentlyContinue
    Remove-Job -Job $ApiJob, $UiJob -Force -ErrorAction SilentlyContinue
    Write-Host 'SignalLab stopped.'
}
