"""
CodeFlow Desktop 自动更新模块

流程：
1. check_update()  — 请求 GitHub Releases API，比较版本号
2. 发现新版本     — 测速选最快线路（Gitee / GitHub），后台下载
3. 下载完成       — 设置 _update_ready 标志，前端轮询 /api/update/check 获知
4. apply_update() — 写入替换脚本并重启，脚本等旧进程退出后复制新 EXE 覆盖原文件

下载线路：
  - 主线路：Gitee（国内快）
  - 备用线路：GitHub Releases
  - 启动前先用 HEAD 请求测速，响应快的优先
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
from urllib.request import urlopen, Request, build_opener, getproxies, ProxyHandler
from urllib.error import URLError
import socket

logger = logging.getLogger("codeflow.updater")

# ── 配置 ─────────────────────────────────────────────────────────────
GITHUB_REPO    = "joinwell52-AI/codeflow-pwa"
GITEE_REPO     = "joinwell52/cursor-ai"          # Gitee 仓库
ASSET_NAME     = "CodeFlow-Desktop.exe"
API_URL        = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITEE_API_URL  = f"https://gitee.com/api/v5/repos/{GITEE_REPO}/releases/latest"

CHECK_TIMEOUT      = 10   # 秒，版本检查超时
PROBE_TIMEOUT      = 5    # 秒，测速探测超时
DL_CONNECT_TIMEOUT = 15   # 秒，下载连接超时
DL_READ_TIMEOUT    = 30   # 秒，单次 read 超时
DL_TOTAL_LIMIT     = 300  # 秒，整体下载最大时长

# ── 状态 ─────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_state: dict = {
    "status":           "idle",
    "latest":           "",
    "current":          "",
    "progress":         0,
    "error":            "",
    "download_url":     "",
    "new_exe":          "",
    "startup_checking": False,
    "mirror":           "",   # 当前使用的线路名称
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


# ── 网络工具 ──────────────────────────────────────────────────────────
def _make_opener():
    """跟随系统代理（VPN 自动生效）。"""
    proxies = getproxies()
    if proxies:
        logger.debug("[updater] 使用系统代理: %s", proxies)
        return build_opener(ProxyHandler(proxies))
    return build_opener(ProxyHandler({}))


def _probe_ms(url: str) -> float:
    """测量 HEAD 请求响应时间（毫秒），失败返回 999999。"""
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "CodeFlow-Updater-Probe"})
        opener = _make_opener()
        t0 = time.monotonic()
        with opener.open(req, timeout=PROBE_TIMEOUT):
            pass
        return (time.monotonic() - t0) * 1000
    except Exception as e:
        logger.debug("[updater] 探测失败 %s: %s", url, e)
        return 999999.0


# ── 版本检查（GitHub API 为准，Gitee 作下载源）───────────────────────
def _fetch_latest_release() -> dict | None:
    """
    返回 {version, github_url, gitee_url} 或 None。
    版本号以 GitHub 为准（官方发布源），同时构造 Gitee 下载地址。
    """
    try:
        req = Request(API_URL, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeFlow-Desktop-Updater",
        })
        opener = _make_opener()
        with opener.open(req, timeout=CHECK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])
        github_url = next(
            (a["browser_download_url"] for a in assets if a.get("name") == ASSET_NAME),
            None,
        )
        if not (tag and github_url):
            return None

        # Gitee 下载地址按约定构造（与发版脚本保持一致）
        gitee_url = (
            f"https://gitee.com/{GITEE_REPO}/releases/download/{tag}/{ASSET_NAME}"
        )
        return {
            "version":    tag.lstrip("v"),
            "github_url": github_url,
            "gitee_url":  gitee_url,
            "download_url": github_url,  # 兼容旧字段，最终由 _pick_url 覆盖
        }
    except URLError as e:
        logger.debug("[updater] 网络请求失败: %s", e)
    except Exception as e:
        logger.debug("[updater] release 解析失败: %s", e)
    return None


def _pick_url(github_url: str, gitee_url: str) -> tuple[str, str]:
    """
    并发测速，返回 (最快URL, 线路名称)。
    Gitee 响应时间 < GitHub + 500ms 时选 Gitee，否则选 GitHub。
    """
    results: dict[str, float] = {}

    def probe(name, url):
        results[name] = _probe_ms(url)

    threads = [
        threading.Thread(target=probe, args=("Gitee", gitee_url), daemon=True),
        threading.Thread(target=probe, args=("GitHub", github_url), daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=PROBE_TIMEOUT + 1)

    gitee_ms  = results.get("Gitee",  999999.0)
    github_ms = results.get("GitHub", 999999.0)
    logger.info("[updater] 测速 Gitee=%.0fms GitHub=%.0fms", gitee_ms, github_ms)

    if gitee_ms < 999999 and gitee_ms <= github_ms + 500:
        return gitee_url, f"Gitee ({gitee_ms:.0f}ms)"
    if github_ms < 999999:
        return github_url, f"GitHub ({github_ms:.0f}ms)"
    # 都失败，先 Gitee 后 GitHub
    return gitee_url, "Gitee(fallback)"


# ── 下载 ──────────────────────────────────────────────────────────────
def _download(url: str, dest: Path, fallback_url: str | None = None) -> bool:
    """
    流式下载，带连接超时、整体超时、自动重试。
    主 URL 失败时自动切换到 fallback_url。
    """
    urls_to_try = [u for u in [url, fallback_url] if u]

    for attempt, try_url in enumerate(urls_to_try):
        label = "主线路" if attempt == 0 else "备用线路"
        logger.info("[updater] %s 下载: %s", label, try_url)
        if attempt > 0:
            _set(mirror=f"切换到{label}")

        try:
            req = Request(try_url, headers={"User-Agent": "CodeFlow-Desktop-Updater"})
            opener = _make_opener()
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(DL_CONNECT_TIMEOUT)
            try:
                resp = opener.open(req, timeout=DL_CONNECT_TIMEOUT)
            finally:
                socket.setdefaulttimeout(old_timeout)

            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk = 65536
            start_ts = time.monotonic()

            with open(dest, "wb") as f:
                while True:
                    if time.monotonic() - start_ts > DL_TOTAL_LIMIT:
                        resp.close()
                        logger.warning("[updater] 下载超时（%ds）", DL_TOTAL_LIMIT)
                        break
                    socket.setdefaulttimeout(DL_READ_TIMEOUT)
                    try:
                        buf = resp.read(chunk)
                    finally:
                        socket.setdefaulttimeout(old_timeout)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if total:
                        _set(progress=min(99, int(downloaded * 100 / total)))
                    elif downloaded > 0:
                        _set(progress=min(99, int(downloaded * 100 / (40 * 1024 * 1024))))

            resp.close()
            if downloaded > 1024 * 1024:  # 至少 1MB 才算成功
                _set(progress=100)
                logger.info("[updater] 下载完成 %.1fMB via %s", downloaded / 1024 / 1024, label)
                return True
            logger.warning("[updater] %s 下载不完整 (%d bytes)，切换线路", label, downloaded)

        except Exception as e:
            logger.warning("[updater] %s 下载失败: %s", label, e)

    return False


# ── 替换 & 重启 ────────────────────────────────────────────────────────
EXE_NAME = "CodeFlow-Desktop.exe"


def _current_exe() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def cleanup_after_upgrade():
    """启动时调用：清理上次升级残留的 upgrade.bat 和 uptemp 目录。"""
    d = _exe_dir()
    bat = d / "upgrade.bat"
    if bat.is_file():
        try:
            bat.unlink()
            logger.info("[updater] 已清理 upgrade.bat")
        except Exception:
            pass
    uptemp = d / "uptemp"
    if uptemp.is_dir():
        try:
            shutil.rmtree(str(uptemp), ignore_errors=True)
            logger.info("[updater] 已清理 uptemp/")
        except Exception:
            pass


def apply_update(new_exe: str) -> tuple[bool, str]:
    """
    升级流程（参考 taskkill + bat 方案）：
    1. 新 EXE 已下载到临时目录
    2. 生成 upgrade.bat：杀进程 → 等 2s → 删旧 → 复制新 → 启动 → 清理
    3. 执行 bat，bat 会杀掉当前进程并完成替换
    """
    src = Path(new_exe)
    dst = _current_exe()
    if not dst:
        return False, "非打包环境，不支持自动更新"
    if not src.is_file():
        return False, f"新 EXE 不存在: {src}"

    bat_dir = dst.parent
    bat_path = bat_dir / "upgrade.bat"

    old_q = f'"{dst}"'
    new_q = f'"{src}"'
    dir_q = f'"{bat_dir}"'

    script = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        f"cd /d {dir_q}\r\n"
        "echo [CodeFlow] updating...\r\n"
        f"taskkill /f /im {EXE_NAME} >nul 2>&1\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"
        f"if exist {old_q} del /f /q {old_q}\r\n"
        f"if not exist {new_q} (\r\n"
        "    echo [CodeFlow] ERROR: new exe not found!\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        f"copy /y {new_q} {old_q} >nul\r\n"
        "if errorlevel 1 (\r\n"
        "    echo [CodeFlow] ERROR: copy failed!\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        "echo [CodeFlow] update done, launching...\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        f"start \"\" {old_q}\r\n"
        f"del /f /q {new_q} >nul 2>&1\r\n"
        "exit\r\n"
    )

    try:
        bat_path.write_text(script, encoding="utf-8")
        logger.info("[updater] upgrade.bat created: %s", bat_path)

        import subprocess
        subprocess.Popen(
            [str(bat_path)],
            shell=True,
            cwd=str(bat_dir),
        )
        logger.info("[updater] upgrade.bat launched, process will be killed shortly")
        _set(status="done")
        return True, "ok"

    except Exception as e:
        logger.error("[updater] apply_update failed: %s", e)
        return False, str(e)


# ── 主入口 ────────────────────────────────────────────────────────────
def _run_check_and_download(current_version: str, force: bool = False):
    release = _fetch_latest_release()
    if not release:
        _set(status="error", error="无法获取版本信息，请检查网络")
        return

    latest     = release["version"]
    github_url = release["github_url"]
    gitee_url  = release["gitee_url"]
    _set(latest=latest, download_url=github_url)

    if not force and not is_newer(latest, current_version):
        logger.info("[updater] 已是最新版本 %s", current_version)
        _set(status="no_update")
        return

    # 测速选最快线路
    best_url, mirror_name = _pick_url(github_url, gitee_url)
    fallback_url = gitee_url if best_url == github_url else github_url
    logger.info("[updater] 发现新版本 %s，使用 %s 下载", latest, mirror_name)
    _set(status="downloading", mirror=mirror_name, download_url=best_url)

    tmp = Path(tempfile.mkdtemp()) / ASSET_NAME
    ok = _download(best_url, tmp, fallback_url=fallback_url)
    if ok:
        _set(status="ready", new_exe=str(tmp))
    else:
        _set(status="error", error="下载失败，请手动下载或稍后重试")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def check_and_download(current_version: str, *, force: bool = False) -> None:
    with _lock:
        if _state["status"] in ("checking", "downloading", "ready") and not force:
            return
        _state.update(status="checking", current=current_version,
                      progress=0, error="", new_exe="", mirror="")

    threading.Thread(
        target=_run_check_and_download,
        args=(current_version, force),
        daemon=True, name="updater",
    ).start()


def start_background_check(current_version: str, delay_s: float = 15.0) -> None:
    def _delayed():
        time.sleep(delay_s)
        check_and_download(current_version)
    threading.Thread(target=_delayed, daemon=True, name="updater-init").start()


def quick_check(current_version: str, timeout: float = 5.0) -> bool:
    result = [False]
    _set(startup_checking=True, status="startup_checking", current=current_version)

    def _run():
        release = _fetch_latest_release()
        if release and is_newer(release["version"], current_version):
            result[0] = True
            github_url = release["github_url"]
            gitee_url  = release["gitee_url"]
            best_url, mirror_name = _pick_url(github_url, gitee_url)
            fallback_url = gitee_url if best_url == github_url else github_url
            _set(status="downloading", latest=release["version"],
                 download_url=best_url, mirror=mirror_name,
                 current=current_version, progress=0, error="", new_exe="")
            tmp = Path(tempfile.mkdtemp()) / ASSET_NAME
            ok = _download(best_url, tmp, fallback_url=fallback_url)
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
    if t.is_alive():
        _set(startup_checking=False)
    return result[0]
