@echo off
setlocal
cd /d "%~dp0"
title Flame Fighter Tactical Station

echo.
echo =============================================================
echo       FLAME FIGHTER - TACTICAL DEFENSE SYSTEM
echo =============================================================
echo.
echo [*] Freeing port 5000 and clearing previous sessions...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul

echo [*] Scanning for cameras (Priority: USB External Camera)...
echo [*] Launching Dashboard at http://localhost:5000...
echo.

start /b cmd /c "ping 127.0.0.1 -n 3 > nul && start http://localhost:5000"

python System_IP.py %*

echo.
echo [!] System stopped. Press any key to close.
pause > nul
