@echo off

set REPO_URL=https://github.com/eresmio1906/telegram.git
set DEST_DIR=C:\Users
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

for %%A in ("%REPO_URL%") do set REPO_NAME=%%~nA

if exist "%DEST_DIR%\%REPO_NAME%" (
    echo Repo exists, pulling latest...
    cd /d "%DEST_DIR%\%REPO_NAME%"
    git pull
) else (
    echo Cloning repo...
    git clone %REPO_URL% "%DEST_DIR%\%REPO_NAME%"
)

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
