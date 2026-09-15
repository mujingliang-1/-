@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

py -3 --version >nul 2>&1
if not errorlevel 1 (
  set "PY=py -3"
) else (
  python --version >nul 2>&1
  if errorlevel 1 (
    echo.
    echo 还没装 Python。浏览器会打开下载页：安装时务必勾选 Add python.exe to PATH
    echo 装完关掉本窗口，再双击 start.bat
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set "PY=python"
)

if not exist ".env" (
  echo.
  echo 把 DeepSeek API Key 粘贴后按回车（以 sk- 开头）
  set /p KEY=
  if "!KEY!"=="" (
    echo 没有填写 Key，已退出。
    pause
    exit /b 1
  )
  (
    echo VISION_API_KEY=!KEY!
    echo VISION_BASE_URL=https://api.deepseek.com
    echo VISION_MODEL=deepseek-flash
    echo SKIP_LOCAL_VLM=1
  ) > .env
  echo 已保存 Key，下次不用再填。
)

if not exist ".venv\Scripts\python.exe" (
  echo 正在创建运行环境...
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
echo 正在安装依赖，第一次需要一两分钟，请等...
python -m pip install -U pip
python -m pip install -r display_inspector\requirements.txt
set "PYTHONPATH=%cd%"
set "SKIP_LOCAL_VLM=1"

echo.
echo 本机页面： http://127.0.0.1:8080
echo 这个黑窗口不要关。若要给别人打开，再双击「给别人打开.bat」
echo.
start "" cmd /c "timeout /t 6 /nobreak >nul && start http://127.0.0.1:8080"
python -m display_inspector
pause
