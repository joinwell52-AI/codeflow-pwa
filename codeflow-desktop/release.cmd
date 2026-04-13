@echo off
:: CodeFlow Desktop 一键发版脚本
:: 用法：release.cmd <版本号>
:: 示例：release.cmd 2.9.22
::
:: 效果：
::   1. 检查 CHANGELOG 是否有对应版本说明
::   2. 打包 EXE
::   3. git commit + tag + push（触发代码同步）
::   4. 用 gh CLI 创建 GitHub Release 并上传 EXE
::      （若 gh 未登录，先执行 gh auth login）

cd /d "%~dp0"
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo.
    echo 用法: release.cmd ^<版本号^>
    echo 示例: release.cmd 2.9.22
    echo.
    exit /b 1
)

set VERSION=%~1
set TAG=v%VERSION%
set REPO=joinwell52-AI/codeflow-pwa
set EXE=dist\CodeFlow-Desktop.exe

echo.
echo ╔══════════════════════════════════════════╗
echo   CodeFlow Desktop 发版  %TAG%
echo ╚══════════════════════════════════════════╝
echo.

:: ── 1. 检查 CHANGELOG ─────────────────────────────────────────────
echo [1/5] 检查 CHANGELOG...
findstr /C:"## [%VERSION%]" ..\CHANGELOG.md
if errorlevel 1 (
    echo.
    echo [错误] CHANGELOG.md 中未找到版本 [%VERSION%] 的条目！
    echo 请先在 CHANGELOG.md 中补充本版发版说明，格式：
    echo   ## [%VERSION%] - YYYY-MM-DD
    echo.
    exit /b 1
)
echo [1/5] CHANGELOG 检查通过 ✓

:: ── 2. 打包 ───────────────────────────────────────────────────────
echo.
echo [2/5] 打包 EXE...
call pack.cmd
:: pack.cmd 因 snap_click 编码问题会返回 1，但 EXE 实际已生成，检查文件
if not exist "%EXE%" (
    echo [错误] 打包失败，%EXE% 不存在！
    exit /b 1
)
echo [2/5] 打包完成 ✓  (%EXE%)

:: ── 3. 提取 CHANGELOG 当前版本说明（写入临时文件）────────────────
echo.
echo [3/5] 提取版本说明...
py -3.12 -c "
import re, sys
ver = '%VERSION%'
text = open('../CHANGELOG.md', encoding='utf-8').read()
m = re.search(r'## \[' + re.escape(ver) + r'\].*?\n(.*?)(?=\n## \[|\Z)', text, re.DOTALL)
body = m.group(1).strip() if m else ''
header = '''## 码流（CodeFlow）Desktop v%VERSION%

> 下载 `CodeFlow-Desktop.exe`，双击运行，无需安装。
> 已安装旧版的用户程序会**自动检测并提示更新**，无需手动下载。

---

'''
footer = '''

---

### 系统要求
- Windows 10 / 11（64 位）
- 已安装 [Cursor IDE](https://www.cursor.com/)

### 快速开始
1. 双击 `CodeFlow-Desktop.exe` 启动
2. 按引导选择项目目录和团队模板
3. 手机打开 [码流 PWA](https://joinwell52-ai.github.io/codeflow-pwa/) 扫码绑定

### 完整更新日志
见 [CHANGELOG.md](https://github.com/joinwell52-AI/codeflow-pwa/blob/main/CHANGELOG.md)
'''
open('_release_notes.md', 'w', encoding='utf-8').write(header + body + footer)
print('OK')
"
if errorlevel 1 (
    echo [错误] 提取版本说明失败
    exit /b 1
)
echo [3/5] 版本说明已生成 ✓

:: ── 4. git commit + tag + push ────────────────────────────────────
echo.
echo [4/5] 提交代码并打 tag %TAG%...
cd /d "%~dp0\.."
git add -A
git commit -m "release: CodeFlow Desktop %TAG%"
git tag -a %TAG% -m "CodeFlow Desktop %TAG%"
git push origin main
git push origin %TAG%
if errorlevel 1 (
    echo [警告] git push 可能失败，请检查网络和权限
)
echo [4/5] 代码已推送 ✓

:: ── 5. 创建 GitHub Release 并上传 EXE ────────────────────────────
echo.
echo [5/5] 发布 GitHub Release...
cd /d "%~dp0"

gh release create %TAG% ^
    "%EXE%#CodeFlow-Desktop.exe" ^
    --repo %REPO% ^
    --title "CodeFlow Desktop %TAG%" ^
    --notes-file "_release_notes.md"

if errorlevel 1 (
    echo.
    echo [错误] GitHub Release 创建失败！
    echo 可能原因：
    echo   1. gh 未登录 → 先运行: gh auth login
    echo   2. tag 已存在 → git tag -d %TAG% 删除后重试
    echo   3. 网络问题
    del /q "_release_notes.md" 2>nul
    exit /b 1
)

del /q "_release_notes.md" 2>nul

echo.
echo ╔══════════════════════════════════════════╗
echo   发版成功！ %TAG%
echo   https://github.com/%REPO%/releases/tag/%TAG%
echo ╚══════════════════════════════════════════╝
echo.
