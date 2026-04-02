from __future__ import annotations

import ctypes
from dataclasses import asdict, dataclass


@dataclass
class DesktopWindow:
    hwnd: int
    title: str
    pid: int
    visible: bool
    minimized: bool

    def to_dict(self) -> dict:
        return asdict(self)


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def _window_title(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value.strip()


def _window_pid(hwnd: int) -> int:
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _is_visible(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindowVisible(hwnd))


def _is_minimized(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsIconic(hwnd))


def list_desktop_windows() -> list[DesktopWindow]:
    items: list[DesktopWindow] = []

    @EnumWindowsProc
    def callback(hwnd, _lparam):
        hwnd_int = int(hwnd)
        title = _window_title(hwnd_int)
        if not title:
            return True
        items.append(
            DesktopWindow(
                hwnd=hwnd_int,
                title=title,
                pid=_window_pid(hwnd_int),
                visible=_is_visible(hwnd_int),
                minimized=_is_minimized(hwnd_int),
            )
        )
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return items


def focus_window(hwnd: int) -> bool:
    if not hwnd:
        return False
    try:
        if _is_minimized(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, 9)
        else:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        return True
    except Exception:
        return False
