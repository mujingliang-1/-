@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo 先确认 start.bat 已经在跑，浏览器能打开 http://127.0.0.1:8080
echo 接下来会申请一条临时链接。这个窗口不要关，电脑不要休眠。
echo 关机或关窗口后，链接立刻失效。
echo.

where cpolar >nul 2>&1
if not errorlevel 1 (
  echo 使用 cpolar ...
  cpolar http 8080
  pause
  exit /b 0
)

where ssh >nul 2>&1
if not errorlevel 1 (
  echo 使用临时隧道，出现 https:// 开头的地址后复制发给别人。
  echo 若询问 yes/no，输入 yes 回车。
  echo.
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ServerAliveInterval=30 -R 80:localhost:8080 nokey@localhost.run
  pause
  exit /b 0
)

echo 本机还没有隧道工具。任选一个：
echo.
echo 【更稳，国内推荐】下载 cpolar：
echo https://www.cpolar.com/
echo 安装后打开新的命令窗口，输入：  cpolar http 8080
echo 把显示的 https://xxxx.cpolar.cn 发给别人。
echo.
echo 【不装软件】Windows 设置 → 可选功能 → 添加 OpenSSH 客户端
echo 然后重新双击本文件。
echo.
start https://www.cpolar.com/
pause
