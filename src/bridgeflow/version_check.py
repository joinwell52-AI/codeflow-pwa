"""
版本检查模块：启动时查询 PyPI，有新版本时提示并可自动升级重启。

设计原则：
- 后台线程执行查询，不阻塞启动（async 模式）
- 同步阻塞模式：查到新版后询问用户是否升级，升级后自动重启进程
- 网络不可用时静默失败，不报错
- 每 24 小时最多查一次（结果缓存到 runtime 目录）
- 查询超时 5 秒
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from bridgeflow import __version__

PYPI_URL = "https://pypi.org/pypi/bridgeflow/json"
CACHE_FILE_NAME = "version_check_cache.json"
CHECK_INTERVAL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 5


def _parse_version(v: str) -> tuple[int, ...]:
    """将版本字符串转为可比较元组，如 '0.2.0' → (0, 2, 0)。"""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0,)


def _cache_path(runtime_dir: Optional[str]) -> Path:
    if runtime_dir:
        return Path(runtime_dir) / CACHE_FILE_NAME
    import tempfile
    return Path(tempfile.gettempdir()) / "bridgeflow" / CACHE_FILE_NAME


def _load_cache(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _fetch_latest_version() -> Optional[str]:
    """从 PyPI 获取最新版本号，超时或失败返回 None。"""
    try:
        req = urllib.request.Request(
            PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": f"bridgeflow/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["info"]["version"]
    except Exception:
        return None


def _should_check(cache: dict) -> bool:
    """距上次检查超过 24 小时才重新查询。"""
    last = cache.get("last_checked")
    if not last:
        return True
    try:
        return datetime.now() - datetime.fromisoformat(last) > timedelta(hours=CHECK_INTERVAL_HOURS)
    except Exception:
        return True


def _get_latest_cached_or_fetch(runtime_dir: Optional[str]) -> Optional[str]:
    """返回最新版本号（优先缓存，过期则查 PyPI）。"""
    path = _cache_path(runtime_dir)
    cache = _load_cache(path)

    if _should_check(cache):
        latest = _fetch_latest_version()
        cache["last_checked"] = datetime.now().isoformat()
        if latest:
            cache["latest_version"] = latest
        _save_cache(path, cache)
        return latest
    return cache.get("latest_version")


def _do_upgrade_and_restart() -> None:
    """执行 pip 升级，升级成功后用相同参数重启进程。"""
    print("\n  正在升级 bridgeflow…\n")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "bridgeflow"],
        check=False,
    )
    if result.returncode != 0:
        print("  ✗ 升级失败，请手动运行：pip install --upgrade bridgeflow")
        return

    print("\n  ✓ 升级完成，正在重启…\n")
    # 用相同参数重新执行当前进程
    try:
        os.execv(sys.argv[0], sys.argv)
    except Exception:
        # execv 在某些 Windows 环境下可能不可用，改用 subprocess
        subprocess.Popen([sys.argv[0]] + sys.argv[1:])
        sys.exit(0)


# ── 公开 API ────────────────────────────────────────────────────────────────

def check_update_async(runtime_dir: Optional[str] = None) -> None:
    """
    后台线程检查更新，有新版时仅打印提示框（不交互）。
    适合在脚本/自动化场景中使用。
    """
    def _worker() -> None:
        try:
            latest = _get_latest_cached_or_fetch(runtime_dir)
            if latest and _parse_version(latest) > _parse_version(__version__):
                print()
                print("  ┌─────────────────────────────────────────────────┐")
                print(f"  │  💡 新版本可用：v{latest}（当前 v{__version__}）")
                print(f"  │  升级命令：pip install --upgrade bridgeflow")
                print("  └─────────────────────────────────────────────────┘")
                print()
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    time.sleep(0.3)  # 给线程机会在横幅后打印


def check_update_interactive(runtime_dir: Optional[str] = None,
                             auto_upgrade: bool = False) -> None:
    """
    同步检查更新，有新版时询问用户是否立即升级。
    升级成功后自动重启进程。

    Args:
        runtime_dir:   缓存目录（通常为 config.runtime_dir）
        auto_upgrade:  True 时跳过确认直接升级（--auto-upgrade 模式）
    """
    try:
        latest = _get_latest_cached_or_fetch(runtime_dir)
    except Exception:
        return

    if not latest or _parse_version(latest) <= _parse_version(__version__):
        return

    print()
    print("  ╔═════════════════════════════════════════════════╗")
    print(f"  ║  🚀 发现新版本 v{latest}  （当前 v{__version__}）")
    print(f"  ║  更新内容：https://github.com/joinwell52-ai/BridgeFlow/blob/main/CHANGELOG.md")
    print("  ╚═════════════════════════════════════════════════╝")

    if auto_upgrade:
        _do_upgrade_and_restart()
        return

    try:
        answer = input("  是否立即升级并重启？[y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    if answer in ("y", "yes", "是"):
        _do_upgrade_and_restart()
    else:
        print("  已跳过升级，继续启动…\n")
