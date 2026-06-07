@echo off
chcp 65001 >nul
title Dex AI Assistant v3+
setlocal enabledelayedexpansion

echo === Dex AI Assistant v3+ Launcher ===
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Install Python 3.12+ from https://python.org
    pause
    exit /b 1
)

python --version

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    set PIP=.venv\Scripts\pip.exe
    echo [OK] Virtual env found
) else (
    set PYTHON=python
    set PIP=pip
    echo [INFO] Using system Python
)

echo.
echo --- Library Version Check ---

%PIP% list --format=columns 2>nul | findstr /i "speechrecognition pyttsx3 pyaudio edge-tts chromadb opencv-python pillow torch psutil pyyaml gitpython textual ollama requests pytest" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Some dependencies missing, installing...
    %PIP% install --upgrade pip >nul 2>&1
    %PIP% install -r requirements.txt
    %PIP% install ollama python-dotenv requests mediapipe 2>nul
) else (
    echo All core libraries found.
    %PIP% list --format=columns 2>nul | findstr /i "speechrecognition pyttsx3 pyaudio edge-tts chromadb sentence-transformers opencv-python pillow pytesseract pynput transformers torch psutil pyyaml gitpython textual ollama requests pytest"
)

echo.
echo --- Ollama Status ---
python -c "import urllib.request; urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)" 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Ollama is running
) else (
    echo [WARN] Ollama not detected. Start ollama or set DEX_SKIP_LLM=1
)

echo.
echo --- Creating data directories ---
if not exist "data" mkdir data
for %%d in (memory feedback logs plugins rules backup agents data research predictor twin debates wearable docs meta_learning ethics jit_agents self_expansion dexos mesh psych counsel temporal intent prime evolution) do (
    if not exist "data\%%d" mkdir "data\%%d" 2>nul
)

echo.
echo --- Starting Dex ---
echo.

python main.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Dex exited with code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo [OK] Dex finished
