@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title Flame Fighter - GitHub Direct Push

echo.
echo =============================================================
echo       FLAME FIGHTER - DIRECT GITHUB PUSH
echo =============================================================
echo.
echo [*] Target Repository:
echo     https://github.com/adammohammedahmedtawfik/Flame_Fighter_V1.git
echo.

cd /d "%~dp0"

echo [1/3] Checking Git Status...
git status --short

echo.
echo [2/3] Setting branch to main...
git branch -M main

echo.
echo [3/3] Pushing to https://github.com/adammohammedahmedtawfik/Flame_Fighter_V1.git ...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =============================================================
    echo   [SUCCESS] تم رفع المشروع بنجاح إلى المستودع الجديد!
    echo =============================================================
) else (
    echo.
    echo =============================================================
    echo [NOTICE] إذا طُلب منك تسجيل الدخول، سجّل عبر المتصفح.
    echo أو إذا كان لديك Personal Access Token (PAT):
    echo =============================================================
    set /p TOKEN="أدخل GitHub Token (أو اضغط ENTER للمحاولة مرة أخرى): "
    if not "!TOKEN!"=="" (
        git remote set-url origin https://!TOKEN!@github.com/adammohammedahmedtawfik/Flame_Fighter_V1.git
        git push -u origin main
    )
)

echo.
pause
