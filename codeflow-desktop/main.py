"""

CodeFlow Desktop — 主入口


双击运行后：

1. 单实例互斥（防止重复启动）

2. 选择项目文件夹（首次弹窗，之后记住上次）

3. 自动配置 Cursor keybindings.json

4. 启动本地面板 http://127.0.0.1:18765

5. 嵌入 Cursor Simple Browser（失败降级系统浏览器）

6. 面板无连接超时自动退出；Cursor 关闭时同步退出

"""

from __future__ import annotations


import atexit

import json

import logging

import os

import signal

import sys

import threading

import time

import webbrowser

from pathlib import Path


VERSION = "2.11.0"


logger = logging.getLogger("codeflow")


_nudger_thread: threading.Thread | None = None

_relay_thread: threading.Thread | None = None

_nudger_instance = None

_embed_panel_stop = threading.Event()  # 设置后，所有 embed 线程退出循环


# 面板无任何连接时的宽限期（秒）。嵌入模式需要时间加载，给足余量。

_PANEL_NO_EVER_GRACE_S = 300


# ─── 日志 ─────────────────────────────────────────────────────────────


def setup_logging():
    """启动时先把日志写到全局临时目录，项目确定后调用 switch_log_to_project 切换。"""
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")

    root = logging.getLogger("codeflow")

    root.setLevel(logging.INFO)

    if sys.stdout:

        sh = logging.StreamHandler(sys.stdout)

        sh.setFormatter(fmt)

        root.addHandler(sh)

    # 启动阶段临时写到全局目录（项目未知），项目确定后由 switch_log_to_project 切换
    base = Path(os.environ.get("APPDATA", "."))

    log_dir = base / "CodeFlow"

    log_dir.mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(log_dir / "desktop.log", encoding="utf-8")

    fh.setFormatter(fmt)

    root.addHandler(fh)


def switch_log_to_project(project_dir: Path):
    """项目目录确定后，把文件日志切换到 {project_dir}/.codeflow/desktop.log。"""
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")

    log_dir = project_dir / ".codeflow"
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("codeflow")

    # 移除旧的 FileHandler
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            try:
                h.close()
            except Exception:
                pass
            root.removeHandler(h)

    fh = logging.FileHandler(log_dir / "desktop.log", encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    root.info("日志已切换到项目目录: %s", log_dir / "desktop.log")

# ─── 单实例互斥 ───────────────────────────────────────────────────────


_mutex_handle = None


def _try_acquire_single_instance_mutex() -> bool:

    """Windows 命名 Mutex 防止重复启动。返回 True 表示本进程是第一个实例。"""

    global _mutex_handle

    if sys.platform != "win32":

        return True

    try:

        import ctypes

        _mutex_name = "CodeFlowDesktop_18765"
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _mutex_name)

        err = ctypes.windll.kernel32.GetLastError()

        return err != 183  # ERROR_ALREADY_EXISTS

    except Exception:

        return True

def _release_mutex():

    global _mutex_handle

    if _mutex_handle and sys.platform == "win32":

        try:

            import ctypes

            ctypes.windll.kernel32.ReleaseMutex(_mutex_handle)

            ctypes.windll.kernel32.CloseHandle(_mutex_handle)

        except Exception:

            pass

        _mutex_handle = None

# ─── 配置持久化 ──────────────────────────────────────────────────────


def get_config_path() -> Path:

    appdata = os.environ.get("APPDATA", "")

    if appdata:

        cfg_dir = Path(appdata) / "CodeFlow"

        if not cfg_dir.exists():

            legacy = Path(appdata) / "BridgeFlow"

            if legacy.exists():

                cfg_dir = legacy

    else:

        cfg_dir = Path.home() / ".codeflow"

        if not cfg_dir.exists() and (Path.home() / ".bridgeflow").exists():

            cfg_dir = Path.home() / ".bridgeflow"

    cfg_dir.mkdir(parents=True, exist_ok=True)

    return cfg_dir / "config.json"

