@echo off
cd /d "%~dp0"
set VENV_PATH=venv\Scripts\pythonw.exe

if exist %VENV_PATH% (
    start "" %VENV_PATH% main.py
) else (
    start "" pythonw.exe main.py
)
exit
