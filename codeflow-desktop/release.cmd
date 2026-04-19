@echo off
chcp 65001 >nul
:: ══════════════════════════════════════════════════════════════
::  CodeFlow Desktop 一键发版脚本（一条龙）
::
::  用法：release.cmd <版本号>
::  示例：release.cmd 2.10.0
::
::  执行步骤：
::    [1/8] 前置检查（VERSION / CHANGELOG / gh / gitee token）
::    [2/8] 打包 EXE（PyInstaller）
::    [3/8] 提取版本说明
::    [4/8] git commit + tag
::    [5/8] git push origin（GitHub 主仓）
::    [6/8] GitHub Release + 上传 EXE
::    [7/8] Gitee 代码同步 + Release + 上传 EXE
::    [8/8] backup 仓库同步
::
::  前置条件：
::    - gh CLI 已安装并登录（gh auth login）
::    - .gitee_token 文件存在（或 GITEE_TOKEN 环境变量）
::    - git remote: origin / gitee / backup 已配置
::    - promotion/index.html 必须在仓库根目录（旧链接保活）
::    - 使用 D:\Git\cmd\git.exe（系统 git），避免 Cursor 注入 --trailer 报错
:: ══════════════════════════════════════════════════════════════

cd /d "%~dp0"
setlocal enabledelayedexpansion

:: ── 参数校验 ─────────────────────────────────────────────────
if "%~1"=="" (
    echo.
    echo  用法: release.cmd ^<版本号^>
    echo  示例: release.cmd 2.10.0
    echo.
    exit /b 1
)

set VERSION=%~1
set TAG=v%VERSION%
set REPO=joinwell52-AI/codeflow-pwa
set EXE=dist\CodeFlow-Desktop.exe
set GH_CLI="C:\Program Files\GitHub CLI\gh.exe"

echo.
echo  ╔════════════════════════════════════════════════════╗
echo  ║  CodeFlow Desktop 发版  %TAG%                     ║
echo  ╚════════════════════════════════════════════════════╝
echo.

:: ══════════════════════════════════════════════════════════════
::  [1/8] 前置检查
:: ══════════════════════════════════════════════════════════════
echo [1/8] 前置检查...

:: 检查 main.py 中的版本号是否匹配
findstr /C:"VERSION = \"%VERSION%\"" main.py >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [错误] main.py 中的 VERSION 不是 "%VERSION%"
    echo  请先修改 main.py: VERSION = "%VERSION%"
    echo.
    exit /b 1
)
echo   √ main.py VERSION = "%VERSION%"

:: 检查 CHANGELOG
findstr /C:"## [%VERSION%]" ..\CHANGELOG.md >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [错误] CHANGELOG.md 中未找到 [%VERSION%] 条目！
    echo  请先补充：## [%VERSION%] - YYYY-MM-DD
    echo.
    exit /b 1
)
echo   √ CHANGELOG.md 包含 [%VERSION%]

:: 检查 gh CLI
if not exist %GH_CLI% (
    echo.
    echo  [错误] gh CLI 未找到: %GH_CLI%
    echo  请安装 GitHub CLI: https://cli.github.com/
    echo.
    exit /b 1
)
echo   √ gh CLI 已就绪

:: 检查 Gitee token
set GITEE_TOKEN_FILE=.gitee_token
if exist "%GITEE_TOKEN_FILE%" (
    set /p GITEE_TK=<"%GITEE_TOKEN_FILE%"
    echo   √ Gitee token 已就绪
) else (
    echo   ! Gitee token 未找到，Gitee 发布将跳过
    set GITEE_TK=
)

:: 检查推广页是否在仓库根目录（防止路径乱掉导致旧链接 404）
if not exist "..\promotion\index.html" (
    echo.
    echo  [错误] 推广页 promotion/index.html 不在仓库根目录！
    echo  旧链接 https://joinwell52-ai.github.io/codeflow-pwa/promotion/ 会 404
    echo  请确保 promotion/index.html 存在于仓库根目录后再发版。
    echo.
    exit /b 1
)
echo   √ promotion/index.html 路径正确

echo [1/8] 前置检查通过 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [2/8] 打包 EXE
:: ══════════════════════════════════════════════════════════════
echo [2/8] 打包 EXE...
call pack.cmd
if not exist "%EXE%" (
    echo  [错误] 打包失败，%EXE% 不存在！
    exit /b 1
)
for %%A in (%EXE%) do set EXE_SIZE=%%~zA
set /a EXE_MB=%EXE_SIZE% / 1048576
echo [2/8] 打包完成 ✓  (%EXE%, ~%EXE_MB% MB)
echo.

