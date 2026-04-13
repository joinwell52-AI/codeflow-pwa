"""
启动后在 Cursor 内用 Simple Browser 打开本机面板（命令面板自动化，不依赖 MCP）。

依赖 pyautogui（nudger 已依赖）。Windows 下自动查找 Cursor.exe 常见路径；macOS 可用 `open -a Cursor`；非标准路径可配置 `cursor_exe_path`。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger("codeflow.embed")


def default_cursor_exe() -> Path | None:
    """常见安装路径：%LOCALAPPDATA%\\Programs\\cursor\\Cursor.exe"""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            p = Path(local) / "Programs" / "cursor" / "Cursor.exe"
            if p.is_file():
                return p
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        p2 = Path(pf) / "Cursor" / "Cursor.exe"
        if p2.is_file():
            return p2
    if sys.platform == "darwin":
        p = Path("/Applications/Cursor.app/Contents/MacOS/Cursor")
        if p.is_file():
            return p
    return None


def try_launch_cursor(exe: Path, project_dir: Path | None = None) -> tuple[bool, str]:
    if not exe.is_file():
        return False, f"文件不存在: {exe}"
    try:
        if sys.platform == "darwin":
            if project_dir:
                subprocess.Popen(["open", "-a", "Cursor", str(project_dir)])
            else:
                subprocess.Popen(["open", "-a", "Cursor"])
        else:
            # 传入项目目录，让 Cursor 直接打开对应工作区
            # --remote-debugging-port=9222 让 Playwright 可以通过 CDP 协议连接
            cmd = [str(exe), "--remote-debugging-port=9222"]
            if project_dir and project_dir.is_dir():
                cmd.append(str(project_dir))
            subprocess.Popen(cmd, cwd=str(exe.parent), shell=False)
        return True, str(exe)
    except Exception as e:
        return False, str(e)


def _find_cursor_pids() -> set[int]:
    """用多种方法枚举 Cursor 进程 PID，任一成功即返回。"""
    _cursor_names = {"cursor.exe", "code.exe"}
    pids: set[int] = set()

    # 方法1：win32 API CreateToolhelp32Snapshot（最直接，不依赖外部命令）
    try:
        import ctypes, ctypes.wintypes
        TH32CS_SNAPPROCESS = 0x2
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize",              ctypes.wintypes.DWORD),
                ("cntUsage",            ctypes.wintypes.DWORD),
                ("th32ProcessID",       ctypes.wintypes.DWORD),
                ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID",        ctypes.wintypes.DWORD),
                ("cntThreads",          ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD),
                ("pcPriClassBase",      ctypes.c_long),
                ("dwFlags",             ctypes.wintypes.DWORD),
                ("szExeFile",           ctypes.c_char * 260),
            ]
        snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap and snap != ctypes.wintypes.HANDLE(-1).value:
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            ok = ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))
            while ok:
                name = pe.szExeFile.decode(errors="replace").lower()
                if name in _cursor_names:
                    pids.add(pe.th32ProcessID)
                ok = ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe))
            ctypes.windll.kernel32.CloseHandle(snap)
        if pids:
            logger.info("[Cursor 查找] Toolhelp32 找到 cursor PIDs=%s", pids)
            return pids
    except Exception as e:
        logger.debug("[Cursor 查找] Toolhelp32 失败: %s", e)

    # 方法2：psutil
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() in _cursor_names:
                    pids.add(proc.info["pid"])
            except Exception:
                pass
        if pids:
            logger.info("[Cursor 查找] psutil 找到 cursor PIDs=%s", pids)
            return pids
    except Exception:
        pass

    # 方法3：tasklist 全量输出
    try:
        import subprocess
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            timeout=8, creationflags=0x08000000
        ).decode(errors="replace")
        for line in out.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() in _cursor_names:
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    pass
        if pids:
            logger.info("[Cursor 查找] tasklist 找到 cursor PIDs=%s", pids)
    except Exception as e:
        logger.debug("[Cursor 查找] tasklist 失败: %s", e)

    return pids


def _find_cursor_main_hwnd() -> int | None:
    """
    用 win32 找 Cursor 主窗口 hwnd。
    条件：cursor.exe 进程 + 有窗口标题 + 无 Owner + 可见 + 面积最大。
    """
    if sys.platform != "win32":
        return None
    try:
        import win32gui
        import win32con
        import win32process

        cursor_pids = _find_cursor_pids()

        # 仍然没找到：枚举所有可见顶层窗口，取面积最大且有标题的（Cursor 通常是最大窗口）
        if not cursor_pids:
            logger.info("[Cursor 查找] tasklist 未找到 cursor 进程，降级取最大可见窗口")
            _all_windows: list[tuple[int,int,str]] = []
            def _cb_all(hwnd: int, _) -> None:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                if win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0:
                    return
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return
                # 排除自身面板和已知系统/工具窗口
                _skip = ("codeflow", "码流", "program manager", "windows 输入体验",
                         "任务管理器", "task manager", "向日葵", "sunlogin",
                         "设置", "settings", "microsoft text")
                if any(s in title.lower() for s in _skip):
                    return
                try:
                    r = win32gui.GetWindowRect(hwnd)
                    area = max(0, r[2]-r[0]) * max(0, r[3]-r[1])
                    if area > 100000:  # 至少 ~316x316，排除小窗口
                        logger.info("[Cursor 查找][all] title=%r area=%d", title, area)
                        _all_windows.append((area, hwnd, title))
                except Exception:
                    pass
            win32gui.EnumWindows(_cb_all, None)
            if _all_windows:
                _all_windows.sort(reverse=True)
                best_title = _all_windows[0][2]
                best_area  = _all_windows[0][0]
                # 只有标题包含明确 IDE 特征才信任，否则认为 Cursor 未运行
                _ide_hints = ("cursor", "code", "vscode", "vs code", "visual studio")
                if any(h in best_title.lower() for h in _ide_hints):
                    logger.info("[Cursor 查找] 选最大窗口: title=%r area=%d", best_title, best_area)
                    return _all_windows[0][1]
                else:
                    logger.info("[Cursor 查找] 最大窗口 %r 不像 IDE，视为 Cursor 未运行", best_title)
            return None

        logger.info("[Cursor 查找] 找到 cursor.exe 进程数: %d PIDs=%s", len(cursor_pids), cursor_pids)

        best_hwnd: int | None = None
        best_area = -1

        def _cb(hwnd: int, _) -> None:
            nonlocal best_hwnd, best_area
            if not win32gui.IsWindowVisible(hwnd):
                return
            if win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0:
                return
            if not win32gui.GetWindowText(hwnd):
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid not in cursor_pids:
                    return
                r = win32gui.GetWindowRect(hwnd)
                area = max(0, r[2] - r[0]) * max(0, r[3] - r[1])
                title = win32gui.GetWindowText(hwnd)
                logger.info("[Cursor 查找] 命中窗口 title=%r area=%d", title, area)
                score = area * 2 + (1 if "cursor" in title.lower() else 0)
                if score > best_area:
                    best_area = score
                    best_hwnd = hwnd
            except Exception:
                pass

        win32gui.EnumWindows(_cb, None)
        return best_hwnd
    except Exception as e:
        logger.warning("[Cursor 嵌入] 查找主窗口失败: %s", e)
        return None


def _force_maximize(hwnd: int) -> None:
    """
    强制全屏最大化 Cursor 窗口，不依赖 IsZoomed（Electron 下不可靠）。
    方法：先还原（解除贴靠），再 SW_SHOWMAXIMIZED，再置前台。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        import win32gui
        import win32con
        user32 = ctypes.windll.user32

        # 先还原（解除任何贴靠/最小化状态）
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.15)

        # 强制最大化
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        time.sleep(0.3)

        # 置前台
        ALT = 0x12
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(ALT, 0, 0, 0)
        user32.keybd_event(ALT, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.2)

        logger.info("[Cursor 嵌入] 强制最大化完成 hwnd=%s", hwnd)
    except Exception as e:
        logger.warning("[Cursor 嵌入] _force_maximize 失败: %s", e)


