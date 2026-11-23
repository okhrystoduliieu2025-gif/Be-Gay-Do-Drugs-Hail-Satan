@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo The game could not start. Check the error above.
    pause
)
