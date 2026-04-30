@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    py -m venv .venv
    if errorlevel 1 ( echo [ERROR] venv creation failed & pause & exit /b 1 )
    call .venv\Scripts\activate.bat
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

python -m app.main
if errorlevel 1 ( pause )
endlocal
