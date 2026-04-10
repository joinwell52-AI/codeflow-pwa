"""
轻量 MCP：在 Cursor 内通过命令面板打开 Simple Browser，加载本机 CodeFlow 控制面板。

与 ``mcp_server.py``（协作任务工具集）独立，仅需 ``fastmcp`` + ``pyautogui``。

实现方式：模拟键盘（与 CodeFlow Desktop 巡检一致），不依赖未公开的 ACP HTTP 端点。

前置：已运行 CodeFlow-Desktop.exe，本机 ``http://127.0.0.1:18765/`` 可访问。

``mcp.json`` 中 ``command`` / ``args`` 指向本文件绝对路径；依赖见 ``requirements-codeflow-mcp.txt``。
"""
from __future__ import annotations

import sys
import time

from fastmcp import FastMCP

mcp = FastMCP(
    name="codeflow-panel",
    instructions=(
        "Open the CodeFlow control panel at http://127.0.0.1:18765/ inside Cursor Simple Browser. "
        "Requires CodeFlow Desktop running. Uses keyboard automation."
    ),
)

_DEFAULT_URL = "http://127.0.0.1:18765/"


def _palette_hotkey() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return ("command", "shift", "p")
    return ("ctrl", "shift", "p")


def _activate_cursor_window() -> tuple[bool, str]:
    try:
        import pyautogui
    except ImportError:
        return False, "未安装 pyautogui；在 codeflow-plugin 目录执行: pip install -r requirements-codeflow-mcp.txt"

    if not hasattr(pyautogui, "getWindowsWithTitle"):
        return (
            False,
            "当前环境无 getWindowsWithTitle，请先手动点击 Cursor 窗口使其获得焦点，再重试工具。",
        )

    try:
        wins = pyautogui.getWindowsWithTitle("Cursor")
    except Exception as e:
        return False, f"枚举窗口失败: {e}"

    if not wins:
        return False, "未找到标题含 Cursor 的窗口，请先打开 Cursor。"

    try:
        wins[0].activate()
    except Exception as e:
        return False, f"激活窗口失败: {e}"

    return True, ""


@mcp.tool
def open_codeflow_panel(
    url: str = _DEFAULT_URL,
    wait_s: float = 0.25,
) -> str:
    """在 Cursor 内置 Simple Browser 中打开 CodeFlow 控制面板。

    Args:
        url: 面板地址，默认 http://127.0.0.1:18765/
        wait_s: 各步骤间等待（秒），界面较慢时可略增大。
    """
    ok, err = _activate_cursor_window()
    if not ok:
        return f"[失败] {err}"

    try:
        import pyautogui
    except ImportError:
        return "[失败] 未安装 pyautogui"

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    try:
        time.sleep(wait_s)
        pyautogui.hotkey(*_palette_hotkey())
        time.sleep(wait_s + 0.12)
        pyautogui.write("Simple Browser", interval=0.02)
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(wait_s + 0.35)
        pyautogui.write(url.strip() or _DEFAULT_URL, interval=0.015)
        time.sleep(0.06)
        pyautogui.press("enter")
    except Exception as e:
        return f"[失败] 操作中断: {e}"

    return f"[成功] 已在 Cursor 内请求打开 Simple Browser：{url.strip() or _DEFAULT_URL}"


@mcp.tool
def refresh_codeflow_panel() -> str:
    """刷新当前聚焦视图（Ctrl+R / Cmd+R）；焦点需在 Simple Browser 内才生效。"""
    ok, err = _activate_cursor_window()
    if not ok:
        return f"[失败] {err}"

    try:
        import pyautogui
    except ImportError:
        return "[失败] 未安装 pyautogui"

    try:
        if sys.platform == "darwin":
            pyautogui.hotkey("command", "r")
        else:
            pyautogui.hotkey("ctrl", "r")
    except Exception as e:
        return f"[失败] {e}"

    return "[成功] 已发送刷新快捷键（请确认焦点在 Simple Browser 内）"


if __name__ == "__main__":
    mcp.run()
