@echo off
cd /d "%~dp0"

echo [1/3] 停止旧进程...
taskkill /f /im CodeFlow-Desktop.exe
timeout /t 2 /nobreak

echo [2/3] 清除构建缓存...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [3/3] 打包...
py -3.12 -m PyInstaller build.spec --noconfirm --clean
if errorlevel 1 (
    echo 打包失败！
    exit /b 1
)

echo.
echo 完成: dist\CodeFlow-Desktop.exe
