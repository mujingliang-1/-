@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
python -m pip install -r display_inspector\requirements.txt
set "PYTHONPATH=%cd%"
set "SKIP_LOCAL_VLM=1"
echo.
echo Starting display inspector on http://0.0.0.0:8080
echo Leave this window open. Disconnect RDP; do not log off.
echo.
python -m display_inspector