:: ══════════════════════════════════════════════════════════════
::  [3/8] 提取版本说明
:: ══════════════════════════════════════════════════════════════
echo [3/8] 提取版本说明...
py -3.12 -c "import re;ver='%VERSION%';text=open('../CHANGELOG.md',encoding='utf-8').read();m=re.search(r'## \['+re.escape(ver)+r'\].*?\n(.*?)(?=\n## \[|\Z)',text,re.DOTALL);body=m.group(1).strip() if m else '';header='## CodeFlow Desktop v%VERSION%\n\n> 下载 `CodeFlow-Desktop.exe`，双击运行，无需安装。\n> 已安装旧版会**自动检测并提示更新**。\n\n---\n\n';footer='\n\n---\n\n### 系统要求\n- Windows 10 / 11（64 位）\n- [Cursor IDE](https://www.cursor.com/)\n\n### 快速开始\n1. 双击 `CodeFlow-Desktop.exe` 启动\n2. 选择项目目录和团队模板\n3. 手机打开 [码流 PWA](https://joinwell52-ai.github.io/codeflow-pwa/) 扫码绑定\n\n### 完整更新日志\n见 [CHANGELOG.md](https://github.com/joinwell52-AI/codeflow-pwa/blob/main/CHANGELOG.md)\n';open('_release_notes.md','w',encoding='utf-8').write(header+body+footer);print('OK')"
if errorlevel 1 (
    echo  [错误] 提取版本说明失败
    exit /b 1
)
echo [3/8] 版本说明已生成 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [4/8] git commit + tag
:: ══════════════════════════════════════════════════════════════
echo [4/8] 提交代码并打 tag %TAG%...
cd /d "%~dp0\.."
D:\Git\cmd\git.exe add -A
D:\Git\cmd\git.exe commit -m "release: CodeFlow Desktop %TAG%"
if errorlevel 1 (
    echo   提示：无新改动需要提交，继续...
)
D:\Git\cmd\git.exe tag -a %TAG% -m "CodeFlow Desktop %TAG%" 2>nul
if errorlevel 1 (
    echo   提示：tag %TAG% 已存在，继续...
)
echo [4/8] 代码已提交 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [5/8] git push origin（GitHub 主仓）
:: ══════════════════════════════════════════════════════════════
echo [5/8] 推送到 GitHub (origin)...
D:\Git\cmd\git.exe push origin main
D:\Git\cmd\git.exe push origin %TAG%
if errorlevel 1 (
    echo  [警告] origin push 可能失败，请检查网络
)
echo [5/8] GitHub 推送完成 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [6/8] GitHub Release + 上传 EXE
:: ══════════════════════════════════════════════════════════════
echo [6/8] 发布 GitHub Release...
cd /d "%~dp0"

%GH_CLI% release create %TAG% ^
    "%EXE%#CodeFlow-Desktop.exe" ^
    --repo %REPO% ^
    --title "CodeFlow Desktop %TAG%" ^
    --notes-file "_release_notes.md"

if errorlevel 1 (
    echo.
    echo  [警告] GitHub Release 创建失败（可能已存在）
    echo  手动检查: https://github.com/%REPO%/releases/tag/%TAG%
)
echo [6/8] GitHub Release 完成 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [7/8] Gitee 同步 + Release
:: ══════════════════════════════════════════════════════════════
echo [7/8] 同步到 Gitee (国内镜像)...
cd /d "%~dp0\.."

:: 推送代码和 tag
D:\Git\cmd\git.exe push gitee main --tags 2>nul
if errorlevel 1 (
    echo   [警告] gitee push 部分失败（可能有已存在的 tag）
)

:: 创建 Gitee Release + 上传 EXE
cd /d "%~dp0"
if not "%GITEE_TK%"=="" (
    echo   创建 Gitee Release 并上传 EXE...
    py -3.12 release.py %VERSION% %EXE%
    if errorlevel 1 (
        echo   [警告] Gitee Release 发布失败，可手动操作
    )
) else (
    echo   跳过 Gitee Release（无 token）
)
echo [7/8] Gitee 同步完成 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  [8/8] backup 仓库同步
:: ══════════════════════════════════════════════════════════════
echo [8/8] 同步到 backup 仓库...
cd /d "%~dp0\.."
D:\Git\cmd\git.exe push backup main --tags 2>nul
if errorlevel 1 (
    echo   [警告] backup push 部分失败
)
echo [8/8] backup 同步完成 ✓
echo.

:: ══════════════════════════════════════════════════════════════
::  清理 + 完成
:: ══════════════════════════════════════════════════════════════
cd /d "%~dp0"
del /q "_release_notes.md" 2>nul

echo.
echo  ╔════════════════════════════════════════════════════╗
echo  ║  发版完成！ %TAG%                                 ║
echo  ╠════════════════════════════════════════════════════╣
echo  ║  GitHub:  github.com/%REPO%/releases/tag/%TAG%    ║
echo  ║  Gitee:   gitee.com/joinwell52/cursor-ai/releases ║
echo  ║  Backup:  github.com/joinwell52-AI/codehouse      ║
echo  ╚════════════════════════════════════════════════════╝
echo.