def load_saved_config() -> dict:
    """全局配置：只包含 project_dir、cursor_exe_path 等跨项目字段。"""
    cfg_path = get_config_path()

    if cfg_path.exists():

        try:

            return json.loads(cfg_path.read_text(encoding="utf-8"))

        except Exception:

            pass

    return {}


def save_config(data: dict):
    """全局配置写入：只允许写 project_dir、cursor_exe_path 这类跨项目字段。"""
    _GLOBAL_KEYS = {"project_dir", "cursor_exe_path"}
    filtered = {k: v for k, v in data.items() if k in _GLOBAL_KEYS}
    if not filtered:
        return

    cfg_path = get_config_path()

    existing = load_saved_config()

    existing.update(filtered)

    cfg_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── 项目级配置（存放在 {project_dir}/.codeflow/config.json）────────────────

_current_project_dir: Path | None = None


def get_project_config_path(project_dir: Path) -> Path:
    cfg_dir = project_dir / ".codeflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


def load_project_config(project_dir: Path) -> dict:
    """读取项目级配置（room_key、relay_url、lang 等）。"""
    cfg_path = get_project_config_path(project_dir)
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_project_config(project_dir: Path, data: dict):
    """写入项目级配置，与全局配置完全隔离。"""
    cfg_path = get_project_config_path(project_dir)
    existing = load_project_config(project_dir)
    existing.update(data)
    cfg_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_project_config_into_nudger_config(project_dir, base_config):
    """引导完成后，把项目配置（codeflow.json）加载到 NudgerConfig 并返回。"""
    from config import NudgerConfig
    cfg = NudgerConfig(project_dir=project_dir)
    # 复制 cursor_exe_path
    if getattr(base_config, "cursor_exe_path", ""):
        cfg.cursor_exe_path = base_config.cursor_exe_path
    # 读取刚写入的 codeflow.json
    agents_dir = project_dir / "docs" / "agents" if project_dir else None
    if agents_dir:
        for fname in ("codeflow.json", "bridgeflow.json"):
            json_cfg = agents_dir / fname
            if json_cfg.exists():
                try:
                    data = json.loads(json_cfg.read_text(encoding="utf-8"))
                    if data.get("room_key"):
                        cfg.room_key = data["room_key"]
                    if data.get("relay_url"):
                        cfg.relay_url = data["relay_url"]
                    if data.get("roles"):
                        cfg.roles = data["roles"]
                    if data.get("leader"):
                        cfg.leader = data["leader"]
                    logger.info("已加载团队配置: %s", json_cfg)
                except Exception as e:
                    logger.warning("团队配置加载失败: %s", e)
                break
    return cfg


# ─── 项目目录 ────────────────────────────────────────────────────────


def select_project_dir() -> Path | None:
    """
    exe 放在项目文件夹根目录里运行，直接以 exe 所在目录作为项目目录。
    开发模式（直接运行 main.py）时，使用脚本所在目录的父目录或当前工作目录。
    """
    if getattr(sys, "frozen", False):
        # 打包后：exe 所在目录就是项目目录
        exe_dir = Path(sys.executable).resolve().parent
        logger.info("打包模式：以 exe 所在目录为项目目录: %s", exe_dir)
        return exe_dir
    else:
        # 开发模式：codeflow-desktop/ 的上级目录（即项目根）
        script_dir = Path(__file__).resolve().parent
        project_dir = script_dir.parent
        logger.info("开发模式：以脚本父目录为项目目录: %s", project_dir)
        return project_dir

