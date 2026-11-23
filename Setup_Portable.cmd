@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Looking for Python 3.11...
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
if errorlevel 1 goto use_python
set "PYTHON_BOOTSTRAP=py -3.11"
goto create_env

:use_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
if errorlevel 1 goto wrong_python
set "PYTHON_BOOTSTRAP=python"

:create_env
if not exist ".venv\Scripts\python.exe" (
  echo [2/3] Creating the local virtual environment...
  %PYTHON_BOOTSTRAP% -m venv ".venv"
  if errorlevel 1 goto failed
) else (
  echo [2/3] Reusing the existing local virtual environment.
)

echo [3/3] Installing pinned dependencies...
if not exist "Cache\pip" mkdir "Cache\pip"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --cache-dir "Cache\pip" -r "requirements.txt"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -B "portable_launcher.py" --diagnose
if errorlevel 1 goto failed
echo.
echo Setup complete. You can now run Start_Sorting.cmd.
pause
exit /b 0

:no_python
echo ERROR: Python 3.11 was not found. Install Python 3.11 x64, then run this file again.
goto failed

:wrong_python
echo ERROR: The Python command is not Python 3.11. Install Python 3.11 x64 or enable the py launcher.

:failed
echo.
echo Setup failed. See README.md for requirements and troubleshooting.
pause
exit /b 1
