"""
CodeFlow Desktop 自动更新模块

流程：
1. check_update()  — 请求 GitHub Releases API，比较版本号
2. 发现新版本     — 后台线程静默下载新 EXE 到临时目录
3. 下载完成       — 设置 _update_ready 标志，前端轮询 /api/update/check 获知
4. apply_update() — 写入替换脚本并重启，脚本等旧进程退出后复制新 EXE 覆盖原文件

GitHub Releases 约定：
  - Repo   : GITHUB_REPO  (owner/repo)
  - Asset  : CodeFlow-Desktop.exe
  - Tag    : v{version}，如 v2.9.19
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger("codeflow.updater")

# ── 配置 ─────────────────────────────────────────────────────────────
GITHUB_REPO   = "joinwell52-AI/codeflow-pwa"
ASSET_NAME    = "CodeFlow-Desktop.exe"
API_URL       = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_TIMEOUT = 10   # 秒
DL_TIMEOUT    = 120  # 秒，单次 read 超时

# ── 状态 ─────────────────────────────────────────────────────────────
_lock           = threading.Lock()
_state: dict    = {
    "status":           "idle",   # idle | startup_checking | checking | no_update | downloading | ready | error
    "latest":           "",       # 最新版本号，如 "2.9.19"
    "current":          "",       # 当前版本号
    "progress":         0,        # 下载进度 0-100
    "error":            "",
    "download_url":     "",
    "new_exe":          "",       # 下载完成后的临时文件路径
    "startup_checking": False,    # 启动阶段同步检查中
}


def _set(**kw):
    with _lock:
        _state.update(kw)


def get_state() -> dict:
    with _lock:
        return dict(_state)


# ── 版本比较 ──────────────────────────────────────────────────────────
def _parse_version(v: str) -> tuple:
    v = v.lstrip("v").strip()
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


# ── GitHub API ────────────────────────────────────────────────────────
def _fetch_latest_release() -> dict | None:
    """返回 {version, download_url} 或 None。"""
    try:
        req = Request(API_URL, headers={"Accept": "application/vnd.github+json",
                                        "User-Agent": "CodeFlow-Desktop-Updater"})
        with urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])
        url = next((a["browser_download_url"] for a in assets
                    if a.get("name") == ASSET_NAME), None)
        if tag and url:
            return {"version": tag.lstrip("v"), "download_url": url}
    except URLError as e:
        logger.debug("[updater] 网络请求失败: %s", e)
    except Exception as e:
        logger.debug("[updater] release 解析失败: %s", e)
    return None


# ── 下载 ──────────────────────────────────────────────────────────────
def _download(url: str, dest: Path) -> bool:
    """流式下载，更新进度。返回是否成功。"""
    try:
        req = Request(url, headers={"User-Agent": "CodeFlow-Desktop-Updater"})
        with urlopen(req, timeout=DL_TIMEOUT) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if total:
                        _set(progress=min(99, int(downloaded * 100 / total)))
        _set(progress=100)
        return True
    except Exception as e:
        logger.warning("[updater] 下载失败: %s", e)
        return False


# ── 替换 & 重启 ────────────────────────────────────────────────────────
def _current_exe() -> Path | None:
    """返回当前运行的 EXE 路径（PyInstaller 打包环境）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def apply_update(new_exe: str) -> tuple[bool, str]:
    """
    用 batch 脚本实现热替换：
    1. 等旧进程退出
    2. 复制新 EXE 覆盖旧 EXE
    3. 启动新 EXE
    4. 删除临时文件和脚本自身
    """
    src = Path(new_exe)
    dst = _current_exe()
    if not dst:
        return False, "非打包环境，不支持自动更新"
    if not src.is_file():
        return False, f"新 EXE 不存在: {src}"

    pid = os.getpid()
    bat = Path(tempfile.mktemp(suffix="_codeflow_update.bat"))
    bat.write_text(
        f"@echo off\r\n"
        f":wait\r\n"
        f"tasklist /fi \"PID eq {pid}\" | find \"{pid}\" >nul 2>&1\r\n"
        f"if not errorlevel 1 (timeout /t 1 /nobreak >nul & goto wait)\r\n"
        f"copy /y \"{src}\" \"{dst}\"\r\n"
        f"start \"\" \"{dst}\"\r\n"
        f"del \"{src}\"\r\n"
        f"del \"%~f0\"\r\n",
        encoding="ascii",
    )
    try:
        import subprocess
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat)],
            creationflags=0x00000008,  # DETACHED_PROCESS
            close_fds=True,
        )
        logger.info("[updater] 替换脚本已启动，准备退出: %s -> %s", src, dst)
        return True, "ok"
    except Exception as e:
        return False, str(e)


# ── 主入口 ────────────────────────────────────────────────────────────
def check_and_download(current_version: str, *, force: bool = False) -> None:
    """
    后台线程入口：检查版本 → 若有新版本则自动下载。
    force=True 时跳过"已是最新"判断（供手动触发）。
    """
    with _lock:
        if _state["status"] in ("checking", "downloading", "ready") and not force:
            return
        _state.update(status="checking", current=current_version,
                      progress=0, error="", new_exe="")

    def _run():
        release = _fetch_latest_release()
        if not release:
            _set(status="error", error="无法连接 GitHub，请检查网络")
            return

        latest = release["version"]
        url    = release["download_url"]
        _set(latest=latest, download_url=url)

        if not force and not is_newer(latest, current_version):
            logger.info("[updater] 已是最新版本 %s", current_version)
            _set(status="no_update")
            return

        logger.info("[updater] 发现新版本 %s（当前 %s），开始下载…", latest, current_version)
        _set(status="downloading")

        tmp = Path(tempfile.mkdtemp()) / ASSET_NAME
        ok = _download(url, tmp)
        if ok:
            logger.info("[updater] 下载完成: %s", tmp)
            _set(status="ready", new_exe=str(tmp))
        else:
            _set(status="error", error="下载失败，请稍后重试")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True, name="updater").start()


def start_background_check(current_version: str, delay_s: float = 15.0) -> None:
    """程序启动后延迟 delay_s 秒再检查，避免影响启动速度。"""
    def _delayed():
        time.sleep(delay_s)
        check_and_download(current_version)
    threading.Thread(target=_delayed, daemon=True, name="updater-init").start()


def quick_check(current_version: str, timeout: float = 5.0) -> bool:
    """
    启动阶段同步快速检查：是否有新版本可用。
    超时或网络失败返回 False（不阻断正常启动）。
    若发现新版本，同时触发后台下载。
    """
    result = [False]
    _set(startup_checking=True, status="startup_checking", current=current_version)

    def _run():
        release = _fetch_latest_release()
        if release and is_newer(release["version"], current_version):
            result[0] = True
            # 顺手触发后台下载
            _set(status="downloading", latest=release["version"],
                 download_url=release["download_url"],
                 current=current_version, progress=0, error="", new_exe="")
            tmp = Path(tempfile.mkdtemp()) / ASSET_NAME
            ok = _download(release["download_url"], tmp)
            if ok:
                _set(status="ready", new_exe=str(tmp), startup_checking=False)
            else:
                _set(status="error", error="下载失败，请稍后重试", startup_checking=False)
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            _set(status="no_update", startup_checking=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    # 超时：下载线程继续跑，但 startup_checking 标记清掉
    if t.is_alive():
        _set(startup_checking=False)
    return result[0]
