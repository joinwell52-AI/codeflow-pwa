from __future__ import annotations

import csv
import ctypes
import re
import subprocess
from dataclasses import asdict, dataclass

from bridgeflow.desktop.window_control import DesktopWindow, list_desktop_windows


@dataclass
class CursorSnapshot:
    os_name: str
    cursor_running: bool
    cursor_process_count: int
    cursor_pids: list[int]
    foreground_title: str
    foreground_exe: str
    foreground_pid: int | None
    cursor_foreground: bool
    project_hint: str
    cursor_windows: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


CURSOR_TITLE_KEYWORDS = ("cursor",)


def _run_command(args: list[str]) -> str:
    try:
        completed = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="ignore", check=False)
        return completed.stdout.strip()
    except Exception:
        return ""


def _tasklist_rows(filters: list[str]) -> list[dict[str, str]]:
    output = _run_command(["tasklist", *filters, "/FO", "CSV", "/NH"])
    rows: list[dict[str, str]] = []
    if not output:
        return rows
    reader = csv.reader(line for line in output.splitlines() if line.strip())
    for row in reader:
        if not row or row[0].startswith("INFO:"):
            continue
        if len(row) < 2:
            continue
        rows.append({"image_name": row[0], "pid": row[1]})
    return rows


def _list_cursor_processes() -> list[int]:
    rows = _tasklist_rows(["/FI", "IMAGENAME eq Cursor.exe"])
    return [int(item["pid"]) for item in rows if str(item.get("pid", "")).isdigit()]


def _foreground_window_handle() -> int:
    try:
        return int(ctypes.windll.user32.GetForegroundWindow())
    except Exception:
        return 0


def _foreground_window_title() -> str:
    handle = _foreground_window_handle()
    if not handle:
        return ""
    buffer = ctypes.create_unicode_buffer(512)
    try:
        ctypes.windll.user32.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value.strip()
    except Exception:
        return ""


def _foreground_pid() -> int | None:
    handle = _foreground_window_handle()
    if not handle:
        return None
    pid = ctypes.c_ulong()
    try:
        ctypes.windll.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return int(pid.value) if pid.value else None
    except Exception:
        return None


def _image_name_by_pid(pid: int | None) -> str:
    if not pid:
        return ""
    rows = _tasklist_rows(["/FI", f"PID eq {pid}"])
    if not rows:
        return ""
    return str(rows[0].get("image_name", "")).strip()


def _project_hint_from_title(title: str) -> str:
    if not title:
        return ""
    patterns = [
        r"^(.*?)\s+-\s+Cursor$",
        r"^(.*?)\s+[-|]\s+Cursor$",
        r"^(.*?)\s+-\s+Visual Studio Code$",
    ]
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            return match.group(1).strip()
    return title[:80].strip()


def _is_cursor_window(window: DesktopWindow, cursor_pids: set[int]) -> bool:
    if window.pid in cursor_pids:
        return True
    title = window.title.lower()
    return any(keyword in title for keyword in CURSOR_TITLE_KEYWORDS)


def list_cursor_windows() -> list[DesktopWindow]:
    cursor_pids = set(_list_cursor_processes())
    return [item for item in list_desktop_windows() if _is_cursor_window(item, cursor_pids)]


def snapshot_cursor_state() -> CursorSnapshot:
    cursor_pids = _list_cursor_processes()
    title = _foreground_window_title()
    foreground_pid = _foreground_pid()
    foreground_exe = _image_name_by_pid(foreground_pid)
    cursor_foreground = foreground_exe.lower() == "cursor.exe" or title.lower().endswith("cursor")
    windows = [item.to_dict() for item in list_cursor_windows()]
    return CursorSnapshot(
        os_name="windows",
        cursor_running=bool(cursor_pids),
        cursor_process_count=len(cursor_pids),
        cursor_pids=cursor_pids,
        foreground_title=title,
        foreground_exe=foreground_exe,
        foreground_pid=foreground_pid,
        cursor_foreground=cursor_foreground,
        project_hint=_project_hint_from_title(title),
        cursor_windows=windows,
    )
