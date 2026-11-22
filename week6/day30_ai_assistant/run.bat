@echo off
setlocal
title Nova Agro-Vet AI Assistant
rem pushd (not cd) also works when the folder is on a network share (\\server\share).
pushd "%~dp0" || (echo [ERROR] Could not open the program folder. & pause & exit /b 1)

echo "%~dp0" | find /i "\AppData\Local\Temp\" >nul
if not errorlevel 1 (
    echo [SETUP ERROR] This is running from inside the ZIP file.
    echo Right-click the ZIP, choose "Extract All", open the extracted folder,
    echo and double-click run.bat there.
    goto :fail
)

rem ---- First run: create .env from the example and open it in Notepad ----
if not exist ".env" if not exist ".env.txt" if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example.
    echo Paste your Anthropic API key into the Notepad window that opens, save it,
    echo close Notepad, then double-click run.bat again.
    start "" notepad ".env"
    goto :fail
)

set "PYTHON_CMD="
if exist "venv\Scripts\python.exe" set "PYTHON_CMD=venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist "%USERPROFILE%\.venvs\kimnovix-env\Scripts\python.exe" set "PYTHON_CMD=%USERPROFILE%\.venvs\kimnovix-env\Scripts\python.exe"
if defined PYTHON_CMD goto :have_python

rem ---- First run on a client PC: find Python 3.10+ and build a private venv once ----
set "SYS_PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "SYS_PY=py -3"
if defined SYS_PY goto :make_venv
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "SYS_PY=python"
if not defined SYS_PY goto :no_python

:make_venv
echo First-time setup: installing components (needs internet, 1-3 minutes)...
%SYS_PY% -m venv venv
if errorlevel 1 goto :setup_failed
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 goto :setup_failed
set "PYTHON_CMD=venv\Scripts\python.exe"
echo Setup complete.
echo.

:have_python
"%PYTHON_CMD%" app.py --check-config
if errorlevel 1 (
    echo.
    echo Fix the issue shown above, save .env, and double-click run.bat again.
    goto :fail
)

"%PYTHON_CMD%" app.py
if errorlevel 1 goto :fail
popd
exit /b 0

:no_python
echo [SETUP ERROR] Python 3.10 or newer was not found on this computer.
echo Install Python 3.13 from https://www.python.org/downloads/windows/
echo and tick "Add python.exe to PATH" on the first installer screen.
echo Then double-click run.bat again.
goto :fail

:setup_failed
echo.
echo [SETUP ERROR] Installing components failed. Check the internet connection
echo and double-click run.bat again. The half-finished setup has been removed.
if exist "venv\Scripts\python.exe" rmdir /s /q "venv" >nul 2>&1
goto :fail

:fail
echo.
pause
popd
exit /b 1
