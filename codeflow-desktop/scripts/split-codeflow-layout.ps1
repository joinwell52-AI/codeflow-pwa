#Requires -Version 5.1
<#
.SYNOPSIS
  尝试将 Cursor 与「本机 CodeFlow 面板」浏览器窗口按场景比例贴靠到主显示器工作区（左右分屏）。

.DESCRIPTION
  - 程序无法从面板网页内直接操纵 Cursor 窗口；本脚本用 Win32 MoveWindow 做常见场景下的快速排布。
  - 使用前请先打开：① Cursor  ② 已访问 http://127.0.0.1:18765/ 的浏览器窗口（标题里会含 127.0.0.1 或 18765）。
  - 若有多台显示器，仅处理主屏工作区（任务栏除外）。

.PARAMETER Mode
  preflight — Cursor 约 58%（左），面板约 42%（右），便于侧栏 Agents + Composer 与预检同屏。
  patrol    — Cursor 约 68%（左），面板约 32%（右），巡检时主视野偏代码/对话。
  half      — 各占 50%。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\split-codeflow-layout.ps1 -Mode preflight
#>
param(
    [ValidateSet("preflight", "patrol", "half")]
    [string]$Mode = "preflight"
)

Add-Type -AssemblyName System.Windows.Forms | Out-Null
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinLayout {
  [DllImport("user32.dll", SetLastError = true)]
  public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@

$wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$left = $wa.Left
$top = $wa.Top
$W = $wa.Width
$H = $wa.Height

$cursorRatio = switch ($Mode) {
    "preflight" { 0.58 }
    "patrol" { 0.68 }
    "half" { 0.50 }
}
$split = [int][Math]::Round($W * $cursorRatio)

$cursorProc = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.MainWindowTitle } |
    Select-Object -First 1

$browserProc = Get-Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.MainWindowHandle -ne [IntPtr]::Zero -and
        $_.MainWindowTitle -and (
            $_.MainWindowTitle -match '127\.0\.0\.1|localhost:18765|:18765|CodeFlow|码流'
        )
    } | Select-Object -First 1

if (-not $cursorProc) {
    Write-Warning "未找到带主窗口的 Cursor 进程。请先打开 Cursor。"
    exit 1
}
if (-not $browserProc) {
    Write-Warning "未找到标题含 127.0.0.1 / 18765 的浏览器窗口。请先在浏览器打开 http://127.0.0.1:18765/"
    exit 1
}

$ok1 = [WinLayout]::MoveWindow($cursorProc.MainWindowHandle, $left, $top, $split, $H, $true)
$ok2 = [WinLayout]::MoveWindow($browserProc.MainWindowHandle, $left + $split, $top, $W - $split, $H, $true)

if ($ok1 -and $ok2) {
    Write-Host "已按 Mode=$Mode 贴靠：Cursor 宽≈$split px，面板宽≈$($W - $split) px（主屏工作区 ${W}x${H}）。"
    Write-Host "提示：在 Cursor 内保持侧栏与 Composer 打开，便于 Agents + 聊天可见。"
    exit 0
}

Write-Warning "MoveWindow 部分失败（可能被系统/最小化阻止）。"
exit 1
