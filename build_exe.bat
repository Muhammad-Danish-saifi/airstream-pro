@echo off
title Building AirStream Pro Executable (.exe)
echo ======================================================
echo    AirStream Pro - PyInstaller Windows Packager
echo ======================================================
echo.
echo Step 1: Checking icons...
if not exist "app_icon.ico" (
    echo Generating app_icon.ico...
    python create_icon.py
)
echo.
echo Step 2: Running PyInstaller build...
python -m PyInstaller --clean AirStreamPro.spec
echo.
if exist "dist\AirStreamPro.exe" (
    echo ======================================================
    echo  SUCCESS! Standalone Executable created at:
    echo  dist\AirStreamPro.exe
    echo ======================================================
) else (
    echo [ERROR] Build failed. Please check output above.
)
pause
