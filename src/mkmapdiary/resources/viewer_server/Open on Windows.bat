@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=
for %%P in (51342 51343 51344 51345 51346) do (
    if not defined PORT (
        powershell -NoProfile -Command "try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', %%P); $c.Close(); exit 1 } catch { exit 0 }" >nul 2>&1
        if !errorlevel! equ 0 (
            set PORT=%%P
        )
    )
)

if not defined PORT (
    echo Could not find a free port among: 51342 51343 51344 51345 51346
    echo Close whatever is using one of these ports and try again.
    pause
    exit /b 1
)

start "" /b ".\_site\.server\miniserve-windows.exe" -i 127.0.0.1 -p !PORT! --index index.html --disable-indexing .\_site

powershell -NoProfile -Command "for ($i=0; $i -lt 50; $i++) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', !PORT!); $c.Close(); exit 0 } catch { Start-Sleep -Milliseconds 100 } }"

set URL=http://127.0.0.1:!PORT!/
start "" "!URL!"

echo Your travel journal is running at !URL!
echo Close this window to stop viewing.
pause >nul
rem Kills every running miniserve-windows.exe system-wide, not just this
rem journal's instance -- a clean PID-scoped kill is awkward in plain batch
rem (no portable job-object/process-tree primitive without extra tooling).
rem Accepted as a known limitation rather than over-engineering it here.
taskkill /f /im miniserve-windows.exe >nul 2>&1
