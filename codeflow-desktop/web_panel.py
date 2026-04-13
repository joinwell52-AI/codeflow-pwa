"""

码流（CodeFlow）本地 Web 面板


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

logger = logging.getLogger("codeflow.panel")


PANEL_PORT = 18765  # 默认端口，实际运行时由 get_panel_port() 按项目动态分配


def get_panel_port() -> int:
    """返回固定端口 18765。"""
    return 18765

_VERSION = "2.9.14"


# 面板最后活跃时间（monotonic），用于心跳超时检测

_last_panel_active_ts: float | None = None


def _get_version() -> str:
    try:
        import main as _main
        return getattr(_main, "VERSION", _VERSION)
    except Exception:
        return _VERSION

def get_last_panel_active_ts() -> float | None:

    """返回面板最后一次有请求的 monotonic 时间戳，从未连接返回 None。"""

    return _last_panel_active_ts

def _get_machine_code() -> str:

    import platform, hashlib

    raw = platform.node() + "-" + str(platform.machine())

    return hashlib.md5(raw.encode()).hexdigest()[:12]

_log_queue: queue.Queue[str] = queue.Queue(maxsize=500)

_nudger_ref: Nudger | None = None

# 引导阶段（nudger 未启动时）记录 exe 所在项目目录
_pending_project_dir: Path | None = None

_start_callback = None

_stop_callback = None

_setup_complete_callback = None  # 引导完成后调用，由 main.py 注入


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
    if _nudger_ref:
        return _nudger_ref.config.project_dir
    return _pending_project_dir

def _agents_dir() -> Path | None:
    if _nudger_ref:
        return _nudger_ref.config.agents_dir
    if _pending_project_dir:
        return _pending_project_dir / "docs" / "agents"
    return None

def _team_config_path_read(ad: Path) -> Path | None:

    primary, legacy = ad / "codeflow.json", ad / "bridgeflow.json"

    if primary.exists():

        return primary

    if legacy.exists():

        return legacy

    return None

def _team_config_path_write(ad: Path) -> Path:

    primary, legacy = ad / "codeflow.json", ad / "bridgeflow.json"

    if primary.exists() or not legacy.exists():

        return primary

    return legacy

def _load_bf_config() -> dict | None:

    ad = _agents_dir()

    if not ad:
        # nudger 未就绪时，尝试从 _pending_project_dir 读取
        pd = _pending_project_dir
        if pd:
            ad = pd / "docs" / "agents"

    if not ad:

        return None

    path = _team_config_path_read(ad)

    if path and path.exists():

        try:

            return json.loads(path.read_text(encoding="utf-8"))

        except Exception:

            pass

    return None

def _save_bf_config(data: dict):

    ad = _agents_dir()

    if ad:

        path = _team_config_path_write(ad)

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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

    # 清除旧团队角色文件（只删 .md，保留 tasks/reports/issues/log 子目录和 codeflow.json）

    _KEEP = {"tasks", "reports", "issues", "log", ".codeflow"}

    for f in list(agents_dst.glob("*.md")):

        try:

            f.unlink()

        except Exception:

            pass

    # 清除其他团队子目录下的旧角色文件（如果有残留）

    for sub in agents_dst.iterdir():

        if sub.is_dir() and sub.name not in _KEEP:

            try:

                shutil.rmtree(str(sub))

            except Exception:

                pass

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

        global _last_panel_active_ts

        _last_panel_active_ts = time.monotonic()

        parsed = urlparse(self.path)

        path = parsed.path

        params = parse_qs(parsed.query)

        routes = {

            "/": lambda: self._serve_file("index.html", "text/html"),

            "/index.html": lambda: self._serve_file("index.html", "text/html"),

            "/favicon.ico": lambda: self._serve_file("app.ico", "image/x-icon"),

            "/qrcode.min.js": lambda: self._serve_file("qrcode.min.js", "application/javascript"),

            "/logo-sm.png": lambda: self._serve_file("logo-sm.png", "image/png"),

            "/logo.png": lambda: self._serve_file("logo.png", "image/png"),

            "/api/debug-panel-dir": lambda: self._json({"panel_dir": str(_panel_dir()), "files": [f.name for f in _panel_dir().iterdir()] if _panel_dir().exists() else []}),

            "/api/status": self._api_status,

            "/api/cursor-state": self._api_cursor_state,

            "/api/preflight": self._api_preflight,

            "/api/agent/calibrate_poll": self._api_agent_calibrate_poll,

            "/api/patrol_trace": self._api_patrol_trace,

            "/api/teams": self._api_teams,

            "/api/devices": self._api_devices,

            "/api/pipeline": self._api_pipeline,

            "/api/logs": self._api_logs_sse,

            "/api/debug_panel": self._api_debug_panel,

            "/api/agent/test_all_poll": self._api_agent_test_all_poll,

            "/api/skills/list": self._api_skills_list,
            "/api/skills/repos": self._api_skills_repos,

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

        global _last_panel_active_ts

        _last_panel_active_ts = time.monotonic()

        routes = {

            "/api/start": self._api_start,

            "/api/stop": self._api_stop,

            "/api/reset": self._api_reset,

            "/api/quit": self._api_quit,
            "/api/restart": self._api_restart,

            "/api/setup": self._api_setup,

            "/api/config": self._api_config,

            "/api/regenerate_key": self._api_regenerate_key,

            "/api/unbind": self._api_unbind,

            "/api/change_project": self._api_change_project,

            "/api/copy_templates": self._api_copy_templates,

            "/api/set_cursor_exe": self._api_set_cursor_exe,
            "/api/browse_folder": self._api_browse_folder,

            "/api/agent/calibrate": self._api_agent_calibrate,

            "/api/agent/test_switch": self._api_agent_test_switch,

            "/api/agent/test_all": self._api_agent_test_all,

            "/api/skills/install": self._api_skills_install,
            "/api/skills/download": self._api_skills_download,

            "/api/agent/delete": self._api_agent_delete,

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

        # index.html 动态注入版本号 + 防缓存 meta，彻底规避 Chromium 缓存
        if filename == "index.html":
            try:
                ver = _get_version()
                html = body.decode("utf-8", errors="replace")
                import re as _re
                html = _re.sub(r'PC v[\d.]+', f'PC v{ver}', html)
                # 注入防缓存 meta 和版本检测脚本到 <head>
                cache_meta = (
                    '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">'
                    '<meta http-equiv="Pragma" content="no-cache">'
                    '<meta http-equiv="Expires" content="0">'
                    f'<meta name="app-version" content="{ver}">'
                )
                html = html.replace('<head>', '<head>' + cache_meta, 1)
                body = html.encode("utf-8")
            except Exception:
                pass

        self.send_response(200)

        ct = content_type

        if filename.endswith(".js"):

            ct = "application/javascript"

        elif filename.endswith(".css"):

            ct = "text/css"

        elif filename.endswith(".png"):

            ct = "image/png"

        elif filename.endswith(".ico"):

            ct = "image/x-icon"

        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):

            ct = "image/jpeg"

        if "image/" in ct:

            self.send_header("Content-Type", ct)

        else:

            self.send_header("Content-Type", f"{ct}; charset=utf-8")

        self.send_header("Content-Length", str(len(body)))

        cache_ctrl = "no-cache, no-store, must-revalidate" if ct in ("text/html", "text/javascript", "application/javascript") else "public, max-age=3600"
        self.send_header("Cache-Control", cache_ctrl)

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

        # Cursor 可执行文件路径和检测状态
        _exe_path = ""
        if _nudger_ref and getattr(_nudger_ref.config, "cursor_exe_path", ""):
            _exe_path = _nudger_ref.config.cursor_exe_path
        if not _exe_path:
            try:
                from main import load_saved_config as _lsc3
                _exe_path = _lsc3().get("cursor_exe_path", "")
            except Exception:
                pass
        if not _exe_path:
            try:
                from cursor_embed import default_cursor_exe
                _found = default_cursor_exe()
                if _found:
                    _exe_path = str(_found)
            except Exception:
                pass
        status["cursor_exe_path"] = _exe_path
        status["cursor_found"] = bool(_exe_path)

        # 项目目录
        _pd = _project_dir()
        status["project_dir"] = str(_pd) if _pd else ""

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

            rdir = cursor_dir / "rules"

            has_core = (rdir / "codeflow-core.mdc").exists() or (rdir / "bridgeflow-core.mdc").exists()

            has_patrol = (rdir / "codeflow-patrol.mdc").exists() or (rdir / "bridgeflow-patrol.mdc").exists()

            rules_ok = has_core and has_patrol and (cursor_dir / "skills" / "file-protocol" / "SKILL.md").exists()

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

        t0 = time.perf_counter()

        cfg_pf = _nudger_ref.config if _nudger_ref else None

        win = find_cursor_window(cfg_pf)

        # 兜底：用 cursor_embed 的 win32 枚举再找一次

        if not win:

            try:

                from cursor_embed import _find_cursor_main_hwnd

                import win32gui as _wg

                hwnd = _find_cursor_main_hwnd()

                if hwnd:

                    title = _wg.GetWindowText(hwnd) or "Cursor"

                    win = (hwnd, title)

            except Exception:

                pass

        cursor_probe_ms = int((time.perf_counter() - t0) * 1000)

        cursor_exe_saved = ""

        try:

            from main import load_saved_config as _lsc2

            cursor_exe_saved = _lsc2().get("cursor_exe_path", "")

        except Exception:

            pass

        checks.append({"name": "Cursor 窗口", "ok": win is not None,

                        "detail": win[1][:60] if win else "未找到 Cursor，请先打开（或手动指定路径）",

                        "action": "set_cursor_exe" if not win else "",

                        "cursor_exe": cursor_exe_saved})

        # 从团队配置提取当前角色列表（按序号顺序）

        team_roles: list[str] = []  # ["PUBLISHER", "COLLECTOR", ...]

        agent_name_hint: list[str] = []  # ["01-PUBLISHER", "02-COLLECTOR", ...]

        if cfg:

            team_id = cfg.get("team", cfg.get("team_id", "dev-team"))

            # 优先直接用 codeflow.json 里的 roles，其次查 TEAM_TEMPLATES
            role_defs = cfg.get("roles") or TEAM_TEMPLATES.get(team_id, {}).get("roles", [])

            for i, rd in enumerate(role_defs, 1):

                code = rd.get("code", "").upper()

                if code:

                    team_roles.append(code)

                    agent_name_hint.append(f"{i:02d}-{code}")

            logger.warning("preflight team=%s roles=%s", team_id, team_roles)

        # 若团队配置未就绪，回退到 nudger hotkeys 里的角色

        if not team_roles and _nudger_ref:

            for k in sorted(_nudger_ref.config.hotkeys.keys()):

                team_roles.append(k.upper())

                agent_name_hint.append(k.upper())

        # Agent 映射：只要选了团队就先生成角色列表，再尝试 OCR 补充坐标/标签

        agent_mapping: list[dict] = []

        agent_mapping_ok = False

        ocr_scan_ms: float | None = None

        ocr_active = ""

        map_saved_path: str | None = None

        map_detail = "未执行 OCR 映射"

        # ── Step 1：只要有团队角色，先生成完整映射骨架（加载已保存坐标）──

        if team_roles:

            try:

                from nudger import _AGENT_COORDS as _AC_PRE

            except Exception:

                _AC_PRE = {}

            for i, code in enumerate(team_roles, 1):

                saved_xy = _AC_PRE.get(code.upper())

                agent_mapping.append({

                    "role": code,

                    "seq": i,

                    "expected_label": f"{i:02d}-{code}",

                    "sidebar_label_ocr": "",

                    "mapped": False,

                    "screen_xy": list(saved_xy) if saved_xy else None,

                })

        else:

            map_detail = "请先选择团队（团队配置未就绪）"

        # ── Step 2：尝试 OCR 识别，补充侧栏标签和坐标（失败不影响表格显示）──

        if agent_mapping and _nudger_ref:

            try:

                from nudger import (

                    focus_window,

                    build_preflight_agent_mapping,

                    format_preflight_mapping_detail,

                    save_preflight_agent_map_file,

                    update_agent_coords,

                    _register_ui_labels,

                )

                from cursor_vision import scan as vision_scan, register_roles as cv_register_roles, check_ocr_languages

                cv_register_roles(agent_name_hint)

                # 检查 OCR 语言包，缺失时自动安装并在预检里提示
                try:
                    ocr_lang_check = check_ocr_languages()
                    if ocr_lang_check.get("missing"):
                        missing = ocr_lang_check["missing"]
                        checks.append({
                            "name": "OCR 语言包",
                            "ok": False,
                            "detail": f"缺少 {missing}，已触发后台安装（需管理员权限），安装完成后重新预检即可",
                        })
                    else:
                        checks.append({
                            "name": "OCR 语言包",
                            "ok": True,
                            "detail": f"en={ocr_lang_check['en']} zh={ocr_lang_check['zh']}",
                        })
                except Exception:
                    pass

                if win:

                    focus_window(win[0])

                    time.sleep(0.28)

                    st = vision_scan()

                else:

                    st = None

                ocr_scan_ms = round(float(getattr(st, "scan_ms", 0) or 0), 1) if st else None

                ocr_active = (getattr(st, "agent_role", None) or "").strip() if st else ""

                # 用 OCR 结果更新骨架里已有的行（补充标签和坐标）

                ocr_mapping, _ = build_preflight_agent_mapping(st, team_roles)

                ocr_by_role = {r["role"]: r for r in ocr_mapping}

                for row in agent_mapping:

                    ocr_row = ocr_by_role.get(row["role"])

                    if ocr_row:

                        if ocr_row.get("mapped"):

                            row["mapped"] = True

                        if ocr_row.get("sidebar_label_ocr"):

                            row["sidebar_label_ocr"] = ocr_row["sidebar_label_ocr"]

                        if ocr_row.get("screen_xy") and not row.get("screen_xy"):

                            row["screen_xy"] = ocr_row["screen_xy"]

                update_agent_coords(agent_mapping)

                _register_ui_labels(agent_mapping)

                # ── 有坐标但未 OCR 确认 → 点击验证 ──

                if win:

                    try:

                        from nudger import _click_agent_by_coord, _AGENT_COORDS

                        import re as _re_pf

                        def _sfx_pf(r):

                            return _re_pf.sub(r'^\d+[-\s]*', '', r.upper())

                        for row in agent_mapping:

                            role_code = row.get("role", "")

                            has_coord = bool(row.get("screen_xy")) or bool(_AGENT_COORDS.get(role_code.upper()))

                            if has_coord and not row.get("mapped"):

                                clicked = _click_agent_by_coord(role_code, win[0])

                                if clicked:

                                    time.sleep(0.9)

                                    st2 = vision_scan()

                                    ocr2 = (getattr(st2, "agent_role", "") or "").strip()

                                    if ocr2 and _sfx_pf(ocr2) == _sfx_pf(role_code):

                                        row["mapped"] = True

                                        row["sidebar_label_ocr"] = ocr2

                                        if not row.get("screen_xy"):

                                            xy2 = _AGENT_COORDS.get(role_code.upper())

                                            if xy2:

                                                row["screen_xy"] = xy2

                    except Exception as e:

                        logger.debug("preflight coord verify: %s", e)

                agent_mapping_ok = bool(agent_mapping) and all(r.get("mapped") for r in agent_mapping)

                map_detail = format_preflight_mapping_detail(agent_mapping, ocr_active)

                if pd and agent_mapping and win:

                    map_saved_path = save_preflight_agent_map_file(

                        pd, win[1], ocr_active, agent_mapping

                    )

            except Exception as e:

                logger.warning("preflight agent mapping OCR: %s", e)

                map_detail = f"OCR 扫描异常（坐标记录仍有效）: {e}"[:160]

        elif agent_mapping:

            map_detail = "Nudger 未就绪，仅显示角色列表（可手动定位）"

        checks.append({

            "name": "Agent 映射",

            "ok": agent_mapping_ok,

            "detail": map_detail[:300],

        })

        all_ok = all(c["ok"] for c in checks)

        attempts = 4

        if cfg_pf is not None:

            attempts = max(1, int(getattr(cfg_pf, "find_cursor_max_attempts", 4)))

        self._json({

            "checks": checks,

            "all_ok": all_ok,

            "preflight_meta": {

                "cursor_probe_ms": cursor_probe_ms,

                "find_cursor_attempts": attempts,

                "agent_mapping": agent_mapping,

                "agent_mapping_ok": agent_mapping_ok,

                "ocr_active": ocr_active,

                "ocr_scan_ms": ocr_scan_ms,

                "preflight_map_path": map_saved_path,

                "team_roles": team_roles,

                "agent_name_hint": agent_name_hint,

            },

        })

    def _api_patrol_trace(self):

        from nudger import get_patrol_trace

        params = parse_qs(urlparse(self.path).query)

        lim = 80

        try:

            lim = int(params.get("limit", [80])[0])

        except Exception:

            pass

        self._json({"events": get_patrol_trace(lim)})

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

    def _api_restart(self):
        """保存 cursor_exe_path 后重启程序，重新走完整启动流程。"""
        import sys as _sys, os as _os, subprocess as _sp
        self._json({"ok": True, "message": "正在重启…"})

        def _do_restart():
            time.sleep(0.8)
            exe = _sys.executable
            args = _sys.argv[:]
            logger.info("重启: %s %s", exe, args)
            try:
                _sp.Popen([exe] + args, cwd=_os.path.dirname(exe))
            except Exception as e:
                logger.warning("重启失败: %s", e)
            time.sleep(0.3)
            _os._exit(0)

        threading.Thread(target=_do_restart, daemon=True).start()

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

            "relay_url": "wss://ai.chedian.cc/codeflow/ws/",

            "lang": "zh",

            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            "devices": [],

        }

        _save_bf_config(config)

        _copy_templates(pd, team_id)

        logger.info("团队初始化: %s", tmpl["name"])

        self._json({"ok": True, "message": f"{tmpl['name']} 已创建", "room_key": room_key})

        # 引导完成：延迟 1 秒后退出程序，让用户重启走正常启动流程
        def _exit_after_setup():
            time.sleep(1.0)
            logger.info("引导完成，程序即将退出，请重启以正常启动")
            import os as _os
            _os._exit(0)
        threading.Thread(target=_exit_after_setup, daemon=True, name="setup-exit").start()

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

    def _api_browse_folder(self):
        """弹出文件夹选择框，返回选中的路径。"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askdirectory(title="选择项目文件夹")
            root.destroy()
        except Exception as e:
            return self._json({"ok": False, "message": f"选择失败: {e}"})
        if not path:
            return self._json({"ok": False, "message": "未选择"})
        return self._json({"ok": True, "path": path})

    def _api_set_cursor_exe(self):

        """弹出文件选择框让用户指定 Cursor.exe，保存到全局 config"""

        try:

            import tkinter as tk

            from tkinter import filedialog

            root = tk.Tk()

            root.withdraw()

            root.attributes("-topmost", True)

            path = filedialog.askopenfilename(

                title="选择 Cursor.exe",

                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],

            )

            root.destroy()

        except Exception as e:

            return self._json({"ok": False, "message": f"文件选择失败: {e}"})

        if not path:

            return self._json({"ok": False, "message": "未选择文件"})

        p = Path(path)

        if not p.is_file():

            return self._json({"ok": False, "message": f"文件不存在: {path}"})

        from main import save_config

        save_config({"cursor_exe_path": str(p)})

        if _nudger_ref:

            _nudger_ref.config.cursor_exe_path = str(p)

        logger.info("Cursor.exe 路径已保存: %s", p)

        # 保存后立刻触发嵌入（在后台线程，不阻塞响应）
        def _do_embed_after_save():
            import time as _t
            _t.sleep(0.5)
            try:
                from cursor_embed import embed_panel_after_launch
                from main import VERSION
                _pd = _project_dir()
                _port = get_panel_port()
                _url = f"http://127.0.0.1:{_port}?v={VERSION}&t={int(_t.time())}"
                ok, msg = embed_panel_after_launch(
                    _url,
                    cursor_exe=p,
                    launch_if_no_window=True,
                    project_dir=_pd,
                )
                logger.info("[嵌入] %s: %s", "成功" if ok else "失败", msg)
            except Exception as e:
                logger.warning("[嵌入] 异常: %s", e)
        import threading as _th
        _th.Thread(target=_do_embed_after_save, daemon=True).start()

        self._json({"ok": True, "message": f"已保存: {p.name}", "cursor_exe_path": str(p)})

    # ── Agent 坐标定位 / 实测 / 删除 ────────────────────────────────────


    # 每个 role 一个状态槽：{ role_key: {"status":…, "xy":…, "msg":…} }

    _calibrate_states: dict = {}
    _test_all_state: dict = {}  # {"running": bool, "results": [...], "current": "ROLE"}

    def _calibrate_save_coords(self, role: str, role_key: str, xy: tuple) -> None:

        try:

            from nudger import update_agent_coords, _normalize_role, save_preflight_agent_map_file, _register_ui_labels

            import json as _json

            update_agent_coords([{"role": role_key, "screen_xy": [xy[0], xy[1]]}])

            _register_ui_labels([{"role": role_key, "sidebar_label_ocr": role}])

            pd = _project_dir()

            if pd:

                map_file = pd / "docs" / "agents" / ".codeflow" / "preflight_agent_map.json"

                existing = []

                if map_file.exists():

                    try:

                        existing = _json.loads(map_file.read_text(encoding="utf-8")).get("roles", [])

                    except Exception:

                        pass

                found = False

                for row in existing:

                    if _normalize_role(str(row.get("role", ""))).upper() == role_key:

                        row["screen_xy"] = [xy[0], xy[1]]

                        row["mapped"] = True

                        found = True

                        break

                if not found:

                    existing.append({

                        "role": role_key,

                        "sidebar_label_ocr": role,

                        "mapped": True,

                        "screen_xy": [xy[0], xy[1]],

                    })

                save_preflight_agent_map_file(pd, "", "", existing)

        except Exception as e:

            logger.debug("calibrate save coords: %s", e)

    def _api_agent_calibrate(self):

        """启动坐标监听（立即返回），前端轮询 calibrate_poll 获取结果。"""

        import ctypes, ctypes.wintypes

        from nudger import _normalize_role

        body = self._read_body()

        role = (body.get("role") or "").strip()

        if not role:

            return self._json({"ok": False, "message": "缺少 role 参数"}, 400)

        role_key = _normalize_role(role).upper()

        # 每次点击📍定位都强制重新开始，清掉任何旧状态
        PanelHandler._calibrate_states[role_key] = {"status": "waiting", "xy": None, "msg": ""}

        def _listen():
            """GetAsyncKeyState 轮询左键，捕到立即记录坐标，20s 超时。"""
            import time as _t
            import ctypes as _ct
            import ctypes.wintypes as _wt

            logger.info("[定位] 开始等待鼠标点击，目标: %s", role_key)

            u32 = _ct.windll.user32

            # 等 📍 按钮自身的点击完全松开
            _t.sleep(1.2)
            while u32.GetAsyncKeyState(0x01) & 0x8000:
                _t.sleep(0.02)

            logger.info("[定位] 监听中，请点击目标 Agent…")

            xy = None
            prev = False
            deadline = _t.time() + 20.0

            while _t.time() < deadline:
                pressed = bool(u32.GetAsyncKeyState(0x01) & 0x8000)
                if pressed and not prev:
                    # 按下瞬间记录坐标
                    pt = _wt.POINT()
                    u32.GetCursorPos(_ct.byref(pt))
                    xy = (pt.x, pt.y)
                    logger.warning("[定位] 捕获坐标: (%d, %d)", pt.x, pt.y)
                    break
                prev = pressed
                _t.sleep(0.01)

            if not xy:
                PanelHandler._calibrate_states[role_key] = {
                    "status": "timeout", "xy": None,
                    "msg": "20 秒内未捕获到点击，请重试"
                }
                return

            # 保存坐标，直接完成，不做OCR验证
            self._calibrate_save_coords(role, role_key, xy)
            logger.info("[定位] 坐标已记录 %s → (%d, %d)", role_key, xy[0], xy[1])

            PanelHandler._calibrate_states[role_key] = {
                "status": "done",
                "xy": list(xy),
                "msg": f"已记录 ({xy[0]}, {xy[1]})",
                "verified": True,
            }

        threading.Thread(target=_listen, daemon=True).start()

        self._json({"ok": True, "status": "waiting", "token": role_key})

    def _api_agent_calibrate_poll(self):

        """GET /api/agent/calibrate_poll?role=ROLE 轮询坐标捕捉结果。"""

        from nudger import _normalize_role

        qs = parse_qs(urlparse(self.path).query)

        role_key = _normalize_role((qs.get("role", [""])[0]).strip()).upper()

        if not role_key:

            return self._json({"status": "error", "msg": "缺少 role 参数"}, 400)

        state = PanelHandler._calibrate_states.get(role_key)

        if not state:

            return self._json({"status": "not_started", "xy": None, "msg": "未启动监听"})

        self._json(state)

    def _api_agent_test_switch(self):

        """实际切换到指定 Agent 并返回 OCR 验证结果。"""

        body = self._read_body()

        role = (body.get("role") or "").strip()

        if not role:

            return self._json({"ok": False, "message": "缺少 role 参数"}, 400)

        if not _nudger_ref:

            return self._json({"ok": False, "message": "Nudger 未就绪"}, 400)

        try:

            from nudger import (

                find_cursor_window, focus_window,

                _click_agent_by_coord, _run_command_palette_goto_agent,

                _normalize_role, _hotkey_from_label, _UI_LABELS,

            )

            from cursor_vision import scan as vision_scan

            win = find_cursor_window(_nudger_ref.config)

            if not win:

                return self._json({"ok": False, "message": "未找到 Cursor 窗口"})

            focus_window(win[0])

            time.sleep(0.3)

            import pyautogui
            from cursor_vision import scan as _vs, find_keyword_position as _fkp
            role_key = _normalize_role(role).upper()
            cfg2 = _load_bf_config() or {}
            team_id2 = cfg2.get("team_id", cfg2.get("team", "dev-team"))
            role_defs2 = cfg2.get("roles") or TEAM_TEMPLATES.get(team_id2, {}).get("roles", [])
            idx = next((i+1 for i, rd in enumerate(role_defs2)
                        if rd.get("code","").upper() == role_key), 1)
            label = f"{idx:02d}-{role_key}"

            # 每次实时 OCR 扫侧栏（Agent 可能滚动，坐标随时变）
            pos = None
            st0 = _vs()
            if st0 and st0.found:
                pos = _fkp(st0, label) or _fkp(st0, role_key)

            if not pos:
                return self._json({"ok": False, "message": f"OCR未找到 {label}，请确认侧栏可见"})

            logger.info("[切换] OCR点击 %s → (%d,%d)", label, pos[0], pos[1])
            focus_window(win[0])
            time.sleep(0.3)
            pyautogui.click(pos[0], pos[1])

            time.sleep(1.8)

            st = vision_scan()

            return self._json({"ok": True, "method": f"OCR点击:{label}",

                               "ocr_role": getattr(st, "agent_role", "") or ""})

        except Exception as e:

            logger.warning("test_switch: %s", e)

            return self._json({"ok": False, "message": str(e)[:200]}, 500)

    def _api_agent_test_all(self):
        """后台线程逐个切换 Agent，前端轮询 /api/agent/test_all_poll 获取进度。"""
        if not _nudger_ref:
            return self._json({"ok": False, "message": "Nudger 未就绪"}, 400)

        # 如果已在运行，直接返回当前状态
        if PanelHandler._test_all_state.get("running"):
            return self._json({"ok": True, "status": "running"})

        def _run():
            try:
                import re as _re
                import ctypes as _ct
                import pyautogui
                from nudger import find_cursor_window, _normalize_role, _AGENT_COORDS
                from cursor_vision import scan as _cv_scan, find_keyword_position as _fkp

                _u32 = _ct.windll.user32

                def _sfx(r):
                    return _re.sub(r'^\d+[-\s]*', '', r.upper())

                def _safe_focus(hwnd):
                    try:
                        # IsZoomed 返回非零表示当前最大化，保持最大化；否则用 SW_SHOW(5) 不改变窗口大小
                        if _u32.IsZoomed(hwnd):
                            _u32.ShowWindow(hwnd, 3)   # SW_MAXIMIZE
                        else:
                            _u32.ShowWindow(hwnd, 5)   # SW_SHOW
                        _u32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass

                def _push(label, status, detail=""):
                    PanelHandler._test_all_state["steps"].append(
                        {"label": label, "status": status, "detail": detail}
                    )
                    logger.info("[实测] %s | %s | %s", label, status, detail)

                # 读取角色列表
                cfg = _load_bf_config()
                team_roles = []
                role_index = {}
                if cfg:
                    team_id = cfg.get("team_id", cfg.get("team", "dev-team"))
                    role_defs = cfg.get("roles") or TEAM_TEMPLATES.get(team_id, {}).get("roles", [])
                    for i, rd in enumerate(role_defs, 1):
                        code = rd.get("code", "").upper()
                        if code:
                            team_roles.append(code)
                            role_index[code] = i
                if not team_roles and _nudger_ref:
                    for i, k in enumerate(sorted(_nudger_ref.config.hotkeys.keys()), 1):
                        team_roles.append(k.upper())
                        role_index[k.upper()] = i

                # 初始化状态（在读到角色之后再设置，避免 total=0）
                PanelHandler._test_all_state.update({
                    "running": True, "steps": [], "current": "", "total": len(team_roles)
                })

                if not team_roles:
                    _push("系统", "错误", "未读到角色配置，请先完成预检")
                    PanelHandler._test_all_state["running"] = False
                    return

                win = find_cursor_window(_nudger_ref.config) if _nudger_ref else None
                if not win:
                    _push("系统", "错误", "未找到 Cursor 窗口")
                    PanelHandler._test_all_state["running"] = False
                    return

                for idx, role in enumerate(team_roles, 1):
                    role_key = _normalize_role(role).upper()
                    label = f"{role_index.get(role_key, idx):02d}-{role_key}"
                    PanelHandler._test_all_state["current"] = label

                    # 1. OCR 扫描
                    _push(label, "扫描中", "OCR 识别侧栏 Agent 位置…")
                    _safe_focus(win[0])
                    time.sleep(0.3)
                    try:
                        st0 = _cv_scan()
                    except Exception as e:
                        _push(label, "错误", f"OCR 异常: {e}")
                        continue

                    pos = None
                    if st0 and st0.found:
                        pos = _fkp(st0, label) or _fkp(st0, role_key)
                    if not pos:
                        cached = _AGENT_COORDS.get(role_key)
                        if cached:
                            pos = tuple(cached)
                            _push(label, "扫描中", f"OCR未识别，用预检坐标({pos[0]},{pos[1]})")
                    if not pos:
                        _push(label, "未找到", "未识别到该 Agent，请确认已 Pinned 并重新预检")
                        continue

                    # 2. 点击
                    _push(label, "点击中", f"坐标({pos[0]},{pos[1]})，点击…")
                    _safe_focus(win[0])
                    time.sleep(0.2)
                    try:
                        pyautogui.click(int(pos[0]), int(pos[1]))
                    except Exception as e:
                        _push(label, "错误", f"点击失败: {e}")
                        continue

                    # 3. 验证：与巡检 switch_and_send 相同（is_target_role_active_vision），
                    #    不以「聊天标题」单独为准（正文可能仍是旧任务角色名）
                    from nudger import describe_vision_role_signals, is_target_role_active_vision

                    confirmed = False
                    last_diag = ""

                    for attempt in range(1, 4):          # 最多3次
                        time.sleep(1.5)                  # 等Cursor切换刷新
                        try:
                            st2 = _cv_scan()
                        except Exception as _ve:
                            last_diag = f"OCR异常:{_ve}"
                            continue

                        sig = describe_vision_role_signals(st2)
                        if is_target_role_active_vision(st2, label):
                            confirmed = True
                            _push(label, "成功", f"已切换 → 目标={label} | {sig}")
                            break

                        last_diag = sig
                        _push(label, "重试中",
                              f"第{attempt}次：目标={label} | {sig}")
                        try:
                            _safe_focus(win[0])
                            pyautogui.click(int(pos[0]), int(pos[1]))
                        except Exception:
                            pass

                    if not confirmed:
                        _push(label, "失败",
                              f"目标={label} | {last_diag or 'vision 未判定成功'}")

                PanelHandler._test_all_state["running"] = False
                PanelHandler._test_all_state["current"] = ""
                logger.info("[实测] 全部完成，共 %d 个", len(team_roles))

            except Exception as _e:
                logger.error("[实测] 线程异常: %s", _e, exc_info=True)
                PanelHandler._test_all_state["running"] = False
                PanelHandler._test_all_state["current"] = ""
                PanelHandler._test_all_state.setdefault("steps", []).append(
                    {"label": "系统", "status": "错误", "detail": str(_e)[:200]}
                )

        # 线程启动前先重置状态，避免竞态导致前端轮询到旧/空数据
        PanelHandler._test_all_state.update({
            "running": True, "steps": [], "current": "", "total": 0, "error": ""
        })
        threading.Thread(target=_run, daemon=True).start()
        return self._json({"ok": True, "status": "started"})

    def _api_agent_test_all_poll(self):
        """GET /api/agent/test_all_poll — 轮询实测进度。"""
        s = PanelHandler._test_all_state
        self._json({
            "ok": True,
            "running": s.get("running", False),
            "current": s.get("current", ""),
            "total": s.get("total", 0),
            "steps": s.get("steps", []),
            "error": s.get("error", ""),
        })

    def _api_agent_delete(self):

        """从坐标缓存和 preflight_agent_map.json 中删除指定角色。"""

        body = self._read_body()

        role = (body.get("role") or "").strip()

        if not role:

            return self._json({"ok": False, "message": "缺少 role 参数"}, 400)

        try:

            from nudger import _normalize_role, _AGENT_COORDS, _UI_LABELS

            role_key = _normalize_role(role).upper()

            _AGENT_COORDS.pop(role_key, None)

            _UI_LABELS.pop(role_key, None)

            pd = _project_dir()

            if pd:

                map_file = pd / "docs" / "agents" / ".codeflow" / "preflight_agent_map.json"

                if map_file.exists():

                    data = json.loads(map_file.read_text(encoding="utf-8"))

                    data["roles"] = [

                        r for r in data.get("roles", [])

                        if _normalize_role(str(r.get("role", ""))).upper() != role_key

                    ]

                    map_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            self._json({"ok": True, "role": role})

        except Exception as e:

            self._json({"ok": False, "message": str(e)[:200]}, 500)

    def _api_copy_templates(self):

        pd = _project_dir()

        if not pd:

            return self._json({"ok": False, "message": "项目目录未设置"})

        cfg = _load_bf_config()

        tid = cfg.get("team", "dev-team") if cfg else "dev-team"

        _copy_templates(pd, tid)

        self._json({"ok": True, "message": "角色文件已拷贝"})

    # ─── 外部 Skills ──────────────────────────────────────

    def _api_skills_list(self):
        """GET /api/skills/list — 扫描 external/ 目录，列出所有可安装的外部 Skills。

        兼容两种仓库结构：
        - 技能直接在仓库根目录（external/repo-name/SKILL.md, depth=2）
        - 技能在子目录（external/repo-name/skills/xxx/SKILL.md, depth≥3），每个 xxx 单独列出
        过滤：跳过 external/ 根目录直接的 SKILL.md；跳过名为 template/templates 的目录。
        """
        pd = _project_dir()
        ext_dir = self._get_external_dir()

        skills = []
        seen_paths: set = set()
        installed_dir = (pd / ".cursor" / "skills") if pd else None

        if ext_dir:
            for skill_md in ext_dir.rglob("SKILL.md"):
                skill_dir = skill_md.parent

                # 跳过 external/ 根目录本身（depth=1 的 SKILL.md，理论上不存在但做防守）
                if skill_dir == ext_dir:
                    continue

                # 跳过名为 template / templates 的目录（Anthropic 仓库含示例模板）
                if skill_dir.name.lower() in ("template", "templates"):
                    continue

                # 去重（同一目录可能匹配多次）
                sp = str(skill_dir)
                if sp in seen_paths:
                    continue
                seen_paths.add(sp)

                # 解析 YAML frontmatter 取 name/description
                name = skill_dir.name
                description = ""
                try:
                    txt = skill_md.read_text(encoding="utf-8", errors="ignore")
                    if txt.startswith("---"):
                        fm_end = txt.find("---", 3)
                        if fm_end > 0:
                            fm = txt[3:fm_end]
                            for line in fm.splitlines():
                                if line.lower().startswith("name:"):
                                    name = line.split(":", 1)[1].strip().strip('"\'')
                                elif line.lower().startswith("description:"):
                                    desc_raw = line.split(":", 1)[1].strip()
                                    if desc_raw and desc_raw != "|":
                                        description = desc_raw[:200]
                except Exception:
                    pass

                # 判断是否已安装
                installed = False
                if installed_dir:
                    installed = (installed_dir / name).exists() or (installed_dir / skill_dir.name).exists()

                skills.append({
                    "name": name,
                    "dir_name": skill_dir.name,
                    "path": str(skill_dir),
                    "description": description,
                    "installed": installed,
                })

        skills.sort(key=lambda s: s["name"].lower())
        self._json({"ok": True, "skills": skills, "total": len(skills)})

    def _api_skills_install(self):
        """POST /api/skills/install — 把指定 skill 目录复制到项目 .cursor/skills/<name>/"""
        pd = _project_dir()
        if not pd:
            return self._json({"ok": False, "message": "项目目录未设置"}, 400)

        body = self._read_body()
        skill_path = (body.get("path") or "").strip()
        skill_name = (body.get("name") or "").strip()
        if not skill_path or not skill_name:
            return self._json({"ok": False, "message": "缺少 path 或 name"}, 400)

        src = Path(skill_path)
        if not src.exists() or not src.is_dir():
            return self._json({"ok": False, "message": f"skill 目录不存在: {skill_path}"}, 400)

        dst = pd / ".cursor" / "skills" / skill_name
        try:
            # 确保父目录 .cursor/skills/ 存在（新项目可能没有）
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(src), str(dst))
            logger.info("[skills] 已安装 %s → %s", skill_name, dst)
            self._json({"ok": True, "message": f"已安装：{skill_name}", "dst": str(dst)})
        except Exception as e:
            logger.error("[skills] 安装失败 %s: %s", skill_name, e)
            self._json({"ok": False, "message": f"安装失败: {e}"}, 500)

    # ─── 技能市场：仓库列表 + 下载 ───────────────────────────

    # 预设技能仓库列表
    _SKILL_REPOS = [
        {
            "id": "anthropics-skills",
            "name": "Anthropic 官方技能包",
            "desc": "Canvas设计、PPT、Excel、PDF、前端开发、代码测试等15+专业技能",
            "url": "https://github.com/anthropics/skills.git",
            "dir": "anthropics-skills",
        },
        {
            "id": "Auto-Redbook-Skills",
            "name": "小红书笔记创作",
            "desc": "小红书图文笔记创作、排版、发布全流程技能",
            "url": "https://github.com/comeonzhj/Auto-Redbook-Skills.git",
            "dir": "Auto-Redbook-Skills",
        },
        {
            "id": "smart-illustrator",
            "name": "智能配图 & PPT生成",
            "desc": "文章配图、PPT信息图、封面图自动生成，支持Bento Grid风格",
            "url": "https://github.com/axtonliu/smart-illustrator.git",
            "dir": "smart-illustrator",
        },
        {
            "id": "wechat_article_skills",
            "name": "微信公众号技能包",
            "desc": "公众号文章写作、排版、草稿发布、技术文章创作全套技能",
            "url": "https://github.com/BND-1/wechat_article_skills.git",
            "dir": "wechat_article_skills",
        },
        {
            "id": "wewrite",
            "name": "微信公众号全流程助手",
            "desc": "热点抓取→选题→写作→SEO→视觉AI→排版推送草稿箱",
            "url": "https://github.com/oaker-io/wewrite.git",
            "dir": "wewrite",
        },
    ]

    def _get_external_dir(self):
        """获取 external/ 目录，按优先级查找：
        1. 用户配置的项目目录同级/内部
        2. EXE 所在目录（打包后 sys.executable 的父级）
        3. EXE 所在目录的父级
        4. web_panel.py 源码目录的父级（开发模式）
        """
        import sys as _sys
        pd = _project_dir()
        candidates = []
        if pd:
            candidates += [pd.parent, pd]
        # EXE 打包模式：sys.executable 指向真实 EXE 位置
        exe_dir = Path(_sys.executable).parent
        candidates += [
            exe_dir,           # EXE 同级目录（最常见：D:\newflow-1\）
            exe_dir.parent,    # EXE 上一级
        ]
        # 开发模式：__file__ 指向 web_panel.py 源码
        candidates += [
            Path(__file__).parent.parent,
            Path(__file__).parent,
        ]
        for base in candidates:
            ext = base / "external"
            if ext.exists():
                return ext
        # 默认建在 EXE 同级目录（打包）或源码父级（开发）
        fallback = exe_dir / "external"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    def _parse_readme_repos(self, readme_path: "Path") -> list:
        """解析 external/README.md 中的表格，提取仓库列表。
        表格格式：| 本地目录 | 上游仓库 URL | 用途摘要 |
        """
        repos = []
        try:
            text = readme_path.read_text(encoding="utf-8", errors="ignore")
            in_table = False
            header_done = False
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("|"):
                    if in_table:
                        break
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) < 3:
                    continue
                # 跳过表头分隔行
                if all(set(c.replace("-", "").replace(":", "").replace(" ", "")) <= {""} for c in cells):
                    header_done = True
                    in_table = True
                    continue
                if not header_done:
                    # 表头行
                    header_done = False
                    in_table = True
                    continue
                dir_name = cells[0].strip("`")
                url_cell = cells[1]
                desc = cells[2] if len(cells) > 2 else ""
                # 从 markdown 链接 [text](url) 中提取 URL
                import re as _re
                m = _re.search(r'\(([^)]+github[^)]+)\)', url_cell)
                url = (m.group(1) if m else url_cell.strip()).rstrip("/")
                if not url.endswith(".git"):
                    url += ".git"
                if not dir_name:
                    continue
                repos.append({
                    "id": dir_name,
                    "name": dir_name,
                    "desc": desc[:120],
                    "url": url,
                    "dir": dir_name,
                })
        except Exception:
            pass
        return repos

    def _api_skills_repos(self):
        """GET /api/skills/repos — 返回推荐仓库列表及本地下载状态
        优先从 external/README.md 解析，fallback 到内置列表。
        """
        ext_dir = self._get_external_dir()
        # 优先读 external/README.md
        repos = []
        if ext_dir:
            readme = ext_dir / "README.md"
            if readme.exists():
                repos = self._parse_readme_repos(readme)
        # 用内置列表的友好名称/描述补充 README 解析出的条目
        builtin_map = {r["id"]: r for r in PanelHandler._SKILL_REPOS}
        enriched = []
        for r in repos:
            b = builtin_map.get(r["id"])
            if b:
                enriched.append({**r, "name": b["name"], "desc": b["desc"]})
            else:
                enriched.append(r)
        repos = enriched
        # fallback：内置列表中 README 未覆盖的条目
        existing_ids = {r["id"] for r in repos}
        for repo in PanelHandler._SKILL_REPOS:
            if repo["id"] not in existing_ids:
                repos.append(repo)

        result = []
        for repo in repos:
            local_path = (ext_dir / repo["dir"]) if ext_dir else None
            downloaded = bool(local_path and local_path.exists() and (local_path / ".git").exists())
            result.append({**repo, "downloaded": downloaded,
                            "local_path": str(local_path) if local_path else ""})
        self._json({"ok": True, "repos": result,
                    "external_dir": str(ext_dir) if ext_dir else ""})

    def _api_skills_download(self):
        """POST /api/skills/download — git clone 或 git pull 指定仓库到 external/"""
        body = self._read_body()
        repo_id = (body.get("id") or "").strip()
        repo_cfg = next((r for r in PanelHandler._SKILL_REPOS if r["id"] == repo_id), None)
        if not repo_cfg:
            return self._json({"ok": False, "message": f"未知仓库: {repo_id}"}, 400)

        ext_dir = self._get_external_dir()
        if not ext_dir:
            return self._json({"ok": False, "message": "无法确定 external/ 目录，请先设置项目目录"}, 400)

        local_path = ext_dir / repo_cfg["dir"]
        url = repo_cfg["url"]

        import subprocess as _sp
        # Windows 下隐藏控制台窗口的 flag
        _CREATE_NO_WINDOW = 0x08000000
        _sp_kwargs = {"capture_output": True, "text": True,
                      "creationflags": _CREATE_NO_WINDOW}

        # 先检测 git 是否可用
        try:
            _sp.run(["git", "--version"], timeout=5, **_sp_kwargs)
        except (FileNotFoundError, _sp.TimeoutExpired):
            return self._json({
                "ok": False,
                "no_git": True,
                "message": "未检测到 git，请先安装 Git for Windows：\nhttps://git-scm.com/download/win\n安装后重启本程序即可。"
            }, 400)

        # GitHub 国内镜像代理列表（依次尝试）
        _GH_PROXIES = [
            "",                         # 直连
            "https://ghfast.top/",      # 代理1
            "https://gitclone.com/",    # 代理2
        ]

        def _make_url(proxy: str, orig: str) -> str:
            if not proxy:
                return orig
            # ghfast.top/https://github.com/... 或 gitclone.com/https://github.com/...
            return proxy + orig

        try:
            if local_path.exists() and (local_path / ".git").exists():
                r = _sp.run(
                    ["git", "-C", str(local_path), "pull", "--depth=1"],
                    timeout=120, **_sp_kwargs
                )
                action = "更新"
                if r.returncode != 0:
                    err = (r.stderr or r.stdout or "未知错误")[:500]
                    logger.warning("[skills] %s 失败: %s", action, err)
                    return self._json({"ok": False, "message": f"{action}失败:\n{err}"})
            else:
                action = "下载"
                r = None
                last_err = ""
                for proxy in _GH_PROXIES:
                    clone_url = _make_url(proxy, url)
                    logger.info("[skills] clone 尝试: %s", clone_url)
                    # 清理上次失败的残留
                    if local_path.exists():
                        import shutil as _sh
                        _sh.rmtree(local_path, ignore_errors=True)
                    r = _sp.run(
                        ["git", "clone", "--depth=1", clone_url, str(local_path)],
                        timeout=180, **_sp_kwargs
                    )
                    if r.returncode == 0:
                        break
                    last_err = (r.stderr or r.stdout or "")[:500]
                    logger.warning("[skills] clone 失败(%s): %s", proxy or "直连", last_err)

                if r is None or r.returncode != 0:
                    return self._json({"ok": False,
                                       "message": f"下载失败（已尝试直连和镜像）:\n{last_err}"})

            logger.info("[skills] %s 成功: %s", action, repo_cfg["dir"])
            self._json({"ok": True, "message": f"{action}成功：{repo_cfg['name']}",
                        "local_path": str(local_path)})
        except FileNotFoundError:
            self._json({"ok": False,
                        "message": "未找到 git 命令，请先安装 Git（https://git-scm.com）"}, 500)
        except Exception as e:
            self._json({"ok": False, "message": f"操作失败: {e}"}, 500)

# ─── 启动 ────────────────────────────────────────────────


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):

    daemon_threads = True

    allow_reuse_address = True

def start_panel(nudger, on_start, on_stop, port: int = PANEL_PORT, project_dir: Path | None = None, on_setup_complete=None):

    global _nudger_ref, _start_callback, _stop_callback, _pending_project_dir, _setup_complete_callback
    _setup_complete_callback = on_setup_complete

    _nudger_ref = nudger

    # 引导阶段 nudger=None 时，用 project_dir 让面板能读到项目路径
    if nudger is None and project_dir:
        _pending_project_dir = project_dir
    elif nudger is not None:
        _pending_project_dir = None  # nudger 已就绪，清除临时变量

    _start_callback = on_start

    _stop_callback = on_stop

    handler = QueueLogHandler()

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")

    handler.setFormatter(fmt)

    logging.getLogger("codeflow").addHandler(handler)

    server = ThreadedHTTPServer(("127.0.0.1", port), PanelHandler)

    logger.info("本地面板: http://127.0.0.1:%d", port)

    t = threading.Thread(target=server.serve_forever, daemon=True)

    t.start()

    return server





