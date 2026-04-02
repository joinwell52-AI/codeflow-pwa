@echo off
chcp 65001 > nul
title BridgeFlow 安装启动

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║          BridgeFlow  一键安装启动                ║
echo  ║     手机主控台 + PC 执行机 + 文件协作桥接         ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM ── 切换到脚本所在目录（即项目目录）───────────────────────────────────────
cd /d "%~dp0"

REM ── 检查 Python ───────────────────────────────────────────────────────────
echo  [1/3] 检查 Python 环境...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ✗ 未检测到 Python！
    echo.
    echo  请先安装 Python 3.10 或以上版本：
    echo    下载地址：https://www.python.org/downloads/
    echo    安装时必须勾选：Add Python to PATH
    echo.
    echo  安装完成后，重新双击本脚本即可。
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  ✓ Python %PYVER%

REM ── 安装 / 升级 bridgeflow ────────────────────────────────────────────────
echo.
echo  [2/3] 安装 BridgeFlow（首次约需 10-30 秒）...
pip install --upgrade bridgeflow -q
if %errorlevel% neq 0 (
    echo.
    echo  ✗ 安装失败！可能原因：
    echo    - 网络不通（检查代理或 VPN）
    echo    - pip 版本过旧（运行：python -m pip install --upgrade pip）
    echo.
    pause
    exit /b 1
)
echo  ✓ BridgeFlow 安装完成

REM ── 启动 BridgeFlow（自动初始化 + 打开浏览器仪表盘）─────────────────────
echo.
echo  [3/3] 启动 BridgeFlow...
echo.
bridgeflow run

REM ── 异常退出时暂停，方便查看错误 ────────────────────────────────────────
if %errorlevel% neq 0 (
    echo.
    echo  ✗ 启动失败，错误代码：%errorlevel%
    echo  请截图以上内容发给技术支持。
    echo.
    pause
)
