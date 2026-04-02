"""
跨平台环境检测：Python版本、Cursor安装/运行状态、操作系统
支持 Windows / macOS / Linux
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass
class EnvCheckResult:
    os_name: str          # Windows / Darwin / Linux
    os_version: str
    python_version: str
    python_ok: bool       # >= 3.10
    cursor_installed: bool
    cursor_running: bool
    cursor_hint: str      # 安装路径或提示信息

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def ready(self) -> bool:
        return self.python_ok and self.cursor_installed


def _run(args: list[str]) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


def _find_cursor_via_registry() -> str:
    """从 Windows 注册表卸载项中查找 Cursor 安装路径"""
    try:
        import winreg
    except ImportError:
        return ""

    reg_paths = [
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, reg_path in reg_paths:
        try:
            key = winreg.OpenKey(hive, reg_path)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
                try:
                    subkey = winreg.OpenKey(key, subkey_name)
                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                    if "cursor" in str(display_name).lower():
                        # 尝试读安装位置
                        for field in ("InstallLocation", "DisplayIcon", "UninstallString"):
                            try:
                                val, _ = winreg.QueryValueEx(subkey, field)
                                val = str(val).strip('"').strip()
                                if val:
                                    # InstallLocation 是目录，拼上 Cursor.exe
                                    exe = val if val.lower().endswith(".exe") else os.path.join(val, "Cursor.exe")
                                    if os.path.exists(exe):
                                        return exe
                                    if os.path.isdir(val):
                                        return val
                            except OSError:
                                pass
                    winreg.CloseKey(subkey)
                except OSError:
                    pass
        finally:
            winreg.CloseKey(key)
    return ""


def _check_windows() -> tuple[bool, bool, str]:
    """返回 (installed, running, hint)"""
    # 1. 检测是否在运行
    out = _run(["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/FO", "CSV", "/NH"])
    running = "Cursor.exe" in out

    # 2. 注册表查找（最准确）
    reg_path = _find_cursor_via_registry()
    if reg_path:
        return True, running, reg_path

    # 3. 常见默认路径兜底
    local_app = os.environ.get("LOCALAPPDATA", "")
    user_profile = os.environ.get("USERPROFILE", "")
    candidates = [
        os.path.join(local_app, "Programs", "cursor", "Cursor.exe"),
        os.path.join(local_app, "Programs", "Cursor", "Cursor.exe"),
        os.path.join(user_profile, "AppData", "Local", "Programs", "cursor", "Cursor.exe"),
        r"C:\Program Files\Cursor\Cursor.exe",
        r"C:\Program Files (x86)\Cursor\Cursor.exe",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return True, running, path

    # 4. 数据目录兜底
    data_dirs = [
        os.path.join(user_profile, ".cursor"),
        os.path.join(local_app, "Cursor"),
        os.path.join(os.environ.get("APPDATA", ""), "Cursor"),
    ]
    for d in data_dirs:
        if d and os.path.isdir(d):
            return True, running, f"已安装（数据目录: {d}）"

    if running:
        return True, True, "运行中（未找到安装路径）"
    return False, False, "未检测到 Cursor，请从 https://cursor.com 下载安装"


def _check_macos() -> tuple[bool, bool, str]:
    app_path = "/Applications/Cursor.app"
    installed = os.path.exists(app_path)

    out = _run(["pgrep", "-x", "Cursor"])
    running = bool(out.strip())

    if installed:
        return True, running, app_path
    if running:
        return True, True, "运行中（未找到 /Applications/Cursor.app）"
    return False, False, "未检测到 Cursor，请从 https://cursor.com 下载安装"


def _check_linux() -> tuple[bool, bool, str]:
    import shutil
    path = shutil.which("cursor") or shutil.which("Cursor")
    installed = bool(path)

    out = _run(["pgrep", "-x", "cursor"])
    running = bool(out.strip())

    if installed:
        return True, running, path or "cursor"
    if running:
        return True, True, "运行中（which 未找到路径）"
    return False, False, "未检测到 Cursor，请从 https://cursor.com 下载安装"


def check_env() -> EnvCheckResult:
    os_name = platform.system()       # Windows / Darwin / Linux
    os_version = platform.version()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)

    if os_name == "Windows":
        installed, running, hint = _check_windows()
    elif os_name == "Darwin":
        installed, running, hint = _check_macos()
    else:
        installed, running, hint = _check_linux()

    return EnvCheckResult(
        os_name=os_name,
        os_version=os_version,
        python_version=py_ver,
        python_ok=py_ok,
        cursor_installed=installed,
        cursor_running=running,
        cursor_hint=hint,
    )
