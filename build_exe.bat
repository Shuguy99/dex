@echo off
chcp 65001 >nul
title Dex EXE Builder
setlocal enabledelayedexpansion

echo ======================================
echo   Dex AI Assistant - EXE Builder
echo ======================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

if exist "dist\Dex" rmdir /s /q "dist\Dex" 2>nul
if exist "dist\Dex.exe" del "dist\Dex.exe" 2>nul
if exist "build\dex" rmdir /s /q "build\dex" 2>nul
if exist "dex.spec" del "dex.spec" 2>nul

echo.
echo [BUILD] Creating Dex executable...
echo.

python -m PyInstaller ^
    --name "Dex" ^
    --onefile ^
    --windowed ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --add-data "config.py;." ^
    --add-data "watchdog;watchdog" ^
    --add-data "memory;memory" ^
    --add-data "learning;learning" ^
    --add-data "sensors;sensors" ^
    --add-data "multiagent;multiagent" ^
    --add-data "ethics;ethics" ^
    --add-data "generative;generative" ^
    --add-data "dexos;dexos" ^
    --add-data "mesh;mesh" ^
    --add-data "psych;psych" ^
    --add-data "evolution;evolution" ^
    --add-data "counsel;counsel" ^
    --add-data "temporal;temporal" ^
    --add-data "intent;intent" ^
    --add-data "prime;prime" ^
    --add-data "testing;testing" ^
    --hidden-import "PyQt5" ^
    --hidden-import "PyQt5.QtCore" ^
    --hidden-import "PyQt5.QtGui" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --hidden-import "chromadb" ^
    --hidden-import "sentence_transformers" ^
    --hidden-import "ollama" ^
    --hidden-import "torch" ^
    --hidden-import "PIL" ^
    --hidden-import "pynput" ^
    --hidden-import "psutil" ^
    --hidden-import "requests" ^
    --hidden-import "yaml" ^
    --hidden-import "git" ^
    --hidden-import "uvicorn" ^
    --hidden-import "fastapi" ^
    --hidden-import "APScheduler" ^
    --hidden-import "queue" ^
    --hidden-import "concurrent" ^
    --hidden-import "http" ^
    --hidden-import "json" ^
    --hidden-import "asyncio" ^
    --hidden-import "io" ^
    --hidden-import "threading" ^
    --collect-all "chromadb" ^
    --collect-all "sentence_transformers" ^
    --collect-all "PyQt5" ^
    --exclude-module "matplotlib" ^
    --exclude-module "notebook" ^
    --exclude-module "test" ^
    --exclude-module "tensorflow" ^
    --exclude-module "pandas" ^
    run_exe.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed!
    echo.
    echo Common fixes:
    echo 1. pip install --upgrade pyinstaller
    echo 2. Try: python -m PyInstaller --onedir run_exe.py
    echo 3. Check that all hidden imports are available
    pause
    exit /b %ERRORLEVEL%
)

copy /Y launch.bat "dist\" 2>nul

echo.
echo ======================================
echo   Build complete!
echo.
echo   EXE: dist\Dex.exe
echo.
echo   Requirements:
echo   - Ollama (https://ollama.com)
echo   - Model: ollama pull qwen2.5:14b
echo ======================================
echo.

pause
