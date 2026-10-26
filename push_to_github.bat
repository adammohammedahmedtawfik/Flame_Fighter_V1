@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title Flame Fighter - GitHub Auto Push Station

:: Ensure gh CLI is in PATH
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin;%PATH%"
)

echo.
echo =============================================================
echo       FLAME FIGHTER - GITHUB REPOSITORY DEPLOYMENT
echo =============================================================
echo.

where gh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    gh auth status >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        goto CREATE_WITH_GH
    ) else (
        echo [*] GitHub CLI (gh) مثبت ولكنه يحتاج تسجيل الدخول لأول مرة.
        echo.
        echo [1] تسجيل الدخول عبر المتصفح (Browser Login) وإنشاء الريبو آلياً
        echo [2] إدخال رابط ريبو فارغ قمت بإنشائه يدوياً (Repository URL)
        echo.
        set /p CHOICE="اختر رقم الخيار (1 أو 2): "
        if "!CHOICE!"=="1" (
            echo.
            echo [*] سيفتح المتصفح الآن لتسجيل الدخول السريع...
            gh auth login --web -h github.com -p https
            gh auth status >nul 2>nul
            if %ERRORLEVEL% EQU 0 (
                goto CREATE_WITH_GH
            )
        )
    )
)

:MANUAL_URL
echo.
echo [*] أدخل رابط المستودع من GitHub (مثال: https://github.com/USERNAME/Flame-Fighter-Live.git):
set /p REPO_URL="Repository URL: "
if "%REPO_URL%"=="" (
    echo [ERROR] لم تقم بإدخال رابط. تم إلغاء العملية.
    pause
    exit /b 1
)

echo.
echo [1/3] إعداد Remote Origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo [2/3] ضبط الفرع الرئيسي Main...
git branch -M main

echo [3/3] جاري رفع المشروع المستقل إلى GitHub...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =============================================================
    echo   [SUCCESS] تم رفع المشروع المستقل إلى GitHub بنجاح!
    echo =============================================================
) else (
    echo.
    echo [ERROR] فشل الرفع. تأكد من صحة الرابط والصلاحيات.
)
pause
exit /b 0

:CREATE_WITH_GH
echo.
echo [OK] تم التحقق من حساب GitHub بنجاح!
set /p REPO_NAME="أدخل اسم المستودع الجديد (اضغط ENTER للافتراضي: Flame-Fighter-Live): "
if "%REPO_NAME%"=="" set REPO_NAME=Flame-Fighter-Live

echo.
echo [*] جاري إنشاء المستودع %REPO_NAME% على GitHub ورفع المشروع كاملاً...
gh repo create %REPO_NAME% --public --source=. --remote=origin --push

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =============================================================
    echo   [SUCCESS] تم إنشاء المستودع ورفع الملفات بالكامل إلى GitHub!
    echo =============================================================
) else (
    echo.
    echo [*] في حال كان المستودع موجوداً مسبقاً، جاري الرفع المباشر إليه...
    git push -u origin main
)
pause
exit /b 0
