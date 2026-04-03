"""
BridgeFlow Desktop — 主入口

双击运行后：
1. 选择项目文件夹（首次运行弹窗，之后记住）
2. 自动配置 Cursor keybindings.json
3. 启动唤醒器（文件监听 + 快捷键发消息）
4. 启动本地面板（http://127.0.0.1:18765）
5. 自动打开浏览器
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

VERSION = "1.0.0"

logger = logging.getLogger("bridgeflow")

_nudger_thread: threading.Thread | None = None
_relay_thread: threading.Thread | None = None
_nudger_instance = None


def setup_logging():
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger("bridgeflow")
    root.setLevel(logging.INFO)

    if sys.stdout:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    log_dir = Path(os.environ.get("APPDATA", ".")) / "BridgeFlow"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "desktop.log", encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)


def get_config_path() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        cfg_dir = Path(appdata) / "BridgeFlow"
    else:
        cfg_dir = Path.home() / ".bridgeflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


def load_saved_config() -> dict:
    cfg_path = get_config_path()
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(data: dict):
    cfg_path = get_config_path()
    existing = load_saved_config()
    existing.update(data)
    cfg_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def select_project_dir() -> Path | None:
    """弹窗让用户选择项目文件夹。"""
    saved = load_saved_config()
    last_dir = saved.get("project_dir", "")

    if last_dir and Path(last_dir).exists():
        agents_dir = Path(last_dir) / "docs" / "agents"
        if agents_dir.exists():
            logger.info("使用上次的项目目录: %s", last_dir)
            return Path(last_dir)

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        dir_path = filedialog.askdirectory(
            title="选择 BridgeFlow 项目文件夹",
            initialdir=last_dir or str(Path.home() / "Desktop"),
        )
        root.destroy()
        if dir_path:
            return Path(dir_path)
    except Exception as e:
        logger.warning("弹窗失败: %s", e)

    if last_dir:
        return Path(last_dir)
    return None


def init_project_dirs(project_dir: Path):
    """确保 docs/agents/ 目录结构存在。"""
    agents_dir = project_dir / "docs" / "agents"
    for sub in ["tasks", "reports", "issues", "log"]:
        (agents_dir / sub).mkdir(parents=True, exist_ok=True)
    logger.info("项目目录已就绪: %s", agents_dir)


def start_nudger():
    """在后台线程启动唤醒器。"""
    global _nudger_thread, _nudger_instance
    if _nudger_instance and _nudger_instance.running:
        logger.info("唤醒器已在运行")
        return

    if _nudger_instance:
        _nudger_instance._running = False
        time.sleep(0.5)

    def _run():
        _nudger_instance.start_loop()

    _nudger_thread = threading.Thread(target=_run, daemon=True, name="nudger")
    _nudger_thread.start()
    logger.info("唤醒器线程已启动")


def start_relay(config):
    """在后台线程启动中继 WebSocket 客户端。"""
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
        _nudger_instance.stop()
        logger.info("唤醒器已停止")


def main():
    setup_logging()
    logger.info("BridgeFlow Desktop v%s", VERSION)

    project_dir = None

    if len(sys.argv) > 1 and sys.argv[1] != "--":
        candidate = Path(sys.argv[1]).resolve()
        if candidate.exists():
            project_dir = candidate

    if not project_dir:
        project_dir = select_project_dir()

    if not project_dir:
        logger.error("未选择项目目录，退出")
        input("按回车键退出...")
        sys.exit(1)

    project_dir = project_dir.resolve()
    save_config({"project_dir": str(project_dir)})
    logger.info("项目目录: %s", project_dir)

    init_project_dirs(project_dir)

    from config import NudgerConfig
    from nudger import Nudger, check_keybindings
    from web_panel import start_panel

    config = NudgerConfig(project_dir=project_dir)

    bf_json = project_dir / "docs" / "agents" / "bridgeflow.json"
    if bf_json.exists():
        try:
            data = json.loads(bf_json.read_text(encoding="utf-8"))
            if "room_key" in data:
                config.room_key = data["room_key"]
            if "relay_url" in data:
                config.relay_url = data["relay_url"]
            if "roles" in data and isinstance(data["roles"], list):
                new_hotkeys = {}
                for idx, role in enumerate(data["roles"]):
                    code = role.get("code", "").upper()
                    if code:
                        new_hotkeys[code] = ("ctrl", "alt", str(idx + 1))
                if new_hotkeys:
                    config.hotkeys = new_hotkeys
            logger.info("已加载团队配置: %s", bf_json)
        except Exception as e:
            logger.warning("团队配置加载失败: %s", e)

    json_cfg = project_dir / "bridgeflow-nudger.json"
    if json_cfg.exists():
        try:
            data = json.loads(json_cfg.read_text(encoding="utf-8"))
            if "hotkeys" in data:
                config.hotkeys = {k.upper(): tuple(v) for k, v in data["hotkeys"].items()}
            if "input_offset" in data:
                config.input_offset = tuple(data["input_offset"])
            logger.info("已加载高级配置: %s", json_cfg)
        except Exception as e:
            logger.warning("高级配置加载失败: %s", e)

    kb_info = check_keybindings(config.hotkeys)
    if kb_info["ok"]:
        logger.info("keybindings.json 已包含所有 Agent 快捷键")
    else:
        logger.warning("Agent 快捷键需要手动绑定: %s", kb_info.get("detail", ""))

    global _nudger_instance
    _nudger_instance = Nudger(config)

    start_panel(_nudger_instance, start_nudger, stop_nudger)

    url = "http://127.0.0.1:18765"
    logger.info("面板地址: %s", url)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    start_nudger()
    start_relay(config)

    logger.info("BridgeFlow Desktop 运行中（Ctrl+C 退出）")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_nudger()
        logger.info("BridgeFlow Desktop 已退出")


if __name__ == "__main__":
    main()