def ensure_cursor_exe_path(config) -> None:

    """若 config.cursor_exe_path 未设置，弹窗让用户选 Cursor.exe 并保存。"""

    if getattr(config, "cursor_exe_path", "") and Path(config.cursor_exe_path).is_file():

        return

    # 先自动探测常见路径

    try:

        from cursor_embed import default_cursor_exe

        found = default_cursor_exe()

        if found:

            config.cursor_exe_path = str(found)

            save_config({"cursor_exe_path": str(found)})

            logger.info("自动检测到 Cursor.exe: %s", found)

            return

    except Exception:

        pass

    # 弹窗选择

    try:

        import tkinter as tk

        from tkinter import filedialog

        root = tk.Tk()

        root.withdraw()

        root.attributes("-topmost", True)

        path = filedialog.askopenfilename(

            title="找不到 Cursor.exe，请手动选择",

            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],

        )

        root.destroy()

        if path and Path(path).is_file():

            config.cursor_exe_path = path

            save_config({"cursor_exe_path": path})

            logger.info("用户选择 Cursor.exe: %s", path)

    except Exception as e:

        logger.warning("选择 Cursor.exe 弹窗失败: %s", e)

def init_project_dirs(project_dir: Path):

    agents_dir = project_dir / "docs" / "agents"

    for sub in ["tasks", "reports", "issues", "log"]:

        (agents_dir / sub).mkdir(parents=True, exist_ok=True)

    logger.info("项目目录已就绪: %s", agents_dir)

# ─── Nudger / Relay ──────────────────────────────────────────────────


def _ensure_poll_thread():

    global _nudger_thread

    if _nudger_thread and _nudger_thread.is_alive():

        return

    def _run():

        _nudger_instance.start_loop()

    _nudger_thread = threading.Thread(target=_run, daemon=True, name="nudger")

    _nudger_thread.start()

    logger.info("轮询线程已就绪（间隔 %.1fs，idle 每 %d 轮，stuck 每 %d 轮）",

                _nudger_instance.config.poll_interval,

                _nudger_instance.config.idle_check_every_n,

                _nudger_instance.config.stuck_check_every_n)

    logger.info("后台轮询线程已启动（等待启动巡检指令）")

def start_nudger():

    global _nudger_instance

    if not _nudger_instance:

        return

    _ensure_poll_thread()

    _nudger_instance.start_patrol()

def start_relay(config):

    global _relay_thread

    if not config.room_key:

        logger.info("未配置 room_key，跳过中继连接")

        return

    import asyncio

    from nudger import relay_client

    def _run_relay():

        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        try:

            loop.run_until_complete(relay_client(config, _nudger_instance))

        except Exception as e:

            logger.warning("中继线程异常: %s", e)

        finally:

            loop.close()

    _relay_thread = threading.Thread(target=_run_relay, daemon=True, name="relay")

    _relay_thread.start()

    logger.info("中继线程已启动 → %s", config.relay_url)

def stop_nudger():

    global _nudger_instance

    if _nudger_instance:

        _nudger_instance.stop_patrol()

        logger.info("巡检已停止")

# ─── 退出 ────────────────────────────────────────────────────────────


_quit_flag = threading.Event()

_web_server = None


def shutdown_desktop(reason: str = ""):

    if _quit_flag.is_set():

        return

    _quit_flag.set()

    if reason:

        logger.info("CodeFlow Desktop 正在退出… 原因: %s", reason)

    else:

        logger.info("CodeFlow Desktop 正在退出…")

    stop_nudger()

    try:

        if _web_server:

            logger.info("正在关闭本地面板 HTTP 服务…")

            threading.Thread(target=_web_server.shutdown, daemon=True).start()

    except Exception:

        pass

    _release_mutex()

    # 直接在当前线程强制退出，不依赖 daemon 线程调度
    # os._exit 是进程级，任何线程调用都会立即杀死整个进程
    logging.shutdown()
    os._exit(0)

# ─── 面板心跳守护 ─────────────────────────────────────────────────────


