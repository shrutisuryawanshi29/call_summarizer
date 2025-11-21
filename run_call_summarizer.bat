@echo off
REM Batch file to run Call Summarizer and clean up on exit

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Set Python path
set PYTHON_PATH=E:\conda_envs\meetingenv\python.exe

REM Check if Python exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python not found at %PYTHON_PATH%
    echo Please update PYTHON_PATH in this batch file.
    pause
    exit /b 1
)

echo Starting Call Summarizer...
echo.

REM Start the application and wait for it to close
"%PYTHON_PATH%" app.py

REM After the app closes, clean up any remaining processes
echo.
echo Application closed. Cleaning up processes...

REM Use PowerShell to find and kill any Python processes related to the app
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*meetingenv*' }; ^
     foreach ($proc in $processes) { ^
         try { ^
             $cmd = (Get-WmiObject Win32_Process -Filter \"ProcessId = $($proc.Id)\").CommandLine; ^
             if ($cmd -like '*app.py*' -or $cmd -like '*call_summarizer*') { ^
                 Write-Host \"Killing process $($proc.Id)\"; ^
                 Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; ^
             } ^
         } catch { } ^
     }"

echo Cleanup complete.
timeout /t 1 /nobreak >nul
exit
