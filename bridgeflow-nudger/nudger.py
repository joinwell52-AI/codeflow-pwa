"""
BridgeFlow Nudger — Agent 唤醒器核心模块

职责：
1. 监听 docs/agents/tasks/ 和 reports/ 文件变化
2. 从文件名解析收件人角色
3. 用 OCR（cursor_vision）识别 Cursor 窗口状态
4. 用快捷键切换到对应 Agent tab
5. 识别输入框位置 → 精确点击 → 粘贴消息 → 回车
6. 通过 WebSocket 连接中继服务器，接收 PWA 指令、推送文件变化

核心原则：先看再做 — scan() 确认状态 → 操作 → scan() 验证结果
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

try:
    from cursor_vision import (
        scan as vision_scan,
        find_main_cursor_window as vision_find_window,
        click_input_box,
        click_role as vision_click_role,
        find_keyword_position,
        CursorState,
    )
    HAS_VISION = True
except ImportError:
    HAS_VISION = False
    logger.warning("cursor_vision 未加载，回退到盲操作模式")

_relay_connected = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# 角色名标准化映射：OCR 可能识别出的变体 → 标准名
_ROLE_ALIASES = {
    "I-PM": "PM", "1-PM": "PM",
    "2-DEV": "DEV", "I-DEV": "DEV",
    "3-QA": "QA", "I-QA": "QA",
    "4-OPS": "OPS", "I-OPS": "OPS",
}


# ─── 窗口操作 ─────────────────────────────────────────────

def find_cursor_window() -> tuple[int, str] | None:
    if HAS_VISION:
        win = vision_find_window()
        if win:
            return (win.hwnd, win.title)
        return None

    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    results = []

    def _get_process_name(hwnd) -> str:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x0410, False, pid.value)
        if not handle:
            return ""
        try:
            buf = (ctypes.c_wchar * 260)()
            psapi.GetModuleFileNameExW(handle, None, buf, 260)
            return buf.value.lower()
        except Exception:
            return ""
        finally:
            kernel32.CloseHandle(handle)

    def _enum(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        exe_path = _get_process_name(hwnd)
        if exe_path.endswith("cursor.exe"):
            results.append((hwnd, title))

    win32gui.EnumWindows(_enum, None)
    if not results:
        return None
    for hwnd, title in results:
        if " - Cursor" in title:
            return (hwnd, title)
    return results[0]


def focus_window(hwnd: int) -> bool:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
        fg = user32.GetForegroundWindow()
        fg_tid = user32.GetWindowThreadProcessId(fg, None)
        cur_tid = user32.GetWindowThreadProcessId(hwnd, None)
        if fg_tid != cur_tid:
            user32.AttachThreadInput(fg_tid, cur_tid, True)
        user32.BringWindowToTop(hwnd)
        user32.ShowWindow(hwnd, 5)
        VK_ALT = 0x12
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_ALT, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(VK_ALT, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        if fg_tid != cur_tid:
            user32.AttachThreadInput(fg_tid, cur_tid, False)
        time.sleep(0.3)
        return True
    except Exception as e:
        logger.warning("focus_window 失败 hwnd=%s: %s", hwnd, e)
        return False


def _resolve_role(role: str, hotkeys: dict[str, tuple]) -> str | None:
    key = role.upper()
    if key in hotkeys:
        return key
    stripped = re.sub(r'\d+$', '', key)
    if stripped and stripped in hotkeys:
        return stripped
    return None


def _normalize_role(ocr_role: str) -> str:
    """OCR 识别的角色名 → 标准快捷键角色名"""
    upper = ocr_role.upper()
    return _ROLE_ALIASES.get(upper, upper)


def _is_role_active(state: 'CursorState', target_role: str) -> bool:
    """判断目标角色是否已激活（在 Tab 栏第一个或 agent_role 匹配）"""
    if not state or not state.found:
        return False
    target_std = _normalize_role(target_role)
    if state.agent_role:
        current_std = _normalize_role(state.agent_role)
        if current_std == target_std:
            return True
    return False


# ─── 核心操作：看→判断→操作→验证 ─────────────────────────

def switch_and_send(hwnd: int, role: str, message: str,
                    hotkeys: dict[str, tuple],
                    input_offset: tuple[float, float] = (0, 0)) -> bool:
    resolved = _resolve_role(role, hotkeys)
    if not resolved:
        logger.warning("角色 %s 没有配置快捷键，跳过", role)
        return False

    if not focus_window(hwnd):
        return False

    if HAS_VISION:
        return _switch_and_send_with_vision(hwnd, role, resolved, message, hotkeys)
    else:
        return _switch_and_send_blind(hwnd, resolved, message, hotkeys)


def _switch_and_send_blind(hwnd: int, resolved: str, message: str,
                           hotkeys: dict[str, tuple]) -> bool:
    """回退模式：无 OCR，盲按快捷键"""
    try:
        keys = hotkeys[resolved]
        pyautogui.hotkey(*keys)
        time.sleep(0.8)

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
        logger.error("blind switch_and_send 失败: %s", e)
        return False


def _switch_and_send_with_vision(hwnd: int, role: str, resolved: str,
                                 message: str,
                                 hotkeys: dict[str, tuple]) -> bool:
    """
    快捷键执行 + 视觉验证，每步都确认。

    流程：看 → 快捷键切换 → 看（验证） → 快捷键打开面板 → 看（找输入框）
         → 点击输入框 → 粘贴发送 → 看（最终确认）
    """
    MAX_RETRY = 2

    try:
        # ── Step 1: 先看一眼当前状态 ──
        state = vision_scan()
        if not state.found:
            logger.warning("vision: Cursor 窗口不可见，放弃发送")
            return False

        logger.info("vision[看] 当前角色=%s 目标=%s 全部=%s 忙碌=%s",
                     state.agent_role, role, state.all_roles, state.is_busy)

        # ── Step 2: 快捷键切换角色 ──
        if _is_role_active(state, role):
            logger.info("vision[看] 角色已是 %s，无需切换", state.agent_role)
        else:
            switched_ok = False
            for attempt in range(MAX_RETRY):
                # 动作：按快捷键
                keys = hotkeys.get(resolved)
                if keys:
                    logger.info("vision[按] Ctrl+Alt+%s 切换到 %s (第%d次)",
                                keys[-1], resolved, attempt + 1)
                    pyautogui.hotkey(*keys)
                    time.sleep(1.0)

                # 验证：看一眼确认
                state = vision_scan()
                if state.found and _is_role_active(state, role):
                    logger.info("vision[看] 切换成功 → %s", state.agent_role)
                    switched_ok = True
                    break

                # 快捷键没切成功 → 尝试点击角色名兜底
                logger.info("vision[看] 快捷键未生效(当前=%s)，尝试点击",
                            state.agent_role)
                role_variants = [role.upper()]
                stripped = re.sub(r'\d+$', '', role.upper())
                for known in _ROLE_ALIASES:
                    if _ROLE_ALIASES[known] == stripped:
                        role_variants.append(known)
                for rv in role_variants:
                    if vision_click_role(state, rv):
                        logger.info("vision[点] 点击角色 %s", rv)
                        break
                time.sleep(1.0)

                # 再验证
                state = vision_scan()
                if state.found and _is_role_active(state, role):
                    logger.info("vision[看] 点击切换成功 → %s", state.agent_role)
                    switched_ok = True
                    break

            if not switched_ok:
                logger.warning("vision: %d次切换均失败！目标=%s 当前=%s，放弃",
                               MAX_RETRY, role, state.agent_role)
                return False

        # ── Step 3: 快捷键打开面板 + 视觉确认输入框 ──
        if not state.chat_panel_open or not state.input_box:
            logger.info("vision[按] Ctrl+L 打开聊天面板")
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.8)
            state = vision_scan()

        if not state.input_box:
            logger.warning("vision[看] 找不到输入框，放弃发送")
            return False

        # ── Step 4: 发送前最终确认角色 ──
        if not _is_role_active(state, role):
            logger.warning("vision[看] 最终确认失败！目标=%s 当前=%s，放弃",
                           role, state.agent_role)
            return False

        # ── Step 5: 点击输入框 ──
        logger.info("vision[点] 输入框 (%d,%d)",
                     int(state.input_box.cx), int(state.input_box.cy))
        click_input_box(state)
        time.sleep(0.3)

        # ── Step 6: 粘贴消息并发送 ──
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

        logger.info("vision[发] 消息已发送到 %s: %s", role, message[:50])
        return True

    except Exception as e:
        logger.error("vision switch_and_send 异常: %s", e)
        return False


# ─── 文件解析 ─────────────────────────────────────────────

_TASK_PATTERN = re.compile(
    r'TASK-(\d{8})-(\d{3})-([A-Za-z0-9]+)-to-([A-Za-z0-9]+)\.md',
    re.IGNORECASE,
)


def parse_recipient(filename: str) -> str | None:
    m = _TASK_PATTERN.search(filename)
    return m.group(4).upper() if m else None


# ─── 情景对话模板 ─────────────────────────────────────────

_MSG_TEMPLATES = {
    "zh": {
        "first_hello": "开始工作",
        "new_task": "新任务到达: {filename}，请读取任务单并执行",
        "new_report": "新报告到达: {filename}，请审核并回复",
        "new_issue": "新问题: {filename}，请查看并处理",
        "new_file": "新文件: {filename}",
        "remind": "催办: {filename} 已等待 {minutes} 分钟，请尽快处理",
        "kick": "继续",
    },
    "en": {
        "first_hello": "Start working",
        "new_task": "New task: {filename}, please read and execute",
        "new_report": "New report: {filename}, please review",
        "new_issue": "New issue: {filename}, please check",
        "new_file": "New file: {filename}",
        "remind": "Reminder: {filename} waiting {minutes} min, please act",
        "kick": "Continue",
    },
}

# Agent 等待确认的关键词 —— OCR 在聊天区域看到这些就判定"卡住了"
_WAITING_KEYWORDS_ZH = [
    "要我继续", "是否继续", "如果你要我继续", "请确认",
    "下一步就直接", "你确认", "要继续吗", "是否执行",
    "请指示", "等待指令", "等你确认", "需要你确认",
    "是否处理", "要不要", "是否开始",
]
_WAITING_KEYWORDS_EN = [
    "shall i continue", "should i proceed", "do you want me to",
    "please confirm", "waiting for", "let me know",
]

_greeted_roles: set[str] = set()

# ADMIN 是人类操作员，不自动催办 Cursor；其他角色都是 Agent
_NO_NUDGE_RECIPIENTS = frozenset({"ADMIN01", "ADMIN"})


def build_nudge_message(filename: str, directory: str, recipient: str = "",
                        lang: str = "zh", minutes: int = 0) -> str:
    role_code = re.sub(r'\d+$', '', recipient.upper()) if recipient else ""
    _ROLE_TO_FILE = {
        "PM": "docs/agents/PM-01.md",
        "DEV": "docs/agents/DEV-01.md",
        "OPS": "docs/agents/OPS-01.md",
        "QA": "docs/agents/QA-01.md",
    }
    role_file = _ROLE_TO_FILE.get(role_code, f"{role_code}.md") if role_code else ""
    tpl = _MSG_TEMPLATES.get(lang, _MSG_TEMPLATES["zh"])

    if minutes > 0:
        return tpl["remind"].format(role_file=role_file, filename=filename, minutes=minutes)

    if role_code and role_code not in _greeted_roles:
        _greeted_roles.add(role_code)
        return tpl["first_hello"].format(role_file=role_file, filename=filename)

    if "tasks" in directory:
        return tpl["new_task"].format(role_file=role_file, filename=filename)
    elif "reports" in directory:
        return tpl["new_report"].format(role_file=role_file, filename=filename)
    elif "issues" in directory:
        return tpl["new_issue"].format(role_file=role_file, filename=filename)
    return tpl["new_file"].format(role_file=role_file, filename=filename)


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

def _read_keybindings() -> tuple[Path, list[dict]]:
    kb_path = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "keybindings.json"
    existing = []
    if kb_path.exists():
        try:
            raw = kb_path.read_text(encoding="utf-8")
            lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("//")]
            existing = json.loads("\n".join(lines))
        except Exception:
            existing = []
    return kb_path, existing


def check_keybindings(hotkeys: dict[str, tuple]) -> dict:
    """检查快捷键绑定状态，返回详细信息供预检使用"""
    kb_path, existing = _read_keybindings()
    if not kb_path.parent.exists():
        return {"ok": False, "detail": "Cursor 配置目录不存在"}

    result = {"ok": True, "bound": [], "missing": []}
    for role, keys in sorted(hotkeys.items(), key=lambda kv: kv[1]):
        key_str = "+".join(keys)
        found = any(
            item.get("key", "").lower() == key_str.lower()
            and "aichat" in item.get("command", "")
            for item in existing if isinstance(item, dict)
        )
        if found:
            result["bound"].append({"role": role, "key": key_str})
        else:
            result["missing"].append({"role": role, "key": key_str})

    if result["missing"]:
        result["ok"] = False
        missing_str = ", ".join(f'{m["key"]}→{m["role"]}' for m in result["missing"])
        result["detail"] = f"缺少绑定: {missing_str}"
    return result


def ensure_keybindings(hotkeys: dict[str, tuple]):
    """检查快捷键是否已绑定到 aichat 命令，返回检查结果"""
    info = check_keybindings(hotkeys)
    if info["ok"]:
        logger.info("keybindings.json 已包含所有 Agent 快捷键")
    else:
        logger.warning("Agent 快捷键未完全绑定: %s", info.get("detail", ""))
    return info["ok"]


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
        self._kick_times: dict[str, float] = {}  # 角色 → 上次自动 kick 时间

    @property
    def running(self) -> bool:
        return self._running

    def check_and_nudge(self) -> list[dict]:
        if not self._running:
            return []
        new_files = self.watcher.scan()
        events = []
        did_switch = False

        for filename, dir_name, full_path in new_files:
            self.stats["files_detected"] += 1
            if filename in self._notified:
                continue

            recipient = parse_recipient(filename)

            ev = {
                "action": "file_detected",
                "path": f"docs/agents/{dir_name}/{filename}",
                "recipient": recipient or "",
                "time": datetime.now().strftime("%H:%M:%S"),
                "nudged": False,
            }

            if not recipient:
                events.append(ev)
                self._on_event(ev)
                self._notified.add(filename)
                continue

            if recipient.upper() in _NO_NUDGE_RECIPIENTS:
                logger.info("文件 %s → %s（人工角色，仅通知 PWA，不催办）", filename, recipient)
                events.append(ev)
                self._on_event(ev)
                self._notified.add(filename)
                continue

            now = time.time()
            if now - self._last_nudge_time < self.config.nudge_cooldown:
                logger.debug("冷却中，延后唤醒 %s", filename)
                continue

            # 先看 Agent 是否在忙 — 忙碌时不打断，等它干完
            if HAS_VISION:
                try:
                    peek = vision_scan()
                    if peek.found and peek.is_busy:
                        logger.info("Agent 正忙（%s），暂缓催办 %s",
                                    peek.busy_hint, filename)
                        ev["action"] = "deferred_busy"
                        ev["busy_hint"] = peek.busy_hint
                        events.append(ev)
                        self._on_event(ev)
                        continue
                except Exception as e:
                    logger.debug("忙碌检测异常: %s", e)

            win = find_cursor_window()
            msg = build_nudge_message(filename, dir_name, recipient, self.config.lang)

            if win:
                hwnd, title = win
                logger.info("催办 %s ← %s", recipient, filename)
                if switch_and_send(hwnd, recipient, msg,
                                   self.config.hotkeys, self.config.input_offset):
                    self._notified.add(filename)
                    self._last_nudge_time = time.time()
                    self.stats["nudge_ok"] += 1
                    ev["nudged"] = True
                    did_switch = True
                    logger.info("已发送: %s", msg[:60])
                else:
                    self.stats["nudge_fail"] += 1
                    logger.warning("发送失败: %s", recipient)
            else:
                self.stats["nudge_fail"] += 1
                logger.warning("找不到 Cursor 窗口")

            events.append(ev)
            self._on_event(ev)

        return events

    def detect_and_kick_idle(self) -> list[dict]:
        """用 OCR 检测 Agent 是否在等确认，是则自动发"继续" """
        if not self._running:
            return []
        if not HAS_VISION:
            return []

        events = []
        try:
            state = vision_scan()
        except Exception as e:
            logger.debug("idle 检测 scan 异常: %s", e)
            return []

        if not state.found or not state.chat_panel_open:
            return []

        if state.is_busy:
            logger.debug("idle 检测: Agent 正忙（%s），跳过", state.busy_hint)
            return []

        lang = self.config.lang
        keywords = _WAITING_KEYWORDS_ZH if lang == "zh" else _WAITING_KEYWORDS_EN

        # 检查聊天区域下半部分（y > 50%）的文字是否含等待确认关键词
        half_h = state.window.height * 0.50 if state.window else 500
        right_half = state.window.width * 0.40 if state.window else 400
        waiting_hit = ""

        for ln in state.lines:
            if not ln.words:
                continue
            first_w = ln.words[0]
            if first_w.rect.y < half_h or first_w.rect.x < right_half:
                continue
            txt_lower = ln.text.lower()
            for kw in keywords:
                if kw in txt_lower:
                    waiting_hit = kw
                    break
            if waiting_hit:
                break

        if not waiting_hit:
            return []

        # 有角色在等确认 → 发"继续"
        role = state.agent_role or "PM"
        role_std = _normalize_role(role)
        now_str = datetime.now().strftime("%H:%M:%S")

        # 冷却：同一角色 60 秒内不重复 kick
        kick_key = f"kick_{role_std}"
        last_kick = self._kick_times.get(kick_key, 0)
        if time.time() - last_kick < 60:
            return []

        logger.info("idle 检测: %s 在等确认 (命中: \"%s\")，自动发「继续」", role, waiting_hit)

        win = find_cursor_window()
        if not win:
            return []

        hwnd, _ = win
        tpl = _MSG_TEMPLATES.get(lang, _MSG_TEMPLATES["zh"])
        kick_msg = tpl["kick"]

        if switch_and_send(hwnd, role_std, kick_msg,
                           self.config.hotkeys, self.config.input_offset):
            self._kick_times[kick_key] = time.time()
            self.stats["auto_nudge"] += 1
            ev = {
                "action": "auto_kick",
                "role": role_std,
                "trigger": waiting_hit,
                "time": now_str,
            }
            events.append(ev)
            self._on_event(ev)
            logger.info("已自动 kick %s", role_std)

        return events

    def auto_nudge_stuck(self) -> list[dict]:
        if not self._running:
            return []

        # 先检测 Agent 是否在忙，忙碌时整体跳过催促
        if HAS_VISION:
            try:
                peek = vision_scan()
                if peek.found and peek.is_busy:
                    logger.info("auto_nudge: Agent 正忙（%s），跳过本轮催促", peek.busy_hint)
                    return []
            except Exception:
                pass

        stuck_list = self.tracker.get_stuck_tasks()
        events = []

        did_switch = False

        for item in stuck_list:
            if not item["need_nudge"]:
                continue

            recipient = item["recipient"]
            if recipient.upper() in _NO_NUDGE_RECIPIENTS:
                continue

            win = find_cursor_window()
            if not win:
                break

            hwnd, _ = win
            mins = int(item["age_seconds"] / 60)
            auto_msg = build_nudge_message(
                item["filename"], "tasks", recipient, self.config.lang, minutes=mins
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

        return events

    def greet_all_roles(self):
        """启动时逐个角色发打招呼消息，让每个 Agent 知道自己的身份并开始巡检。"""
        win = find_cursor_window()
        if not win:
            logger.warning("未找到 Cursor 窗口，跳过打招呼")
            return

        hwnd, title = win
        logger.info("找到 Cursor 窗口: %s", title[:60])

        greeted = 0

        for role, keys in sorted(self.config.hotkeys.items(), key=lambda kv: kv[1]):
            msg = build_nudge_message("", "", role, self.config.lang)
            logger.info("打招呼 → %s", role)
            if switch_and_send(hwnd, role, msg, self.config.hotkeys, self.config.input_offset):
                greeted += 1
                time.sleep(self.config.nudge_cooldown)
            else:
                logger.warning("打招呼失败: %s", role)

        logger.info("已向 %d 个角色打招呼", greeted)

    def start_patrol(self):
        """启动巡检（由 PWA/面板明确触发）"""
        if self._running:
            logger.info("巡检已在运行，忽略重复启动")
            return
        self._running = True
        self._tick_count = 0
        logger.info("巡检已启动，监听: %s", self.config.agents_dir)

    def stop_patrol(self):
        """停止巡检 — 清除所有运行时状态"""
        self._running = False
        self._tick_count = 0
        self._kick_times.clear()
        self._last_nudge_time = 0
        _greeted_roles.clear()
        logger.info("巡检已停止，所有状态已清除")

    def start_loop(self):
        """后台轮询线程（仅当 _running=True 时才真正执行操作）"""
        SCAN_INTERVAL = 5.0      # 文件扫描间隔（秒）
        IDLE_CHECK_EVERY = 6     # 每 6 轮检测一次 idle（~30 秒）
        STUCK_CHECK_EVERY = 30   # 每 30 轮检测一次超时催促（~150 秒）

        logger.info("轮询线程已就绪（等待启动巡检指令）")
        try:
            while True:
                if self._running:
                    self.check_and_nudge()
                    self._tick_count += 1
                    if self._tick_count % STUCK_CHECK_EVERY == 0:
                        self.auto_nudge_stuck()
                    if self._tick_count % IDLE_CHECK_EVERY == 0:
                        self.detect_and_kick_idle()
                time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            logger.info("轮询线程已退出")

    def stop(self):
        self.stop_patrol()

    def get_file_list(self) -> dict:
        """扫描 tasks/reports/issues 目录，返回文件列表 + 当天统计"""
        import datetime
        today_str = datetime.date.today().strftime("%Y%m%d")
        today_start = datetime.datetime.combine(datetime.date.today(),
                                                 datetime.time.min).timestamp()

        result = {"tasks": [], "reports": [], "issues": [],
                  "today_tasks": 0, "today_reports": 0, "today_issues": 0}

        for dir_name, dir_path in [
            ("tasks", self.config.tasks_dir),
            ("reports", self.config.reports_dir),
            ("issues", self.config.issues_dir),
        ]:
            if not dir_path.exists():
                continue
            today_count = 0
            for f in sorted(dir_path.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                st = f.stat()
                is_today = (today_str in f.name) or (st.st_mtime >= today_start)
                item = {
                    "filename": f.name,
                    "dir": dir_name,
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "today": is_today,
                }
                recipient = parse_recipient(f.name)
                if recipient:
                    item["recipient"] = recipient
                result[dir_name].append(item)
                if is_today:
                    today_count += 1
            result[f"today_{dir_name}"] = today_count

        result["total"] = sum(len(result[k]) for k in ("tasks", "reports", "issues"))
        result["patrol_running"] = self._running
        return result

    def get_status(self) -> dict:
        win = find_cursor_window()
        tasks_count = len(list(self.config.tasks_dir.glob("*.md"))) if self.config.tasks_dir.exists() else 0
        reports_count = len(list(self.config.reports_dir.glob("*.md"))) if self.config.reports_dir.exists() else 0
        issues_count = len(list(self.config.issues_dir.glob("*.md"))) if self.config.issues_dir.exists() else 0

        status = {
            "running": self._running,
            "project_dir": str(self.config.project_dir),
            "cursor_found": win is not None,
            "cursor_connected": win is not None,
            "cursor_title": win[1] if win else None,
            "relay_connected": _relay_connected,
            "tasks_count": tasks_count,
            "reports_count": reports_count,
            "issues_count": issues_count,
            "stats": dict(self.stats),
            "hotkeys": {k: "+".join(v) for k, v in self.config.hotkeys.items()},
            "has_vision": HAS_VISION,
        }
        return status

    def get_cursor_state(self) -> dict:
        """OCR 扫描 Cursor 窗口，返回视觉识别状态"""
        if not HAS_VISION:
            return {"error": "cursor_vision 模块未加载", "has_vision": False}
        try:
            state = vision_scan(save_screenshot=True)
            return state.to_dict()
        except Exception as e:
            return {"error": str(e), "has_vision": True}


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
                global _relay_connected
                _relay_connected = True
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
                            if not nudger.running:
                                logger.info("收到指令但巡检未启动，忽略")
                                continue
                            target_role = str(payload.get("target_role", "PM")).strip() or "PM"
                            _relay_say_to_cursor(nudger, config, target_role, "")

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
                    _last_file_snapshot = ""
                    _push_interval = 10  # 每 10 秒检查一次文件列表变化
                    while not _stop.is_set():
                        await asyncio.sleep(_push_interval)

                        try:
                            file_list = nudger.get_file_list()
                            snapshot = json.dumps(
                                {k: [f["filename"] for f in v]
                                 for k, v in file_list.items()
                                 if isinstance(v, list)},
                                sort_keys=True,
                            )
                            if snapshot != _last_file_snapshot:
                                _last_file_snapshot = snapshot
                                await ws.send(_make_msg("file_list", file_list))
                                logger.debug("文件列表已推送 PWA (%d 个文件)", file_list.get("total", 0))
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
            _relay_connected = False
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
    """通过中继启动巡检"""
    if nudger.running:
        logger.info("巡检已在运行，忽略重复启动")
        return
    nudger.start_patrol()
    logger.info("PWA 远程启动巡检")


def _relay_stop_patrol(nudger: Nudger):
    if not nudger.running:
        logger.info("巡检未运行，忽略停止指令")
        return
    nudger.stop_patrol()
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
            return {"action": action, "ok": True, "message": "巡检已启动"}
        return {"action": action, "ok": True, "message": "巡检已在运行"}
    elif action == "stop_work":
        if nudger.running:
            _relay_stop_patrol(nudger)
            return {"action": action, "ok": True, "message": "巡检已停止"}
        return {"action": action, "ok": True, "message": "巡检未在运行"}
    elif action == "restart":
        nudger.stop_patrol()
        import time as _time
        _time.sleep(1)
        _relay_start_patrol(nudger)
        return {"action": action, "ok": True, "message": "巡检已重启"}
    else:
        return {"action": action, "ok": False, "message": f"未知动作: {action}"}


def _relay_say_to_cursor(nudger: 'Nudger', config, role: str, text: str):
    """PWA 触发 → 切到 Cursor 对应角色窗口 → 说：巡检，开工"""
    logger.info("PWA 触发唤醒 → %s", role)
    win = find_cursor_window()
    if not win:
        logger.warning("未找到 Cursor 窗口，无法唤醒")
        return
    hwnd, title = win
    msg = "巡检，开工" if config.lang == "zh" else "Patrol, let's go"
    if switch_and_send(hwnd, role, msg, config.hotkeys, config.input_offset):
        logger.info("已唤醒 %s", role)
    else:
        logger.warning("唤醒 %s 失败", role)
