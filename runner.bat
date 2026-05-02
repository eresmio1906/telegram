@echo off
git pull
:: Always run from script directory
cd /d "%~dp0"

:: === CONFIG ===
set VENV_DIR=venv
set PY_FILE1=backend.py
set PY_FILE2=bot.py

:: === CHECK / CREATE VENV ===
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv %VENV_DIR%
)

:: === ACTIVATE VENV ===
call "%VENV_DIR%\Scripts\activate.bat"

:: === UPGRADE PIP ===
python -m pip install --upgrade pip

:: === INSTALL REQUIREMENTS ===
if exist requirements.txt (
    pip install -r requirements.txt
)

:: === RUN PYTHON FILES ===

:: Run backend in background (no window)
start "" /b python %PY_FILE1%

:: Wait for backend to start
timeout /t 5 /nobreak >nul

:: Run bot (main process)
python %PY_FILE2%