def _start_panel_watchdog(grace_s: int):

    """

    面板无任何连接超过 grace_s 秒时自动退出。

    由 web_panel 的 heartbeat 机制通知最后活跃时间。

    """

    try:

        from web_panel import get_last_panel_active_ts

    except ImportError:

        return  # 旧版 web_panel 无此接口，跳过

    def _watch():

        time.sleep(grace_s)

        while not _quit_flag.is_set():

            ts = get_last_panel_active_ts()

            if ts is None:

                # 从未连接过

                elapsed = time.monotonic()

                if elapsed > grace_s:

                    logger.warning("%d 秒内无任何面板连接，退出进程（无界面不跑自动化）", grace_s)

                    shutdown_desktop("面板无连接超时")

                    return

            else:

                idle = time.monotonic() - ts

                if idle > grace_s:

                    logger.warning("面板 %.0f 秒无心跳，退出进程", idle)

                    shutdown_desktop("面板心跳超时")

                    return

            time.sleep(10)

    threading.Thread(target=_watch, daemon=True, name="panel-watchdog").start()


# ─── Cursor 进程守护 ──────────────────────────────────────────────────


def _start_cursor_watchdog():

    """Cursor 进程消失后，等待 30s 仍未恢复则退出 Desktop。"""

    if sys.platform != "win32":

        return

    def _is_cursor_running() -> bool:
        """用 tasklist 命令检测 cursor.exe 是否在运行，最简单最可靠。"""
        try:
            import subprocess
            out = subprocess.check_output(
                ["tasklist", "/fi", "imagename eq cursor.exe", "/fo", "csv", "/nh"],
                timeout=5, creationflags=0x08000000  # CREATE_NO_WINDOW
            ).decode(errors="replace").strip()
            return "cursor.exe" in out.lower()
        except Exception:
            return False  # 查询失败视为未运行，避免进程残留

    def _watch():

        # 无限等待 Cursor 首次出现（不设超时，Cursor 什么时候起都能监控到）
        logger.info("[Cursor 守护] 等待 Cursor 启动…")
        while not _quit_flag.is_set():
            if _is_cursor_running():
                break
            time.sleep(2)

        if _quit_flag.is_set():
            return

        logger.info("[Cursor 守护] 检测到 Cursor 已运行，开始监控…")

        # Cursor 已出现，监控是否消失
        gone_since = None

        while not _quit_flag.is_set():

            if _is_cursor_running():

                gone_since = None

            else:

                if gone_since is None:

                    gone_since = time.monotonic()

                    logger.info("[Cursor 守护] Cursor 进程消失，5s 后退出…")

                elif time.monotonic() - gone_since > 5:

                    logger.info("[Cursor 守护] Cursor 已关闭超过 5s，CodeFlow Desktop 同步退出")

                    shutdown_desktop("Cursor 已关闭")

                    return

            time.sleep(2)

    threading.Thread(target=_watch, daemon=False, name="cursor-watchdog").start()


# ─── 嵌入 ────────────────────────────────────────────────────────────


def _schedule_embed_panel(url: str, config, *, auto_launch_cursor: bool = True):
    """后台线程：持续尝试嵌入 Cursor Simple Browser，直到成功。

    auto_launch_cursor=False：只嵌入已运行的 Cursor，不自动拉起（引导阶段用，
    用户刚指定完 cursor_exe_path，不应自动打开 Cursor）。
    auto_launch_cursor=True：Cursor 未运行时第 1 次自动拉起（正常启动时用）。
    """

    _embed_panel_stop.clear()

    def _run():
        time.sleep(1.5)
        from cursor_embed import embed_panel_after_launch

        attempt = 0
        while not _embed_panel_stop.is_set():
            attempt += 1
            msg = ""
            try:
                _exe = None
                _exe_path = getattr(config, "cursor_exe_path", "")
                if _exe_path and Path(_exe_path).is_file():
                    _exe = Path(_exe_path)

                # 引导阶段不自动拉起 Cursor；正常启动时第 1 次允许拉起
                _launch = auto_launch_cursor and (attempt == 1)

                ok, msg = embed_panel_after_launch(
                    url,
                    cursor_exe=_exe,
                    launch_if_no_window=_launch,
                    project_dir=getattr(config, "project_dir", None),
                )

                if ok:
                    logger.info("[面板] 已嵌入 Cursor Simple Browser（第%d次）", attempt)
                    return

                logger.warning("[面板] 嵌入第%d次失败: %s", attempt, msg)

            except Exception as exc:
                logger.warning("[面板] 嵌入第%d次异常: %s", attempt, exc)

            if _embed_panel_stop.is_set():
                return

            # 第3次失败且 Cursor 未找到：用系统浏览器打开一次兜底
            if attempt == 3 and not auto_launch_cursor:
                # 引导阶段：面板已通过其他方式打开，不再重复打开浏览器
                pass
            elif attempt == 3:
                logger.warning("[面板] 嵌入失败，用系统浏览器打开: %s", url)
                try:
                    import webbrowser
                    webbrowser.open(url)
                except Exception:
                    pass

            if "未找到 Cursor" in msg or "not found" in msg.lower():
                logger.info("[面板] 未检测到 Cursor，等待用户打开 Cursor 后自动嵌入…")

            # 最多持续尝试120次（10分钟），之后放弃
            if attempt >= 120:
                logger.warning("[面板] 嵌入持续失败，已放弃")
                return

            time.sleep(5)

    threading.Thread(target=_run, daemon=True, name="embed-panel").start()


