@echo off
REM PCS Check — Streamlit app launcher (Windows)
REM Double-click this file, or run from Command Prompt.
setlocal
cd /d "%~dp0"

echo.
echo === PCS Check (Streamlit) ===
echo Folder: %CD%
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set PY=py
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set PY=python
  ) else (
    echo Python not found. Install from https://www.python.org/downloads/
    echo Tick "Add python.exe to PATH", then reopen this window.
    echo Do NOT use the Microsoft Store python stub under WindowsApps.
    pause
    exit /b 1
  )
)

if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found.
  echo Make sure this .bat sits in the pcs-check project folder.
  pause
  exit /b 1
)

if not exist "pcs_verify\__init__.py" (
  echo ERROR: pcs_verify package missing.
  echo You need the full project folder, not just one file.
  pause
  exit /b 1
)

echo Installing dependencies (first run may take a minute)...
%PY% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo pip install failed.
  pause
  exit /b 1
)

echo.
echo Starting app at http://127.0.0.1:43123
echo Leave this window open. Press Ctrl+C to stop.
echo.
%PY% -m streamlit run app.py --server.port 43123 --server.headless true
pause
