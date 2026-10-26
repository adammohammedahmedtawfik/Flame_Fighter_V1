@echo off
chcp 65001 > nul
title Flame Fighter - GitHub Push Assistant
echo ========================================================
echo       Flame Fighter - Standalone GitHub Push
echo ========================================================
echo.

where gh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [*] Checking GitHub CLI authentication...
    gh auth status >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Authenticated via GitHub CLI!
        echo.
        set /p REPO_NAME="Enter new repo name (press ENTER for 'Flame-Fighter-Live'): "
        if "%REPO_NAME%"=="" set REPO_NAME=Flame-Fighter-Live
        echo [*] Creating GitHub repository %REPO_NAME%...
        gh repo create %REPO_NAME% --public --source=. --remote=origin --push
        if %ERRORLEVEL% EQU 0 (
            echo.
            echo [SUCCESS] Repository created and pushed successfully!
            pause
            exit /b 0
        )
    )
)

echo [*] If you already created an empty repo on GitHub:
set /p REPO_URL="Enter your GitHub Repository URL (e.g. https://github.com/USERNAME/REPO.git): "
if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided.
    pause
    exit /b 1
)

echo.
echo [1/3] Setting remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo [2/3] Setting branch to main...
git branch -M main

echo [3/3] Pushing to GitHub...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo [SUCCESS] Standalone project successfully pushed to GitHub!
    echo ========================================================
) else (
    echo.
    echo [NOTICE] Push failed or authentication required.
    echo Check your credentials or GitHub Personal Access Token.
)

pause
