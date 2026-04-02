from __future__ import annotations

import subprocess
import time
from dataclasses import asdict, dataclass

from bridgeflow.config import PatrolConfig
from bridgeflow.desktop.cursor_probe import list_cursor_windows, snapshot_cursor_state
from bridgeflow.desktop.window_control import focus_window


@dataclass
class DesktopActionResult:
    action: str
    ok: bool
    message: str
    dry_run: bool
    cursor_running: bool
    cursor_foreground_before: bool
    cursor_foreground_after: bool
    window_count: int
    target_title: str
    target_pid: int | None
    typed_text: str
    used_pyautogui: bool

    def to_dict(self) -> dict:
        return asdict(self)


ACTION_TEXT = {
    "inspect": "巡检",
    "start_work": "开工",
}


def _copy_text_to_clipboard(text: str) -> bool:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value @'\n" + text + "\n'@"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return completed.returncode == 0
    except Exception:
        return False


def _send_text_via_pyautogui(text: str) -> bool:
    try:
        import pyautogui
    except Exception:
        return False
    if not _copy_text_to_clipboard(text):
        return False
    time.sleep(0.2)
    try:
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        pyautogui.press("enter")
        return True
    except Exception:
        return False


def _best_cursor_window() -> tuple[int, str, int | None] | tuple[None, str, None]:
    windows = list_cursor_windows()
    if not windows:
        return None, "", None
    windows = sorted(windows, key=lambda item: (not item.visible, item.minimized, item.title.lower()))
    target = windows[0]
    return target.hwnd, target.title, target.pid


def execute_desktop_action(config: PatrolConfig, action: str, *, dry_run: bool = False) -> DesktopActionResult:
    action = action.strip()
    snapshot_before = snapshot_cursor_state()
    hwnd, title, pid = _best_cursor_window()
    if not hwnd:
        return DesktopActionResult(
            action=action,
            ok=False,
            message="未发现可操作的 Cursor 窗口",
            dry_run=dry_run,
            cursor_running=snapshot_before.cursor_running,
            cursor_foreground_before=snapshot_before.cursor_foreground,
            cursor_foreground_after=snapshot_before.cursor_foreground,
            window_count=len(snapshot_before.cursor_windows),
            target_title="",
            target_pid=None,
            typed_text="",
            used_pyautogui=False,
        )

    focused = focus_window(hwnd)
    time.sleep(0.2)
    snapshot_after_focus = snapshot_cursor_state()

    if action == "focus_cursor":
        return DesktopActionResult(
            action=action,
            ok=focused,
            message="已尝试聚焦 Cursor 窗口" if focused else "聚焦 Cursor 窗口失败",
            dry_run=dry_run,
            cursor_running=snapshot_before.cursor_running,
            cursor_foreground_before=snapshot_before.cursor_foreground,
            cursor_foreground_after=snapshot_after_focus.cursor_foreground,
            window_count=len(snapshot_before.cursor_windows),
            target_title=title,
            target_pid=pid,
            typed_text="",
            used_pyautogui=False,
        )

    typed_text = ACTION_TEXT.get(action, action)
    if action == "inspect":
        typed_text = config.patrol_message or ACTION_TEXT["inspect"]
    elif action == "start_work":
        typed_text = ACTION_TEXT["start_work"]

    if dry_run:
        return DesktopActionResult(
            action=action,
            ok=focused,
            message=f"dry-run: 已定位窗口，未实际发送 {typed_text}",
            dry_run=True,
            cursor_running=snapshot_before.cursor_running,
            cursor_foreground_before=snapshot_before.cursor_foreground,
            cursor_foreground_after=snapshot_after_focus.cursor_foreground,
            window_count=len(snapshot_before.cursor_windows),
            target_title=title,
            target_pid=pid,
            typed_text=typed_text,
            used_pyautogui=False,
        )

    sent = _send_text_via_pyautogui(typed_text)
    snapshot_after_send = snapshot_cursor_state()
    return DesktopActionResult(
        action=action,
        ok=focused and sent,
        message=(f"已向 Cursor 发送：{typed_text}" if focused and sent else f"发送失败：{typed_text}"),
        dry_run=False,
        cursor_running=snapshot_before.cursor_running,
        cursor_foreground_before=snapshot_before.cursor_foreground,
        cursor_foreground_after=snapshot_after_send.cursor_foreground,
        window_count=len(snapshot_before.cursor_windows),
        target_title=title,
        target_pid=pid,
        typed_text=typed_text,
        used_pyautogui=sent,
    )