# ─── 主入口 ──────────────────────────────────────────────────────────


def main():

    global _web_server

    setup_logging()

    logger.info("CodeFlow Desktop v%s", VERSION)

    # ── 启动时清理上次更新残留的 upgrade.bat 和 uptemp/
    try:
        from updater import cleanup_after_upgrade
        cleanup_after_upgrade()
    except Exception:
        pass

    # ── 后台检测并安装缺失的 OCR 语言包（en-US / zh-Hans）
    def _ensure_ocr_langs():
        try:
            from cursor_vision import check_ocr_languages
            r = check_ocr_languages()
            if r.get("installing"):
                logger.info("[OCR] 正在后台安装语言包: %s", r["installing"])
            elif not r.get("missing"):
                logger.info("[OCR] 语言包就绪 (en=%s, zh=%s)", r["en"], r["zh"])
        except Exception as e:
            logger.debug("[OCR] 语言包检测跳过: %s", e)
    threading.Thread(target=_ensure_ocr_langs, daemon=True, name="ocr-lang-check").start()

    # ── 单实例检查

    if not _try_acquire_single_instance_mutex():

        logger.warning("检测到已有实例在运行，本进程退出")

        sys.exit(0)

    atexit.register(_release_mutex)


    # ── 项目目录

    project_dir: Path | None = None

    if len(sys.argv) > 1 and sys.argv[1] != "--":

        candidate = Path(sys.argv[1]).resolve()

        if candidate.exists():

            project_dir = candidate

    if not project_dir:

        project_dir = select_project_dir()

    # ── 检查是否有新版本（超时 5s，有新版则强制进引导页下载更新）
    _has_update = False
    try:
        import updater as _upd
        logger.info("[updater] 检查新版本（最多等待 5s）…")
        _has_update = _upd.quick_check(VERSION, timeout=5.0)
        if _has_update:
            logger.info("[updater] 发现新版本，进入引导页提示更新")
        else:
            logger.info("[updater] 已是最新版本或检测超时，正常启动")
    except Exception as _ue:
        logger.debug("[updater] 版本检查异常: %s", _ue)

    # ── 无项目目录 / 新项目（尚无 codeflow.json）/ 发现新版本：启动面板引导配置

    _agents_dir = project_dir / "docs" / "agents" if project_dir else None
    _has_config = bool(
        _agents_dir and (
            (_agents_dir / "codeflow.json").exists() or
            (_agents_dir / "bridgeflow.json").exists()
        )
    )

    if not project_dir or not _has_config or _has_update:

        if project_dir and not _has_config:
            logger.info("新项目目录（尚无 codeflow.json），启动面板引导配置: %s", project_dir)
            switch_log_to_project(project_dir)
            init_project_dirs(project_dir)
        else:
            logger.info("未找到项目目录，启动面板引导配置")

        from config import NudgerConfig

        from web_panel import start_panel, get_panel_port

        config = NudgerConfig(project_dir=project_dir) if project_dir else NudgerConfig()

        # 引导阶段用专属端口 18766，避免 Cursor Simple Browser 会话恢复自动嵌入引导页
        _port = get_panel_port(setup_mode=True)

        # 引导完成回调：配置已写入，直接退出进程，用户重新启动 CodeFlow
        def _on_setup_complete():
            logger.info("引导完成，配置已保存，进程退出，请重新启动 CodeFlow")
            # 停掉 embed 线程
            _embed_panel_stop.set()
            # 延迟 1 秒让前端收到响应后再退出
            def _exit():
                import time as _t2
                _t2.sleep(1)
                shutdown_desktop("setup_complete")
            threading.Thread(target=_exit, daemon=True, name="setup-exit").start()

        srv = start_panel(None, start_nudger, stop_nudger, port=_port,
                          project_dir=project_dir, on_setup_complete=_on_setup_complete)

        _web_server = srv

        # 加版本号+时间戳，强制 Cursor Simple Browser 每次视为新页面，彻底绕过缓存
        import time as _t
        url = f"http://127.0.0.1:{_port}?v={VERSION}&t={int(_t.time())}"

        logger.info("面板地址: %s", url)

        # 引导阶段：用系统浏览器打开引导页，不做任何 embed 尝试
        try:
            import webbrowser as _wb
            _wb.open(url)
        except Exception:
            pass

        _start_panel_watchdog(_PANEL_NO_EVER_GRACE_S)

        signal.signal(signal.SIGTERM, lambda s, f: shutdown_desktop("SIGTERM"))

        signal.signal(signal.SIGINT,  lambda s, f: shutdown_desktop("SIGINT"))

        logger.info("CodeFlow Desktop 运行中（面板「退出」/ 关标签 / Ctrl+C；"

                    "无面板心跳约 %ds 退出；Cursor 内嵌且已关 Cursor 时也会退出）",

                    _PANEL_NO_EVER_GRACE_S)

        try:

            _quit_flag.wait()

        except KeyboardInterrupt:

            shutdown_desktop("KeyboardInterrupt")

        return

    # ── 有项目目录：正常启动

    project_dir = project_dir.resolve()

    # 日志切换到项目目录
    switch_log_to_project(project_dir)

    logger.info("项目目录: %s", project_dir)

    init_project_dirs(project_dir)

    from config import NudgerConfig

    from nudger import Nudger

    from web_panel import start_panel

    config = NudgerConfig(project_dir=project_dir)


    # 读取团队配置（codeflow.json / 兼容 bridgeflow.json）

    agents = project_dir / "docs" / "agents"

    bf_json = agents / "codeflow.json"

    if not bf_json.exists():

        legacy_bf = agents / "bridgeflow.json"

        if legacy_bf.exists():

            bf_json = legacy_bf

    if bf_json.exists():

        try:

            data = json.loads(bf_json.read_text(encoding="utf-8"))

            if "room_key" in data:

                config.room_key = data["room_key"]

            if "relay_url" in data:

                u = data["relay_url"]

                for old, new in [("/relay/", "/codeflow/ws/"), ("/bridgeflow/ws/", "/codeflow/ws/")]:

                    if old in u:

                        u = u.replace(old, new)

                        data["relay_url"] = u

                        bf_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

                        logger.info("已自动升级 relay_url: %s", u)

                config.relay_url = u

            if "lang" in data:

                config.lang = data["lang"]
                from config import set_lang
                set_lang(data["lang"])

            logger.info("已加载团队配置: %s", bf_json)

        except Exception as e:

            logger.warning("团队配置加载失败: %s", e)

    # 读取高级配置（codeflow-nudger.json / 兼容 bridgeflow-nudger.json）

    json_cfg = project_dir / "codeflow-nudger.json"

    if not json_cfg.exists():

        _legacy = project_dir / "bridgeflow-nudger.json"

        if _legacy.exists():

            json_cfg = _legacy

    if json_cfg.exists():

        try:

            data = json.loads(json_cfg.read_text(encoding="utf-8"))

            for key, attr, cast in [

                ("input_offset",          "input_offset",          tuple),

                ("poll_interval",         "poll_interval",         float),

                ("find_cursor_max_attempts", "find_cursor_max_attempts", int),

                ("find_cursor_retry_delay_s", "find_cursor_retry_delay_s", float),

                ("idle_check_every_n",    "idle_check_every_n",    int),

                ("stuck_check_every_n",   "stuck_check_every_n",   int),

                ("task_stuck_threshold_s",    "task_stuck_threshold_s",    float),

                ("task_timeout_threshold_s",  "task_timeout_threshold_s",  float),

                ("auto_nudge_interval_s",     "auto_nudge_interval_s",     float),

                ("patrol_ping_zh",        "patrol_ping_zh",        str),

                ("patrol_ping_en",        "patrol_ping_en",        str),

                ("stuck_reload_window",   "stuck_reload_window",   bool),

                ("stuck_reload_min_age_s", "stuck_reload_min_age_s", float),

                ("stuck_reload_once_per_task", "stuck_reload_once_per_task", bool),

                ("reload_window_wait_s",  "reload_window_wait_s",  float),

                ("use_file_watcher",      "use_file_watcher",      bool),

                ("cursor_exe_path",       "cursor_exe_path",       str),

            ]:

                if key in data:

                    try:

                        setattr(config, attr, cast(data[key]))

                    except Exception:

                        pass

            logger.info("已加载高级配置: %s", json_cfg)

        except Exception as e:

            logger.warning("高级配置加载失败: %s", e)

    # 读取项目级配置里保存的 cursor_exe_path（兜底读全局）
    proj_saved = load_project_config(project_dir)
    if proj_saved.get("cursor_exe_path") and not getattr(config, "cursor_exe_path", ""):
        config.cursor_exe_path = proj_saved["cursor_exe_path"]
    if not getattr(config, "cursor_exe_path", ""):
        global_saved = load_saved_config()
        if global_saved.get("cursor_exe_path"):
            config.cursor_exe_path = global_saved["cursor_exe_path"]

    global _nudger_instance

    _nudger_instance = Nudger(config)

    _ensure_poll_thread()

    from web_panel import get_panel_port
    _port = get_panel_port()
    srv = start_panel(_nudger_instance, start_nudger, stop_nudger, port=_port)

    _web_server = srv

    import time as _t
    url = f"http://127.0.0.1:{_port}?v={VERSION}&t={int(_t.time())}"

    logger.info("本地面板: http://127.0.0.1:%d", _port)
    logger.info("面板地址: %s", url)

    # Cursor.exe 路径确保

    ensure_cursor_exe_path(config)

    # 嵌入 / 开启浏览器

    _schedule_embed_panel(url, config)

    # 中继

    start_relay(config)

    # 后台检查更新（延迟 15s，避免影响启动速度）
    try:
        import updater as _updater
        _updater.start_background_check(VERSION)
    except Exception:
        pass

    # 守护线程

    _start_panel_watchdog(_PANEL_NO_EVER_GRACE_S)

    _start_cursor_watchdog()

    signal.signal(signal.SIGTERM, lambda s, f: shutdown_desktop("SIGTERM"))

    signal.signal(signal.SIGINT,  lambda s, f: shutdown_desktop("SIGINT"))

    atexit.register(lambda: shutdown_desktop("atexit"))

    logger.info("CodeFlow Desktop 运行中（面板「退出」/ 关标签 / Ctrl+C；"

                "无面板心跳约 %ds 退出；Cursor 内嵌且已关 Cursor 时也会退出）",

                _PANEL_NO_EVER_GRACE_S)

    try:

        _quit_flag.wait()

    except KeyboardInterrupt:

        shutdown_desktop("KeyboardInterrupt")

    logger.info("CodeFlow Desktop 已退出")


if __name__ == "__main__":

    main()




