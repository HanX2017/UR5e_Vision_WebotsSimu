@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto setup_needed
".venv\Scripts\python.exe" -B "portable_launcher.py" --test --headless --seed 1001 --run verification %*
set "PROJECT_EXIT=%errorlevel%"
pause
exit /b %PROJECT_EXIT%
:setup_needed
echo Please run Setup_Portable.cmd first.
pause
exit /b 2
