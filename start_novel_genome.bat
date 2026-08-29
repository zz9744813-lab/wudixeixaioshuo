@echo off
rem Novel Genome - one-click launcher (dashboard + server)
rem Dashboard: http://127.0.0.1:8123/   API docs: /docs
title Novel Genome
cd /d "F:\6\Documents\novel-genome"

netstat -ano | findstr ":8123" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [Novel Genome] server already running - opening dashboard...
    start "" "http://127.0.0.1:8123/"
    timeout /t 2 >nul
    exit /b 0
)

echo [Novel Genome] starting server on http://127.0.0.1:8123/ ...
start "Novel Genome server" /min ".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8123

rem wait for the port, then open the dashboard
set /a tries=0
:waitport
timeout /t 1 >nul
netstat -ano | findstr ":8123" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 goto ready
set /a tries+=1
if %tries% lss 15 goto waitport
echo [Novel Genome] server did not come up - check this folder's logs.
pause
exit /b 1

:ready
start "" "http://127.0.0.1:8123/"
echo [Novel Genome] dashboard opened. The server runs minimized in its own
echo window ("Novel Genome server") - close that window to stop it.
timeout /t 4 >nul
exit /b 0