def _ensure_maximized_and_focus(hwnd: int) -> None:
    """兼容旧调用，直接走强制最大化。"""
    _force_maximize(hwnd)


def _wait_for_cursor_window(timeout_s: float = 60.0, poll: float = 0.8) -> int | None:
    """
    等待 Cursor 主窗口出现且达到可操作大小（冷启动后轮询）。
    条件：找到 hwnd 且窗口面积 > 0（只要窗口出现就行，不限大小）。
    返回找到的 hwnd，超时返回 None。
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        hwnd = _find_cursor_main_hwnd()
        if hwnd:
            logger.info("[Cursor 嵌入] Cursor 窗口就绪 hwnd=%s", hwnd)
            time.sleep(2.0)  # 等待 Cursor 完成初始渲染
            return hwnd
        time.sleep(poll)
    logger.warning("[Cursor 嵌入] 等待 Cursor 窗口超时 (%.0fs)", timeout_s)
    return None


def _palette_hotkey() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return ("command", "shift", "p")
    return ("ctrl", "shift", "p")


def _embed_palette_command() -> str:
    return (os.environ.get("CODEFLOW_EMBED_PALETTE_TEXT") or "").strip() or "Simple Browser: Show"


def _do_embed(hwnd: int, url: str, wait_s: float = 0.28) -> tuple[bool, str]:
    """
    已知 hwnd 的情况下执行嵌入：
    1. 最大化 + 置前台
    2. 打开命令面板
    3. 输入 Simple Browser 命令
    4. 输入 URL
    """
    try:
        import pyautogui
    except ImportError:
        return False, "未安装 pyautogui"

    try:
        import pyperclip
    except ImportError:
        pyperclip = None  # type: ignore[assignment]

    pyautogui.FAILSAFE = False  # 嵌入过程中移动鼠标到角落不应中断
    pyautogui.PAUSE = 0.05

    url_s = (url or "").strip()
    if not url_s:
        return False, "url 为空"

    old_clip = ""
    if pyperclip:
        try:
            old_clip = pyperclip.paste() or ""
        except Exception:
            pass

    try:
        # Step 1: 最大化并置前台
        _ensure_maximized_and_focus(hwnd)
        time.sleep(0.6)  # 等焦点彻底切到 Cursor

        # Step 2: 用 Ctrl+Shift+B 直接打开内嵌浏览器（Open Browser 命令）
        pyautogui.hotkey("ctrl", "shift", "b")
        time.sleep(wait_s + 1.5)  # 等待 URL 输入框完全弹出

        # Step 3: 地址栏焦点已在，直接粘贴 URL，回车
        if pyperclip:
            pyperclip.copy(url_s)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.write(url_s, interval=0.012)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.8)

        # Step 4: 嵌入完成后强制最大化（解除贴靠+全屏）
        _force_maximize(hwnd)

        logger.info("[Cursor 嵌入] Ctrl+Shift+B → %r", url_s[:80])
        return True, "ok"
    except Exception as e:
        return False, str(e)
    finally:
        if pyperclip and old_clip:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass


def try_open_simple_browser_embed(url: str, wait_s: float = 0.28) -> tuple[bool, str]:
    """
    Cursor 已在运行时：找到主窗口 → 最大化 → 发命令面板嵌入面板。
    """
    hwnd = _find_cursor_main_hwnd()
    if not hwnd:
        return False, "未找到 Cursor 主窗口"
    return _do_embed(hwnd, url, wait_s=wait_s)


def embed_panel_after_launch(
    url: str,
    *,
    cursor_exe: Path | None,
    launch_if_no_window: bool,
    project_dir: Path | None = None,
    wait_s: float = 0.28,
) -> tuple[bool, str]:
    """
    主入口：
    1. Cursor 已启动 → 直接嵌入
    2. Cursor 未启动 且 launch_if_no_window=True → 拉起 Cursor（带项目目录），等窗口出现，再嵌入
    """
    # 情况1：Cursor 已在运行
    hwnd = _find_cursor_main_hwnd()
    if hwnd:
        logger.info("[Cursor 嵌入] Cursor 已运行，直接嵌入 hwnd=%s", hwnd)
        time.sleep(1.5)  # Cursor 已在运行时，等焦点稳定再嵌入
        return _do_embed(hwnd, url, wait_s=wait_s)

    # 情况2：Cursor 未运行
    if not launch_if_no_window:
        return False, "未找到 Cursor 窗口且不允许启动"

    exe = cursor_exe if (cursor_exe and cursor_exe.is_file()) else default_cursor_exe()
    if not exe:
        return False, "未找到 Cursor 可执行文件"

    launched, lmsg = try_launch_cursor(exe, project_dir=project_dir)
    if not launched:
        return False, f"启动 Cursor 失败: {lmsg}"

    logger.info("[Cursor 嵌入] 已启动 Cursor: %s，等待窗口出现…", lmsg)
    hwnd = _wait_for_cursor_window(timeout_s=60.0)
    if not hwnd:
        return False, "等待 Cursor 窗口超时"

    return _do_embed(hwnd, url, wait_s=wait_s + 0.15)
