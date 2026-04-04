"""
BridgeFlow 本地 Web 面板

基于 Python 内置 http.server + ThreadingMixIn，零额外依赖。
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import secrets
import shutil
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import TYPE_CHECKING
from urllib.parse import urlparse, parse_qs

if TYPE_CHECKING:
    from nudger import Nudger

logger = logging.getLogger("bridgeflow.panel")

PANEL_PORT = 18765
_VERSION = "1.9.6"


def _get_version() -> str:
    return _VERSION


def _get_machine_code() -> str:
    import platform, hashlib
    raw = platform.node() + "-" + str(platform.machine())
    return hashlib.md5(raw.encode()).hexdigest()[:12]

_log_queue: queue.Queue[str] = queue.Queue(maxsize=500)
_nudger_ref: Nudger | None = None
_start_callback = None
_stop_callback = None

TEAM_TEMPLATES = {
    "dev-team": {
        "name": "软件开发团队",
        "name_en": "Software Dev Team",
        "roles": [
            {"code": "PM", "label": "项目经理"},
            {"code": "DEV", "label": "开发工程师"},
            {"code": "QA", "label": "测试工程师"},
            {"code": "OPS", "label": "运维工程师"},
        ],
        "leader": "PM",
    },
    "media-team": {
        "name": "自媒体团队",
        "name_en": "Content Media Team",
        "roles": [
            {"code": "PUBLISHER", "label": "审核发行"},
            {"code": "COLLECTOR", "label": "素材采集"},
            {"code": "WRITER", "label": "拟题提纲"},
            {"code": "EDITOR", "label": "润色编辑"},
        ],
        "leader": "PUBLISHER",
    },
    "mvp-team": {
        "name": "创业MVP团队",
        "name_en": "Startup MVP Team",
        "roles": [
            {"code": "MARKETER", "label": "增长运营"},
            {"code": "RESEARCHER", "label": "市场调研"},
            {"code": "DESIGNER", "label": "产品设计"},
            {"code": "BUILDER", "label": "快速原型"},
        ],
        "leader": "MARKETER",
    },
}


# ─── 工具函数 ─────────────────────────────────────────────

class QueueLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            try:
                _log_queue.put_nowait(msg)
            except queue.Full:
                try:
                    _log_queue.get_nowait()
                except queue.Empty:
                    pass
                _log_queue.put_nowait(msg)
        except Exception:
            pass


def _panel_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "panel"
    return Path(__file__).parent / "panel"


def _project_dir() -> Path | None:
    return _nudger_ref.config.project_dir if _nudger_ref else None


def _agents_dir() -> Path | None:
    return _nudger_ref.config.agents_dir if _nudger_ref else None


def _load_bf_config() -> dict | None:
    ad = _agents_dir()
    if ad:
        cfg = ad / "bridgeflow.json"
        if cfg.exists():
            try:
                return json.loads(cfg.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None


def _save_bf_config(data: dict):
    ad = _agents_dir()
    if ad:
        (ad / "bridgeflow.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _scan_files(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    items = []
    for f in sorted(directory.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = f.stat()
        items.append({
            "filename": f.name,
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "age_minutes": int((time.time() - st.st_mtime) / 60),
        })
    return items


_TASK_RE = re.compile(r'TASK-(\d{8})-(\d{3})-([A-Za-z0-9]+)-to-([A-Za-z0-9]+)\.md', re.IGNORECASE)


def _parse_frontmatter(filepath: Path) -> dict:
    """解析 MD 文件的 YAML frontmatter"""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    front = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            front[k.strip().lower()] = v.strip()
    return front


def _build_pipeline() -> list[dict]:
    ad = _agents_dir()
    if not ad:
        return []

    tasks_dir = ad / "tasks"
    reports_dir = ad / "reports"
    if not tasks_dir.exists():
        return []

    report_map: dict[str, str] = {}
    if reports_dir and reports_dir.exists():
        for f in reports_dir.glob("*.md"):
            report_map[f.name.upper()] = f.name

    pipeline = []
    for f in sorted(tasks_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        m = _TASK_RE.match(f.name)
        if not m:
            continue
        task_id = f"TASK-{m.group(1)}-{m.group(2)}"
        sender = m.group(3)
        recipient = m.group(4)
        age_min = int((time.time() - f.stat().st_mtime) / 60)

        has_report = any(task_id.upper() in rn for rn in report_map)

        front = _parse_frontmatter(f)
        fm_status = front.get("progress", front.get("status", "")).lower()

        if has_report:
            status = "completed"
        elif fm_status in ("completed", "done", "finished"):
            status = "completed"
        elif fm_status in ("in_progress", "working", "executing"):
            status = "in_progress"
        elif fm_status in ("blocked", "failed"):
            status = "blocked"
        elif age_min > 1440:
            status = "expired"
        elif age_min < 10:
            status = "in_progress"
        elif age_min < 30:
            status = "maybe_stuck"
        else:
            status = "timeout"

        pipeline.append({
            "task_id": task_id,
            "filename": f.name,
            "sender": sender,
            "recipient": recipient,
            "age_minutes": age_min,
            "status": status,
            "has_report": has_report,
            "priority": front.get("priority", ""),
            "title": front.get("title", front.get("task_id", task_id)),
        })

    return pipeline[:30]


def _copy_templates(project_dir: Path, team_id: str = "dev-team"):
    if getattr(sys, "frozen", False):
        tpl_base = Path(sys._MEIPASS) / "templates"
    else:
        tpl_base = Path(__file__).parent / "templates"

    if not tpl_base.exists():
        logger.warning("模板目录不存在: %s", tpl_base)
        return

    cursor_dir = project_dir / ".cursor"
    rules_dst = cursor_dir / "rules"
    skills_dst = cursor_dir / "skills" / "file-protocol"
    rules_dst.mkdir(parents=True, exist_ok=True)
    skills_dst.mkdir(parents=True, exist_ok=True)

    rules_src = tpl_base / "rules"
    if rules_src.exists():
        for f in rules_src.glob("*.mdc"):
            shutil.copy2(str(f), str(rules_dst / f.name))

    skill_src = tpl_base / "skills" / "file-protocol"
    if skill_src.exists():
        for f in skill_src.glob("*.md"):
            shutil.copy2(str(f), str(skills_dst / f.name))

    agents_dst = project_dir / "docs" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    agents_src = tpl_base / "agents" / team_id
    if agents_src.exists():
        for f in agents_src.glob("*.md"):
            shutil.copy2(str(f), str(agents_dst / f.name))
        logger.info("已拷贝 %s 角色文档(%d个)到 %s", team_id,
                     len(list(agents_src.glob("*.md"))), agents_dst)

    logger.info("已拷贝规则文件到 %s", cursor_dir)


# ─── HTTP Handler ─────────────────────────────────────────

class PanelHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        routes = {
            "/": lambda: self._serve_file("index.html", "text/html"),
            "/index.html": lambda: self._serve_file("index.html", "text/html"),
            "/qrcode.min.js": lambda: self._serve_file("qrcode.min.js", "application/javascript"),
            "/logo-sm.png": lambda: self._serve_file("logo-sm.png", "image/png"),
            "/logo.png": lambda: self._serve_file("logo.png", "image/png"),
            "/api/debug-panel-dir": lambda: self._json({"panel_dir": str(_panel_dir()), "files": [f.name for f in _panel_dir().iterdir()] if _panel_dir().exists() else []}),
            "/api/status": self._api_status,
            "/api/cursor-state": self._api_cursor_state,
            "/api/preflight": self._api_preflight,
            "/api/teams": self._api_teams,
            "/api/devices": self._api_devices,
            "/api/pipeline": self._api_pipeline,
            "/api/logs": self._api_logs_sse,
            "/api/debug_panel": self._api_debug_panel,
        }

        if path == "/api/files":
            dir_name = params.get("dir", ["tasks"])[0]
            return self._api_files(dir_name)

        if path == "/api/file_content":
            dir_name = params.get("dir", ["tasks"])[0]
            fname = params.get("name", [""])[0]
            return self._api_file_content(dir_name, fname)

        handler = routes.get(path)
        if handler:
            handler()
        else:
            fname = path.lstrip("/")
            fp = _panel_dir() / fname
            logger.debug("静态文件: path=%s fname=%s fp=%s exists=%s", path, fname, fp, fp.exists())
            if fname and fp.is_file():
                self._serve_file(fname, "application/octet-stream")
            else:
                self.send_error(404)

    def do_POST(self):
        routes = {
            "/api/start": self._api_start,
            "/api/stop": self._api_stop,
            "/api/reset": self._api_reset,
            "/api/quit": self._api_quit,
            "/api/setup": self._api_setup,
            "/api/config": self._api_config,
            "/api/regenerate_key": self._api_regenerate_key,
            "/api/unbind": self._api_unbind,
            "/api/change_project": self._api_change_project,
            "/api/copy_templates": self._api_copy_templates,
        }
        handler = routes.get(urlparse(self.path).path)
        if handler:
            handler()
        else:
            self.send_error(404)

    # ─── 静态文件 ──────

    def _serve_file(self, filename: str, content_type: str):
        fp = _panel_dir() / filename
        if not fp.exists():
            self.send_error(500, "面板文件丢失")
            return
        body = fp.read_bytes()
        self.send_response(200)
        ct = content_type
        if filename.endswith(".js"):
            ct = "application/javascript"
        elif filename.endswith(".css"):
            ct = "text/css"
        elif filename.endswith(".png"):
            ct = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            ct = "image/jpeg"
        if "image/" in ct:
            self.send_header("Content-Type", ct)
        else:
            self.send_header("Content-Type", f"{ct}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    # ─── GET API ───────

    def _api_debug_panel(self):
        import sys as _sys
        pd = _panel_dir()
        frozen = getattr(_sys, "frozen", False)
        meipass = getattr(_sys, "_MEIPASS", "N/A")
        files = []
        if pd.exists():
            for f in pd.iterdir():
                files.append({"name": f.name, "size": f.stat().st_size, "is_file": f.is_file()})
        self._json({"panel_dir": str(pd), "exists": pd.exists(), "frozen": frozen,
                     "meipass": str(meipass), "files": files})

    def _api_status(self):
        try:
            status = _nudger_ref.get_status() if _nudger_ref else {"running": False}
        except Exception as e:
            logger.warning("get_status error: %s", e)
            status = {"running": False}
        cfg = _load_bf_config()
        if cfg:
            status["team_name"] = cfg.get("team_name", "")
            status["team"] = cfg.get("team", "")
            status["roles"] = cfg.get("roles", [])
            status["leader"] = cfg.get("leader", "")
            status["room_key"] = cfg.get("room_key", "")
            status["relay_url"] = cfg.get("relay_url", "")
        else:
            pd = _project_dir()
            if pd:
                status["need_setup"] = True
                status["has_project_dir"] = True
                status["project_dir"] = str(pd)
            else:
                status["need_setup"] = True
        status["panel_time"] = datetime.now().strftime("%H:%M:%S")
        status["version"] = _get_version()
        status["machine_code"] = _get_machine_code()
        status["device_id"] = _nudger_ref.config.device_id if _nudger_ref and hasattr(_nudger_ref, 'config') else __import__("platform").node()
        self._json(status)

    def _api_cursor_state(self):
        """OCR 扫描 Cursor 窗口状态"""
        if not _nudger_ref:
            return self._json({"error": "nudger 未启动"})
        try:
            result = _nudger_ref.get_cursor_state()
            self._json(result)
        except Exception as e:
            self._json({"error": str(e)})

    def _api_preflight(self):
        from nudger import find_cursor_window, check_keybindings
        checks = []

        pd = _project_dir()
        checks.append({"name": "项目目录", "ok": pd is not None and pd.exists(),
                        "detail": str(pd) if pd else "未设置",
                        "action": "change_project"})

        ad = _agents_dir()
        dirs_ok = ad and all((ad / d).exists() for d in ["tasks", "reports", "issues", "log"])
        checks.append({"name": "目录结构", "ok": bool(dirs_ok),
                        "detail": "tasks/ reports/ issues/ log/ 就绪" if dirs_ok else "缺少子目录"})

        cfg = _load_bf_config()
        checks.append({"name": "团队配置", "ok": cfg is not None,
                        "detail": cfg.get("team_name", "") if cfg else "未初始化",
                        "action": "change_team"})

        rules_ok = False
        agents_ok = False
        if pd:
            cursor_dir = pd / ".cursor"
            rules_ok = (cursor_dir / "rules" / "bridgeflow-core.mdc").exists() and \
                        (cursor_dir / "rules" / "bridgeflow-patrol.mdc").exists() and \
                        (cursor_dir / "skills" / "file-protocol" / "SKILL.md").exists()
            if ad:
                agents_ok = any(ad.glob("*.md"))
        all_files_ok = rules_ok and agents_ok
        if all_files_ok:
            detail = "rules + skills + 角色文档 已就绪"
        elif rules_ok:
            detail = "rules 就绪，角色文档缺失"
        else:
            detail = "未拷贝到项目"
        checks.append({"name": "角色文件", "ok": all_files_ok,
                        "detail": detail,
                        "action": "copy_templates"})

        win = find_cursor_window()
        checks.append({"name": "Cursor 窗口", "ok": win is not None,
                        "detail": win[1][:60] if win else "未找到 Cursor，请先打开"})

        kb_info = check_keybindings(_nudger_ref.config.hotkeys) if _nudger_ref else {"ok": False, "detail": "Nudger 未启动"}
        if kb_info["ok"]:
            kb_detail = "已绑定: " + ", ".join(f'{b["key"]}→{b["role"]}' for b in kb_info.get("bound", []))
        else:
            missing = kb_info.get("missing", [])
            if missing:
                kb_detail = "需手动绑定: " + " / ".join(f'{m["key"]}→Agent标签{m["role"]}' for m in missing)
                kb_detail += "。在 Cursor 中右键 Agent 标签 → 配置快捷键"
            else:
                kb_detail = kb_info.get("detail", "未配置")
        checks.append({"name": "快捷键", "ok": kb_info["ok"], "detail": kb_detail})

        all_ok = all(c["ok"] for c in checks)
        self._json({"checks": checks, "all_ok": all_ok})

    def _api_files(self, dir_name: str):
        ad = _agents_dir()
        if not ad:
            return self._json({"files": []})
        dir_map = {"tasks": ad / "tasks", "reports": ad / "reports",
                    "issues": ad / "issues", "log": ad / "log"}
        target = dir_map.get(dir_name)
        if not target:
            return self._json({"files": []})
        self._json({"dir": dir_name, "files": _scan_files(target)})

    def _api_file_content(self, dir_name: str, fname: str):
        ad = _agents_dir()
        if not ad or not fname:
            return self._json({"error": "missing params"})
        dir_map = {"tasks": ad / "tasks", "reports": ad / "reports",
                    "issues": ad / "issues", "log": ad / "log"}
        target = dir_map.get(dir_name)
        if not target:
            return self._json({"error": "invalid dir"})
        fp = target / fname
        if not fp.is_file() or not fp.name.endswith(".md"):
            return self._json({"error": "file not found"})
        try:
            content = fp.read_text(encoding="utf-8")
        except Exception as e:
            content = f"读取失败: {e}"
        self._json({"filename": fname, "dir": dir_name, "content": content})

    def _api_teams(self):
        self._json({"teams": TEAM_TEMPLATES})

    def _api_devices(self):
        cfg = _load_bf_config()
        self._json({
            "devices": cfg.get("devices", []) if cfg else [],
            "room_key": cfg.get("room_key", "") if cfg else "",
        })

    def _api_pipeline(self):
        self._json({"pipeline": _build_pipeline()})

    def _api_logs_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                try:
                    msg = _log_queue.get(timeout=2.0)
                    self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    # ─── POST API ──────

    def _api_start(self):
        if _start_callback:
            _start_callback()
            self._json({"ok": True, "message": "巡检已启动"})
        else:
            self._json({"ok": False, "message": "回调未注册"}, 500)

    def _api_stop(self):
        if _stop_callback:
            _stop_callback()
            self._json({"ok": True, "message": "巡检已停止"})
        else:
            self._json({"ok": False, "message": "回调未注册"}, 500)

    def _api_quit(self):
        if _stop_callback:
            try:
                _stop_callback()
            except Exception:
                pass
        self._json({"ok": True, "message": "正在退出"})

        def _shutdown():
            time.sleep(1.0)
            logger.info("面板退出：正在终止进程")
            import os, signal
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                pass
            time.sleep(0.5)
            os._exit(0)
        threading.Thread(target=_shutdown, daemon=True).start()

    def _api_reset(self):
        if _stop_callback:
            _stop_callback()

        from main import save_config, get_config_path
        cfg_path = get_config_path()
        if cfg_path.exists():
            cfg_path.unlink()
            logger.info("已清除本地配置: %s", cfg_path)

        self._json({"ok": True, "message": "已重置，请重新配置项目目录和团队", "need_setup": True})

    def _api_setup(self):
        body = self._read_body()
        team_id = body.get("team", "dev-team")

        if team_id not in TEAM_TEMPLATES:
            return self._json({"ok": False, "message": f"未知团队: {team_id}"}, 400)

        ad = _agents_dir()
        pd = _project_dir()
        if not ad or not pd:
            return self._json({"ok": False, "message": "项目目录未设置"}, 400)

        for sub in ["tasks", "reports", "issues", "log"]:
            (ad / sub).mkdir(parents=True, exist_ok=True)

        tmpl = TEAM_TEMPLATES[team_id]
        room_key = f"bf-{secrets.token_hex(4)}"

        config = {
            "team": team_id,
            "team_name": tmpl["name"],
            "roles": [{"code": r["code"], "label": r["label"]} for r in tmpl["roles"]],
            "leader": tmpl["leader"],
            "room_key": room_key,
            "relay_url": "wss://ai.chedian.cc/bridgeflow/ws/",
            "lang": "zh",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "devices": [],
        }
        _save_bf_config(config)
        _copy_templates(pd, team_id)

        logger.info("团队初始化: %s", tmpl["name"])
        self._json({"ok": True, "message": f"{tmpl['name']} 已创建", "room_key": room_key})

    def _api_config(self):
        body = self._read_body()
        cfg = _load_bf_config() or {}
        for key in ("relay_url", "room_key"):
            if key in body:
                cfg[key] = body[key]
        _save_bf_config(cfg)
        self._json({"ok": True, "message": "配置已保存"})

    def _api_regenerate_key(self):
        cfg = _load_bf_config() or {}
        cfg["room_key"] = f"bf-{secrets.token_hex(4)}"
        cfg["devices"] = []
        _save_bf_config(cfg)
        logger.info("房间密钥已重新生成")
        self._json({"ok": True, "room_key": cfg["room_key"], "message": "密钥已重新生成，所有设备需重新扫码"})

    def _api_unbind(self):
        body = self._read_body()
        device_id = body.get("device_id", "")
        cfg = _load_bf_config() or {}
        devices = cfg.get("devices", [])
        cfg["devices"] = [d for d in devices if d.get("device_id") != device_id]
        _save_bf_config(cfg)
        self._json({"ok": True, "message": f"已解绑: {device_id}"})

    def _api_change_project(self):
        body = self._read_body()
        new_path = body.get("path", "").strip()
        if not new_path:
            return self._json({"ok": False, "message": "路径不能为空"})
        p = Path(new_path)
        if not p.exists() or not p.is_dir():
            return self._json({"ok": False, "message": f"目录不存在: {new_path}"})

        from main import save_config, init_project_dirs
        p = p.resolve()
        init_project_dirs(p)
        save_config({"project_dir": str(p)})

        if _nudger_ref:
            _nudger_ref.config.project_dir = p

        cfg = _load_bf_config()
        tid = cfg.get("team", "dev-team") if cfg else "dev-team"
        _copy_templates(p, tid)
        logger.info("项目目录已切换: %s", p)
        self._json({"ok": True, "message": f"已切换到: {p}", "project_dir": str(p)})

    def _api_copy_templates(self):
        pd = _project_dir()
        if not pd:
            return self._json({"ok": False, "message": "项目目录未设置"})
        cfg = _load_bf_config()
        tid = cfg.get("team", "dev-team") if cfg else "dev-team"
        _copy_templates(pd, tid)
        self._json({"ok": True, "message": "角色文件已拷贝"})


# ─── 启动 ────────────────────────────────────────────────

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_panel(nudger, on_start, on_stop, port: int = PANEL_PORT):
    global _nudger_ref, _start_callback, _stop_callback
    _nudger_ref = nudger
    _start_callback = on_start
    _stop_callback = on_stop

    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger("bridgeflow").addHandler(handler)

    server = ThreadedHTTPServer(("127.0.0.1", port), PanelHandler)
    logger.info("本地面板: http://127.0.0.1:%d", port)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
