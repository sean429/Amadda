@echo off
setlocal

if not exist ".venv" (
    py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m app.main

endlocal
