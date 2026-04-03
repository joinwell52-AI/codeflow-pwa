"""
BridgeFlow Nudger — Agent 唤醒器核心模块

职责：
1. 监听 docs/agents/tasks/ 和 reports/ 文件变化
2. 从文件名解析收件人角色
3. 用快捷键 Ctrl+Alt+N 切换到对应 Agent tab
4. 用 pyautogui 模拟键盘发送消息唤醒 Agent
5. 通过 WebSocket 连接中继服务器，接收 PWA 指令、推送文件变化
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import pyautogui
import pyperclip
import win32con
import win32gui

logger = logging.getLogger("bridgeflow.nudger")

try:
    import websockets
    HAS_WS = True
except ImportError:
    websockets = None
    HAS_WS = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


# ─── 窗口操作 ─────────────────────────────────────────────

def find_cursor_window() -> tuple[int, str] | None:
    results = []

    def _enum(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        if "cursor" in title.lower() and "chrome" not in title.lower():
            results.append((hwnd, title))

    win32gui.EnumWindows(_enum, None)
    return results[0] if results else None


def focus_window(hwnd: int) -> bool:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return True
    except Exception as e:
        logger.warning("focus_window 失败 hwnd=%s: %s", hwnd, e)
        return False


def switch_and_send(hwnd: int, role: str, message: str,
                    hotkeys: dict[str, tuple], input_offset: tuple[float, float] = (0, 0)) -> bool:
    if role.upper() not in hotkeys:
        logger.warning("角色 %s 没有配置快捷键，跳过", role)
        return False

    if not focus_window(hwnd):
        return False

    try:
        keys = hotkeys[role.upper()]
        pyautogui.hotkey(*keys)
        time.sleep(0.8)

        # Ctrl+L 聚焦 Cursor AI 对话输入框（不用猜坐标）
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)

        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        pyperclip.copy(message)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.1)

        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

        return True
    except Exception as e:
        logger.error("switch_and_send 失败: %s", e)
        return False


# ─── 文件解析 ─────────────────────────────────────────────

_TASK_PATTERN = re.compile(
    r'TASK-(\d{8})-(\d{3})-([A-Za-z0-9]+)-to-([A-Za-z0-9]+)\.md',
    re.IGNORECASE,
)


def parse_recipient(filename: str) -> str | None:
    m = _TASK_PATTERN.search(filename)
    return m.group(4).upper() if m else None


def build_nudge_message(filename: str, directory: str) -> str:
    if "tasks" in directory:
        return f"[BridgeFlow] 新任务: {filename}，请调用 read_task 查看并执行"
    elif "reports" in directory:
        return f"[BridgeFlow] 新报告: {filename}，请审核"
    elif "issues" in directory:
        return f"[BridgeFlow] 新问题: {filename}，请查看"
    return f"[BridgeFlow] 新文件: {filename}"


# ─── 文件监听 ─────────────────────────────────────────────

class FileWatcher:
    def __init__(self, tasks_dir: Path, reports_dir: Path, issues_dir: Path):
        self._dirs = {
            "tasks": tasks_dir,
            "reports": reports_dir,
            "issues": issues_dir,
        }
        self._known: dict[str, set[str]] = {}
        self._first_scan = True

    def scan(self) -> list[tuple[str, str, str]]:
        new_files = []
        for dir_name, dir_path in self._dirs.items():
            if not dir_path.exists():
                continue
            current = {f.name for f in dir_path.glob("*.md")}
            if dir_name not in self._known:
                self._known[dir_name] = set()
            if self._first_scan:
                self._known[dir_name] = current
                continue
            for fname in sorted(current - self._known[dir_name]):
                new_files.append((fname, dir_name, str(dir_path / fname)))
            self._known[dir_name] = current
        self._first_scan = False
        return new_files


# ─── keybindings 自动配置 ─────────────────────────────────

def ensure_keybindings(hotkeys: dict[str, tuple]):
    kb_path = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "keybindings.json"
    if not kb_path.parent.exists():
        logger.warning("Cursor 配置目录不存在: %s", kb_path.parent)
        return False

    existing = []
    if kb_path.exists():
        try:
            raw = kb_path.read_text(encoding="utf-8")
            lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("//")]
            existing = json.loads("\n".join(lines))
        except Exception:
            existing = []

    existing_keys = {item.get("key", "").lower() for item in existing if isinstance(item, dict)}

    sorted_roles = sorted(hotkeys.items(), key=lambda kv: kv[1])
    new_entries = []
    for idx, (role, keys) in enumerate(sorted_roles):
        key_str = "+".join(keys)
        if key_str.lower() in existing_keys:
            continue
        new_entries.append({
            "key": key_str,
            "command": f"workbench.action.openEditorAtIndex{idx}",
            "when": "agentWindowFocus",
        })

    if not new_entries:
        logger.info("keybindings.json 已包含所有 Agent 快捷键")
        return True

    merged = existing + new_entries
    kb_path.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info("已写入 %d 条 Agent 快捷键到 %s", len(new_entries), kb_path)
    return True


# ─── 唤醒器核心 ───────────────────────────────────────────

class TaskTracker:
    """追踪任务生命周期：创建 → 执行中 → 可能卡住 → 超时"""

    STUCK_THRESHOLD = 10 * 60    # 10分钟无回复 → 可能卡住
    TIMEOUT_THRESHOLD = 20 * 60  # 20分钟无回复 → 超时
    AUTO_NUDGE_INTERVAL = 5 * 60 # 自动催促间隔

    def __init__(self, config):
        self.config = config
        self._nudged_at: dict[str, float] = {}  # task_id → 上次催促时间

    def get_stuck_tasks(self) -> list[dict]:
        if not self.config.tasks_dir.exists():
            return []

        report_names = set()
        if self.config.reports_dir.exists():
            for f in self.config.reports_dir.glob("*.md"):
                report_names.add(f.name.upper())

        stuck = []
        now = time.time()
        for f in self.config.tasks_dir.glob("*.md"):
            m = _TASK_PATTERN.match(f.name)
            if not m:
                continue
            task_id = f"TASK-{m.group(1)}-{m.group(2)}"
            recipient = m.group(4).upper()
            has_report = any(task_id.upper() in rn for rn in report_names)
            if has_report:
                continue
            age = now - f.stat().st_mtime
            if age < self.STUCK_THRESHOLD:
                continue

            last_nudge = self._nudged_at.get(task_id, 0)
            need_nudge = (now - last_nudge) >= self.AUTO_NUDGE_INTERVAL

            stuck.append({
                "task_id": task_id,
                "filename": f.name,
                "recipient": recipient,
                "age_seconds": age,
                "status": "timeout" if age >= self.TIMEOUT_THRESHOLD else "maybe_stuck",
                "need_nudge": need_nudge,
            })
        return stuck

    def mark_nudged(self, task_id: str):
        self._nudged_at[task_id] = time.time()


def _save_foreground() -> int | None:
    try:
        return win32gui.GetForegroundWindow()
    except Exception:
        return None


def _restore_foreground(hwnd: int | None):
    if not hwnd:
        return
    try:
        time.sleep(0.3)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass


class Nudger:
    def __init__(self, config, on_event: Callable[[dict], None] | None = None):
        self.config = config
        self.watcher = FileWatcher(config.tasks_dir, config.reports_dir, config.issues_dir)
        self.tracker = TaskTracker(config)
        self._notified: set[str] = set()
        self._last_nudge_time: float = 0
        self._running = False
        self._on_event = on_event or (lambda ev: None)
        self.stats = {"nudge_ok": 0, "nudge_fail": 0, "files_detected": 0, "auto_nudge": 0}
        self._tick_count = 0

    @property
    def running(self) -> bool:
        return self._running

    def check_and_nudge(self) -> list[dict]:
        new_files = self.watcher.scan()
        events = []

        prev_hwnd = _save_foreground()
        did_switch = False

        for filename, dir_name, full_path in new_files:
            self.stats["files_detected"] += 1
            if filename in self._notified:
                continue

            recipient = parse_recipient(filename)
            if not recipient:
                ev = {"action": "created", "path": f"docs/agents/{dir_name}/{filename}",
                      "time": datetime.now().strftime("%H:%M:%S")}
                events.append(ev)
                self._on_event(ev)
                continue

            now = time.time()
            if now - self._last_nudge_time < self.config.nudge_cooldown:
                logger.debug("冷却中，延后唤醒 %s", filename)
                continue

            win = find_cursor_window()
            msg = build_nudge_message(filename, dir_name)
            nudged = False

            if win:
                hwnd, title = win
                logger.info("唤醒 %s ← %s", recipient, filename)
                if switch_and_send(hwnd, recipient, msg,
                                   self.config.hotkeys, self.config.input_offset):
                    self._notified.add(filename)
                    self._last_nudge_time = time.time()
                    self.stats["nudge_ok"] += 1
                    nudged = True
                    did_switch = True
                    logger.info("已发送: %s", msg)
                else:
                    self.stats["nudge_fail"] += 1
                    logger.warning("发送失败: %s", recipient)
            else:
                self.stats["nudge_fail"] += 1
                logger.warning("找不到 Cursor 窗口")

            ev = {
                "action": "nudge",
                "path": f"docs/agents/{dir_name}/{filename}",
                "recipient": recipient,
                "nudged": nudged,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
            events.append(ev)
            self._on_event(ev)

        if did_switch:
            _restore_foreground(prev_hwnd)

        return events

    def auto_nudge_stuck(self) -> list[dict]:
        stuck_list = self.tracker.get_stuck_tasks()
        events = []

        prev_hwnd = _save_foreground()
        did_switch = False

        for item in stuck_list:
            if not item["need_nudge"]:
                continue

            recipient = item["recipient"]
            win = find_cursor_window()
            if not win:
                break

            hwnd, _ = win
            auto_msg = (
                f"[BridgeFlow] 任务 {item['task_id']} 已等待 "
                f"{int(item['age_seconds'] / 60)} 分钟，如有疑问请自行判断，"
                f"继续执行，完成后向主控角色回复。"
            )
            logger.info("自动催促 %s: %s", recipient, item["task_id"])
            if switch_and_send(hwnd, recipient, auto_msg,
                               self.config.hotkeys, self.config.input_offset):
                self.tracker.mark_nudged(item["task_id"])
                self.stats["auto_nudge"] += 1
                did_switch = True
                ev = {
                    "action": "auto_nudge",
                    "task_id": item["task_id"],
                    "recipient": recipient,
                    "age_minutes": int(item["age_seconds"] / 60),
                    "time": datetime.now().strftime("%H:%M:%S"),
                }
                events.append(ev)
                self._on_event(ev)
            time.sleep(self.config.nudge_cooldown)

        if did_switch:
            _restore_foreground(prev_hwnd)

        return events

    def start_loop(self):
        self._running = True
        self._tick_count = 0
        self.check_and_nudge()
        logger.info("唤醒器已启动，监听: %s", self.config.agents_dir)
        try:
            while self._running:
                self.check_and_nudge()
                self._tick_count += 1
                if self._tick_count % 15 == 0:
                    self.auto_nudge_stuck()
                time.sleep(self.config.poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            logger.info("唤醒器已停止")

    def stop(self):
        self._running = False

    def get_status(self) -> dict:
        win = find_cursor_window()
        tasks_count = len(list(self.config.tasks_dir.glob("*.md"))) if self.config.tasks_dir.exists() else 0
        reports_count = len(list(self.config.reports_dir.glob("*.md"))) if self.config.reports_dir.exists() else 0
        issues_count = len(list(self.config.issues_dir.glob("*.md"))) if self.config.issues_dir.exists() else 0

        return {
            "running": self._running,
            "project_dir": str(self.config.project_dir),
            "cursor_found": win is not None,
            "cursor_connected": win is not None,
            "cursor_title": win[1] if win else None,
            "relay_connected": False,
            "tasks_count": tasks_count,
            "reports_count": reports_count,
            "issues_count": issues_count,
            "stats": dict(self.stats),
            "hotkeys": {k: "+".join(v) for k, v in self.config.hotkeys.items()},
        }


# ─── 中继客户端 ───────────────────────────────────────────

async def relay_client(config, nudger: Nudger, stop_event: asyncio.Event | None = None):
    if not HAS_WS or not config.room_key:
        return

    _stop = stop_event or asyncio.Event()

    def _make_msg(event_type: str, payload: dict) -> str:
        return json.dumps({
            "room_key": config.room_key,
            "sender": "Nudger",
            "client_type": "desktop_nudger",
            "event_type": event_type,
            "payload": payload,
        }, ensure_ascii=False)

    while not _stop.is_set():
        try:
            async with websockets.connect(
                config.relay_url, ping_interval=20, ping_timeout=20, max_size=16384,
            ) as ws:
                hello = {
                    "room_key": config.room_key,
                    "sender": "Nudger",
                    "client_type": "desktop_nudger",
                    "event_type": "hello",
                    "payload": {
                        "device_id": config.device_id,
                        "device_name": "BridgeFlow Desktop",
                        "owner_role": "SYSTEM",
                    },
                }
                await ws.send(json.dumps(hello, ensure_ascii=False))
                logger.info("已连接中继: %s", config.relay_url)

                async def _send(event_type: str, payload: dict):
                    try:
                        await ws.send(_make_msg(event_type, payload))
                    except Exception:
                        pass

                async def recv_loop():
                    while not _stop.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        et = str(data.get("event_type", ""))
                        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}

                        if et in ("command_from_admin", "admin_command"):
                            text = str(payload.get("text", payload.get("body", ""))).strip()
                            if text:
                                _handle_admin_command(config, text)

                        elif et == "request_dashboard":
                            await _send("dashboard_state", _build_dashboard(config, nudger))

                        elif et == "start_patrol":
                            _relay_start_patrol(nudger)
                            await _send("patrol_state", _build_patrol_state(nudger))

                        elif et == "stop_patrol":
                            _relay_stop_patrol(nudger)
                            await _send("patrol_state", _build_patrol_state(nudger))

                        elif et == "patrol_status":
                            await _send("patrol_state", _build_patrol_state(nudger))

                        elif et == "request_bind_state":
                            await _send("bind_state", _build_bind_state(config))

                        elif et == "request_bind_code":
                            mobile_id = str(payload.get("mobile_device_id", "")).strip()
                            mobile_name = str(payload.get("mobile_device_name", "")).strip()
                            result = _handle_bind_request(config, mobile_id, mobile_name)
                            await _send("bind_state", result)

                        elif et == "execute_desktop_action":
                            action = str(payload.get("action", "")).strip()
                            result = _handle_desktop_action(action, nudger)
                            await _send("desktop_action_result", result)

                async def poll_and_push():
                    while not _stop.is_set():
                        await asyncio.sleep(config.poll_interval)
                        events = nudger.check_and_nudge()
                        for ev in events:
                            try:
                                await ws.send(_make_msg("file_change", ev))
                            except Exception:
                                break

                recv_task = asyncio.create_task(recv_loop())
                poll_task = asyncio.create_task(poll_and_push())
                done, pending = await asyncio.wait(
                    [recv_task, poll_task], return_when=asyncio.FIRST_COMPLETED,
                )
                for t_task in pending:
                    t_task.cancel()
        except Exception as exc:
            logger.warning("中继断开: %s — 3秒后重连", exc)
            try:
                await asyncio.wait_for(_stop.wait(), timeout=3.0)
                break
            except asyncio.TimeoutError:
                pass


# ─── 中继事件处理函数 ───────────────────────────────────────

def _build_dashboard(config, nudger: Nudger) -> dict:
    """构建 PWA dashboard_state 响应"""
    items = []
    for d in ["tasks", "reports"]:
        p = config.agents_dir / d
        if not p.exists():
            continue
        for f in sorted(p.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                text = ""
            front = {}
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            front[k.strip()] = v.strip()
            items.append({
                "filename": f.name,
                "dir": d,
                "task_id": front.get("task_id", f.stem),
                "sender": front.get("sender", ""),
                "recipient": front.get("recipient", ""),
                "priority": front.get("priority", ""),
                "progress": front.get("progress", "pending"),
                "type": front.get("type", d.rstrip("s")),
                "created_at": front.get("created_at", ""),
                "thread_key": front.get("thread_key", ""),
            })

    status = nudger.get_status()
    tasks_count = status.get("tasks_count", 0)
    reports_count = status.get("reports_count", 0)
    stats = status.get("stats", {})

    return {
        "items": items,
        "stats": {
            "today_tasks": tasks_count,
            "today_replies": reports_count,
            "in_progress_threads": sum(1 for i in items if i.get("progress") in ("pending", "in_progress")),
            "replied_threads": sum(1 for i in items if i.get("type") == "report"),
            "nudge_ok": stats.get("nudge_ok", 0),
            "nudge_fail": stats.get("nudge_fail", 0),
        },
    }


def _build_patrol_state(nudger: Nudger) -> dict:
    return {
        "running": nudger.running,
        "round": nudger._tick_count,
        "log": "",
    }


def _relay_start_patrol(nudger: Nudger):
    """通过中继启动巡检（非阻塞，另起线程）"""
    import threading
    if nudger.running:
        return
    t = threading.Thread(target=nudger.start_loop, daemon=True)
    t.start()
    logger.info("PWA 远程启动巡检")


def _relay_stop_patrol(nudger: Nudger):
    if nudger.running:
        nudger.stop()
        logger.info("PWA 远程停止巡检")


def _build_bind_state(config) -> dict:
    bf_path = config.agents_dir / "bridgeflow.json"
    devices = []
    if bf_path.exists():
        try:
            cfg = json.loads(bf_path.read_text(encoding="utf-8"))
            devices = cfg.get("devices", [])
        except Exception:
            pass
    return {
        "status": "bound" if devices else "unbound",
        "machine_code": config.device_id,
        "devices": devices,
    }


def _handle_bind_request(config, mobile_id: str, mobile_name: str) -> dict:
    bf_path = config.agents_dir / "bridgeflow.json"
    cfg = {}
    if bf_path.exists():
        try:
            cfg = json.loads(bf_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    devices = cfg.get("devices", [])
    existing = [d for d in devices if d.get("device_id") == mobile_id]
    if not existing and mobile_id:
        devices.append({
            "device_id": mobile_id,
            "device_name": mobile_name or mobile_id,
            "bound_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        cfg["devices"] = devices
        bf_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("已绑定设备: %s (%s)", mobile_name, mobile_id)

    return {
        "status": "bound",
        "machine_code": config.device_id,
        "devices": devices,
        "bound_mobile_device_name": mobile_name,
    }


def _handle_desktop_action(action: str, nudger: Nudger) -> dict:
    if action == "focus_cursor":
        win = find_cursor_window()
        if win:
            focus_window(win[0])
            return {"action": action, "ok": True, "message": "Cursor 已聚焦"}
        return {"action": action, "ok": False, "message": "未找到 Cursor 窗口"}
    elif action == "inspect":
        status = nudger.get_status()
        return {"action": action, "ok": True, "message": json.dumps(status, ensure_ascii=False)}
    elif action == "start_work":
        if not nudger.running:
            _relay_start_patrol(nudger)
        return {"action": action, "ok": True, "message": "已启动"}
    elif action == "restart":
        nudger.stop()
        import time as _time
        _time.sleep(1)
        _relay_start_patrol(nudger)
        return {"action": action, "ok": True, "message": "已重启"}
    else:
        return {"action": action, "ok": False, "message": f"未知动作: {action}"}


def _handle_admin_command(config, text: str):
    logger.info("收到 PWA 指令: %s", text[:80])
    config.tasks_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    existing = list(config.tasks_dir.glob(f"TASK-{today}-*.md"))
    seq = len(existing) + 1
    task_id = f"TASK-{today}-{seq:03d}"

    leader = "PM"
    bf_config = config.agents_dir / "bridgeflow.json"
    if bf_config.exists():
        try:
            leader = json.loads(bf_config.read_text(encoding="utf-8")).get("leader", "PM")
        except Exception:
            pass

    filename = f"{task_id}-ADMIN-to-{leader}.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        f"---\ntask_id: {task_id}\nsender: ADMIN\nrecipient: {leader}\n"
        f"created_at: {now}\npriority: normal\ntype: admin_command\nsource: pwa\n---\n\n"
        f"# 管理员指令\n\n{text}\n"
    )
    (config.tasks_dir / filename).write_text(content, encoding="utf-8")
    logger.info("已写入: %s", filename)
