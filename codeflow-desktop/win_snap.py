"""
Windows：将 Cursor 主窗口与「本机 CodeFlow 面板」浏览器窗口贴靠主屏工作区左右分栏
（效果接近 Win+← / Win+→，便于预检时 Agents + 聊天同屏可见）。

非 Windows 或缺少依赖时安全跳过。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Literal

Mode = Literal["preflight", "patrol", "half"]


def _work_area() -> tuple[int, int, int, int]:
    """主显示器工作区 (left, top, width, height)，不含任务栏。"""
    SPI_GETWORKAREA = 0x0030

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_int),
            ("top", ctypes.c_int),
            ("right", ctypes.c_int),
            ("bottom", ctypes.c_int),
        ]

    r = RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0)
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def _cursor_pids() -> list[int]:
    """枚举进程名 Cursor.exe 的 PID。"""
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_ulong),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return []
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    out: list[int] = []
    if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            if pe.szExeFile.lower() == "cursor.exe":
                out.append(int(pe.th32ProcessID))
            if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(snap)
    return out


def _best_hwnd_for_pid(pid: int):
    """同 PID 下取面积最大的可见顶层窗口。"""
    try:
        import win32con
        import win32gui
        import win32process
    except ImportError:
        return None

    hwnds: list[int] = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return True
        if win32gui.GetWindow(h, win32con.GW_OWNER) != 0:
            return True
        _, cpid = win32process.GetWindowThreadProcessId(h)
        if cpid == pid:
            hwnds.append(h)
        return True

    win32gui.EnumWindows(cb, None)
    if not hwnds:
        return None

    user32 = ctypes.windll.user32

    def area(h):
        rect = wintypes.RECT()
        if not user32.GetWindowRect(h, ctypes.byref(rect)):
            return 0
        return max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)

    return max(hwnds, key=area)


def _panel_browser_hwnd():
    """标题含 127.0.0.1 / 18765 / 码流 的可见顶层窗口；排除 Cursor.exe（避免把主窗当成浏览器）。"""
    try:
        import re
        import win32con
        import win32gui
        import win32process
    except ImportError:
        return None

    cursor_pids = set(_cursor_pids())
    pat = re.compile(r"127\.0\.0\.1|localhost:18765|:18765|码流|CodeFlow.*控制", re.I)
    candidates: list[tuple[int, int]] = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return True
        if win32gui.GetWindow(h, win32con.GW_OWNER) != 0:
            return True
        _, pid = win32process.GetWindowThreadProcessId(h)
        if pid in cursor_pids:
            return True
        title = win32gui.GetWindowText(h) or ""
        if not pat.search(title):
            return True
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        if not user32.GetWindowRect(h, ctypes.byref(rect)):
            return True
        a = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
        if a > 400:
            candidates.append((a, h))
        return True

    win32gui.EnumWindows(cb, None)
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def snap_cursor_and_panel_browser(mode: Mode = "preflight") -> tuple[bool, str]:
    """
    将 Cursor 置于工作区左侧、面板浏览器置于右侧（按比例）。
    Returns: (ok, message_zh)
    """
    if sys.platform != "win32":
        return False, "非 Windows，跳过分屏"

    ratio = {"preflight": 0.58, "patrol": 0.68, "half": 0.50}.get(mode, 0.58)

    left, top, W, H = _work_area()
    split = int(round(W * ratio))

    pids = _cursor_pids()
    chwnd = None
    for pid in pids:
        chwnd = _best_hwnd_for_pid(pid)
        if chwnd:
            break

    bhwnd = _panel_browser_hwnd()

    user32 = ctypes.windll.user32

    if not chwnd:
        return False, "未找到 Cursor 主窗口（请先打开 Cursor）"
    if not bhwnd:
        return False, "未找到含 127.0.0.1:18765 的浏览器窗口（请先打开面板页）"

    ok1 = user32.MoveWindow(chwnd, left, top, split, H, True)
    ok2 = user32.MoveWindow(bhwnd, left + split, top, W - split, H, True)

    if ok1 and ok2:
        return (
            True,
            f"已分屏（{mode}）：Cursor≈{split}px，面板≈{W - split}px，工作区 {W}×{H}",
        )
    return False, "MoveWindow 失败（窗口可能被最小化或权限限制）"
