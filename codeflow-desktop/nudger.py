"""
CodeFlow Nudger — Agent 唤醒器核心模块

职责：
1. 监听 docs/agents/tasks/ 和 reports/ 文件变化
2. 从文件名解析收件人角色
3. 识别 Cursor 窗口状态（优先 CDP 直连 DOM，降级到 OCR 截屏识别）
4. 用快捷键切换到对应 Agent tab
5. 识别输入框位置 → 精确点击 → 粘贴消息 → 回车
6. 通过 WebSocket 连接中继服务器，接收 PWA 指令、推送文件变化

巡检模式：
  CDP 模式：Cursor 以 --remote-debugging-port=9222 启动时自动激活
            延迟 <100ms，精度 100%，不需要截屏/OCR
  OCR 模式：CDP 不可用时降级，截屏 → WinOCR → 状态分析
            延迟 1-3s，精度约 95%，零侵入

核心原则：先看再做 — scan() 确认状态 → 操作 → scan() 验证结果
"""
from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pyautogui
import pyperclip
import win32con
import win32gui

from config import _T

logger = logging.getLogger("codeflow.nudger")

# ─── 巡检轨迹（结构化可查询，与实时日志同源）────────────────
_PATROL_TRACE_MAX = 120
_patrol_trace_deque: collections.deque = collections.deque(maxlen=_PATROL_TRACE_MAX)
_patrol_trace_lock = threading.Lock()


def patrol_trace(stage: str, detail: str, **fields: Any) -> None:
    """
    记录巡检器在做什么：写 INFO 日志（前缀 [巡检]）+ 环形缓冲。
    stage 建议固定英文键，便于面板做筛选；detail 为人读中文说明。
    """
    ts = time.time()
    extra = {k: v for k, v in fields.items() if v is not None and v != ""}
    line = f"[巡检] {stage} | {detail}"
    if extra:
        line += " | " + " ".join(f"{k}={extra[k]}" for k in sorted(extra))
    logger.info(line)
    rec = {
        "t": datetime.fromtimestamp(ts).strftime("%H:%M:%S"),
        "ts": ts,
        "stage": stage,
        "detail": detail,
        **extra,
    }
    with _patrol_trace_lock:
        _patrol_trace_deque.append(rec)


def get_patrol_trace(limit: int = 80) -> list[dict]:
    with _patrol_trace_lock:
        n = max(1, min(int(limit), _PATROL_TRACE_MAX))
        return list(_patrol_trace_deque)[-n:]


try:
    import websockets
    HAS_WS = True
except ImportError:
    websockets = None
    HAS_WS = False

try:
    from cursor_cdp import (
        is_cdp_available,
        scan as cdp_scan,
        click_role as cdp_click_role,
        type_and_send as cdp_type_and_send,
        press_enter as cdp_press_enter,
        insert_text as cdp_insert_text,
        click_approve as cdp_click_approve,
        CdpCursorState,
    )
    HAS_CDP = True
except ImportError:
    HAS_CDP = False

# CDP 运行时状态：启动时探测，成功后优先走 CDP
_cdp_active = False

try:
    from cursor_vision import (
        scan as vision_scan,
        find_main_cursor_window as vision_find_window,
        click_input_box,
        click_role as vision_click_role,
        find_keyword_position,
        CursorState,
        get_process_exe_path,
        get_chat_title_role,
        get_sidebar_active_role,
        get_active_tab_role,
    )
    HAS_VISION = True
except ImportError:
    HAS_VISION = False
    get_process_exe_path = None  # type: ignore
    logger.warning("cursor_vision 未加载，回退到盲操作模式")

_relay_connected = False


def _probe_cdp(retries: int = 1, delay: float = 0) -> bool:
    """探测 CDP 是否可用，可用则激活 CDP 模式。支持重试（Cursor 冷启动时端口延迟就绪）。"""
    global _cdp_active
    if not HAS_CDP:
        return False
    for attempt in range(1, retries + 1):
        if attempt > 1 and delay > 0:
            time.sleep(delay)
        try:
            if is_cdp_available():
                if not _cdp_active:
                    _cdp_active = True
                    logger.info("✓ CDP 端口可用（9222），巡检使用 CDP 高速模式（第%d次探测）", attempt)
                    patrol_trace("cdp_on", _T("tr_cdp_active"))
                return True
        except Exception as e:
            logger.debug("CDP 探测第%d次异常: %s", attempt, e)
    if not _cdp_active:
        logger.info("CDP 端口 9222 未响应（%d次尝试），使用 OCR 模式", retries)
    return False


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# 角色名标准化映射：OCR 可能识别出的变体 → 标准名
# 覆盖全部四套团队模板：dev-team / media-team / mvp-team / qa-team
_ROLE_ALIASES: dict[str, str] = {
    # ── dev-team ──
    "I-PM": "PM", "1-PM": "PM",
    "2-DEV": "DEV", "I-DEV": "DEV",
    "3-QA": "QA", "I-QA": "QA",
    "4-OPS": "OPS", "I-OPS": "OPS",
    # ── media-team ──
    "I-COLLECTOR": "COLLECTOR", "1-COLLECTOR": "COLLECTOR",
    "2-WRITER": "WRITER", "I-WRITER": "WRITER",
    "3-EDITOR": "EDITOR", "I-EDITOR": "EDITOR",
    "4-PUBLISHER": "PUBLISHER", "I-PUBLISHER": "PUBLISHER",
    # ── mvp-team ──
    "I-BUILDER": "BUILDER", "1-BUILDER": "BUILDER",
    "2-DESIGNER": "DESIGNER", "I-DESIGNER": "DESIGNER",
    "3-MARKETER": "MARKETER", "I-MARKETER": "MARKETER",
    "4-RESEARCHER": "RESEARCHER", "I-RESEARCHER": "RESEARCHER",
    # ── qa-team ──
    "I-LEAD-QA": "LEAD-QA", "1-LEAD-QA": "LEAD-QA",
    "2-TESTER": "TESTER", "I-TESTER": "TESTER",
    "3-AUTO-TESTER": "AUTO-TESTER", "I-AUTO-TESTER": "AUTO-TESTER",
    "4-PERF-TESTER": "PERF-TESTER", "I-PERF-TESTER": "PERF-TESTER",
}

# 命令面板（Ctrl+Shift+P）里搜索的串，需与 Cursor Pinned Agent 显示名一致
# 运行时优先从 _UI_LABELS（预检动态注册）读取；此处为全部四套团队的默认回退值
_PALETTE_ROLE_LABELS: dict[str, str] = {
    # ── dev-team ──
    "PM": "01-PM", "DEV": "02-DEV", "QA": "03-QA",
    "OPS": "04-OPS",
    # ── media-team ──
    "COLLECTOR": "01-COLLECTOR", "WRITER": "02-WRITER",
    "EDITOR": "03-EDITOR", "PUBLISHER": "04-PUBLISHER",
    # ── mvp-team ──
    "BUILDER": "01-BUILDER", "DESIGNER": "02-DESIGNER",
    "MARKETER": "03-MARKETER", "RESEARCHER": "04-RESEARCHER",
    # ── qa-team ──
    "LEAD-QA": "01-LEAD-QA", "TESTER": "02-TESTER",
    "AUTO-TESTER": "03-AUTO-TESTER", "PERF-TESTER": "04-PERF-TESTER",
}

# 切换 Agent：整轮重试次数（每轮内依次 快捷键 → 点击 → 命令面板）
_SWITCH_ROUNDS = 3

# Agent 坐标缓存：{ "PM": [x, y], "COLLECTOR": [x, y], ... }
_AGENT_COORDS: dict[str, list[int]] = {}

# Agent 侧栏标签映射：{ "PM": "01-PM", "COLLECTOR": "02-COLLECTOR", ... }
_UI_LABELS: dict[str, str] = {}


def update_agent_coords(rows: list[dict]) -> None:
    """从预检映射结果更新坐标缓存。rows 格式同 build_preflight_agent_mapping 返回值。"""
    for r in rows:
        role_key = _normalize_role(str(r.get("role", ""))).upper()
        xy = r.get("screen_xy")
        if role_key and xy and len(xy) >= 2:
            _AGENT_COORDS[role_key] = [int(xy[0]), int(xy[1])]


def _register_ui_labels(rows: list[dict]) -> None:
    """注册侧栏标签映射，供命令面板兜底使用。"""
    for r in rows:
        role_key = _normalize_role(str(r.get("role", ""))).upper()
        lbl = r.get("sidebar_label_ocr") or r.get("role", "")
        if role_key and lbl:
            _UI_LABELS[role_key] = str(lbl)


def _click_agent_by_coord(role: str, hwnd: int) -> bool:
    """用记录的坐标点击 Agent Tab。返回 True 表示成功点击（不保证切换正确）。"""
    role_key = _normalize_role(role).upper()
    xy = _AGENT_COORDS.get(role_key)
    if not xy:
        return False
    try:
        import pyautogui
        pyautogui.click(xy[0], xy[1])
        logger.info("vision[坐标] 点击 %s → (%d, %d)", role_key, xy[0], xy[1])
        return True
    except Exception as e:
        logger.warning("_click_agent_by_coord %s: %s", role_key, e)
        return False



def build_preflight_agent_mapping(
    state: Any,
    role_codes: list[str],
) -> tuple[list[dict], bool]:
    """
    一次 vision_scan 后，建立「逻辑角色 ↔ 侧栏 OCR 标签 ↔ 屏幕坐标」映射。

    role_codes: 当前团队的角色列表，按序号顺序（如 ["PUBLISHER","COLLECTOR","WRITER","EDITOR"]）。
                序号自动补充：第1个 → "01-PUBLISHER"，第2个 → "02-COLLECTOR" ...
    返回 (rows, all_mapped)。
    """
    if not state or not getattr(state, "found", False):
        # 即使 OCR 失败也返回带角色的空映射，让前端能显示"定位"按钮
        rows = []
        for idx, code in enumerate(role_codes, 1):
            rows.append({
                "role": code.upper(),
                "seq": idx,
                "expected_label": f"{idx:02d}-{code.upper()}",
                "sidebar_label_ocr": "",
                "mapped": False,
                "screen_xy": None,
            })
        return rows, False

    try:
        from cursor_vision import find_keyword_position
    except ImportError:
        return [], False

    ocr_roles = getattr(state, "all_roles", None) or []

    rows: list[dict] = []
    all_mapped = True

    for idx, code in enumerate(role_codes, 1):
        code_upper = code.upper()
        expected_label = f"{idx:02d}-{code_upper}"  # e.g. "01-PUBLISHER"

        # 从 OCR 识别到的角色里找匹配：
        # 优先精确匹配 "01-PUBLISHER"，其次匹配 "PUBLISHER"（后缀）
        matched_label = ""
        for r in ocr_roles:
            rs = str(r).strip().upper()
            if not rs:
                continue
            # 提取后缀（去掉数字前缀）
            suffix = re.sub(r'^\d+[-\s]*', '', rs)
            if rs == expected_label or suffix == code_upper or rs == code_upper:
                matched_label = r  # 保留原始大小写
                break

        pos = None
        try:
            if matched_label:
                pos = find_keyword_position(state, matched_label)
            if pos is None:
                # 不管 all_roles 有没有，都直接搜 expected_label 文字
                pos = find_keyword_position(state, expected_label)
            if pos is None and matched_label:
                # 也搜后缀（如 "WRITER"）
                pos = find_keyword_position(state, code_upper)
        except Exception:
            pass

        # 如果 OCR 没在 all_roles 里，但能在屏幕上找到坐标，也算识别成功
        if pos and not matched_label:
            matched_label = expected_label

        # 也尝试从已保存的坐标缓存恢复（定位按钮记录的）
        cached_xy = _AGENT_COORDS.get(code_upper)

        if not matched_label and not cached_xy:
            all_mapped = False

        rows.append({
            "role": code_upper,
            "seq": idx,
            "expected_label": expected_label,
            "sidebar_label_ocr": matched_label,
            "mapped": bool(matched_label) or bool(cached_xy),
            "screen_xy": [int(pos[0]), int(pos[1])] if pos else (
                cached_xy if cached_xy else None
            ),
        })

    return rows, bool(rows) and all_mapped


def format_preflight_mapping_detail(rows: list[dict], ocr_active: str) -> str:
    """预检「Agent 映射」一行说明。"""
    parts: list[str] = []
    if ocr_active:
        parts.append(f"当前焦点≈{ocr_active}")
    for r in rows:
        role = r.get("role", "?")
        if r.get("mapped"):
            lb = r.get("sidebar_label_ocr") or ""
            xy = r.get("screen_xy")
            xy_s = f" ({xy[0]},{xy[1]})" if xy else ""
            parts.append(f"{role}→{lb}{xy_s}")
        else:
            parts.append(f"{role}:未识别")
    return "；".join(parts) if parts else "无 OCR 数据"


def save_preflight_agent_map_file(project_dir, window_title: str, ocr_active: str, rows: list[dict]):
    """将映射写入 docs/agents/.codeflow/preflight_agent_map.json。"""
    try:
        from datetime import datetime as _dt
        d = Path(project_dir) / "docs" / "agents" / ".codeflow"
        d.mkdir(parents=True, exist_ok=True)
        fp = d / "preflight_agent_map.json"
        payload = {
            "updated": _dt.now().isoformat(timespec="seconds"),
            "window_title": (window_title or "")[:120],
            "ocr_active": ocr_active or "",
            "roles": rows,
        }
        fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(fp)
    except Exception as e:
        logger.debug("save_preflight_agent_map_file: %s", e)
        return None


# ─── 窗口操作 ─────────────────────────────────────────────

def _find_cursor_window_once() -> tuple[int, str] | None:
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

    def _resolve_exe(hwnd) -> str:
        if get_process_exe_path:
            try:
                return get_process_exe_path(hwnd).lower()
            except Exception:
                pass
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
        title = win32gui.GetWindowText(hwnd) or ""
        exe_path = _resolve_exe(hwnd)
        if exe_path.endswith("cursor.exe"):
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            if (r - l) <= 100 or (b - t) <= 100:
                return
            display = title if title.strip() else "Cursor"
            results.append((hwnd, display))

    win32gui.EnumWindows(_enum, None)
    if not results:
        return None
    # 优先：含 " - Cursor" 且不含「控制面板」
    for hwnd, title in results:
        if " - Cursor" in title and "控制面板" not in title:
            return (hwnd, title)
    # 兜底：含 " - Cursor"
    for hwnd, title in results:
        if " - Cursor" in title:
            return (hwnd, title)
    return results[0]


def find_cursor_window(config: Any | None = None) -> tuple[int, str] | None:
    """
    查找 Cursor 主窗口。枚举与 OpenProcess 在部分环境下偶发失败，故短暂重试几次，
    避免预检「明明已开 Cursor 却显示未找到」。
    重试次数与间隔可由 NudgerConfig / codeflow-nudger.json 配置。
    """
    attempts = 4
    delay = 0.12
    if config is not None:
        attempts = max(1, int(getattr(config, "find_cursor_max_attempts", attempts)))
        delay = max(0.02, float(getattr(config, "find_cursor_retry_delay_s", delay)))
    for attempt in range(attempts):
        w = _find_cursor_window_once()
        if w:
            return w
        if attempt < attempts - 1:
            time.sleep(delay)
    return None


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



def _normalize_role(ocr_role: str) -> str:
    """OCR 识别的角色名 → 标准快捷键角色名"""
    upper = ocr_role.upper()
    return _ROLE_ALIASES.get(upper, upper)


def _role_key_for_task(recipient: str) -> str:
    """任务文件名/OCR标题中的角色名 → 纯角色后缀（去掉所有数字和分隔符）
    例：COLLECTOR / 02-COLLECTOR / COLLECTOR01 → COLLECTOR
        PM / 01-PM → PM
    """
    if not recipient:
        return ""
    s = recipient.upper().strip()
    # 去掉末尾数字（PM → PM）
    s = re.sub(r"\d+$", "", s)
    # 去掉 XX- 前缀数字（02-COLLECTOR → COLLECTOR）
    s = re.sub(r"^\d+[-_\s]*", "", s)
    # 去掉剩余连字符
    s = s.strip("-_ ")
    return _ROLE_ALIASES.get(s, s)


def describe_vision_role_signals(state: 'CursorState') -> str:
    """并列各通道识别结果，供巡检/实测对照。

    - **tab / sidebar**：主判据；tab 为空时显示 ``(未识别)``，避免日志里「只有 sidebar」造成误解。
    - **author⌛**：analyze 的 Author/当前对话行，切换 Tab 后常**滞后**，不必与侧栏一致。
    - **title⚠**：聊天区大字 OCR，易串到消息正文里的角色名，仅作参考。
    """
    if not state or not getattr(state, "found", False):
        return "(窗口未识别)"
    if not HAS_VISION:
        return "(vision 未加载)"
    parts: list[str] = []
    pin = getattr(state, "pinned_active_role", "") or ""
    if pin:
        parts.append(f"pin={pin}")
    try:
        t = get_active_tab_role(state) or ""
    except Exception:
        t = ""
    parts.append(f"tab={'(未识别)' if not t else t}")
    try:
        s = get_sidebar_active_role(state) or ""
    except Exception:
        s = ""
    parts.append(f"sidebar={'(未识别)' if not s else s}")
    ar = getattr(state, "agent_role", "") or ""
    parts.append(f"author⌛={ar if ar else '(空)'}")
    try:
        ct = get_chat_title_role(state) or ""
    except Exception:
        ct = ""
    parts.append(f"title⚠={ct if ct else '(空)'}")
    return " | ".join(parts)


def is_target_role_active_vision(state: 'CursorState', target_role: str) -> bool:
    """与 `switch_and_send` / 面板「全部实测」共用：是否已切到目标 Agent（多通道优先级一致）。"""
    return _is_role_active(state, target_role)


def _is_role_active(state: 'CursorState', target_role: str) -> bool:
    """判断目标角色是否已激活（与界面「当前高亮 Agent」一致）。

    优先级（与 Cursor 实际 UI 一致；顶部 Tab 优先于侧栏行亮度，避免正文/会话标题干扰）：
    1. 侧栏图钉 emoji（pinned_active_role）
    2. 顶部激活 Tab（get_active_tab_role：亮度 / × / OCR；扫描范围仅左侧约 42% 宽）
    3. 右侧 Pinned 竖列行亮度（get_sidebar_active_role）
    4. analyze 给出的 agent_role（仅当与目标匹配才认定）
    5. 聊天区大标题 OCR（get_chat_title_role）— 易误判，放最后
    """
    if not state or not state.found:
        return False
    target = target_role.upper().strip()
    target_name = re.sub(r"^\d+[-_\s]*", "", target).strip()
    if not target_name:
        return False

    def _name_match(candidate: str) -> bool:
        c = candidate.upper().strip()
        c_name = re.sub(r"^\d+[-_\s]*", "", c).strip()
        return (c_name == target_name or
                target_name in c or
                c == target)

    # 1. 侧栏 Pinned 图钉行（高亮行的明确标记）
    pinned = getattr(state, "pinned_active_role", "")
    if pinned:
        matched = _name_match(pinned)
        logger.debug("_is_role_active via pin: %s target=%s → %s",
                     pinned, target_name, matched)
        return matched

    # 2. 顶部 Tab 栏（与用户对「当前 Agent」的第一视觉一致；ROI 已限制在左侧，避免扫到窗体中部）
    if HAS_VISION:
        try:
            tab_role = get_active_tab_role(state)
            if tab_role:
                matched = _name_match(tab_role)
                logger.debug("_is_role_active via active_tab: %s target=%s → %s",
                             tab_role, target_name, matched)
                return matched
        except Exception:
            pass

    # 3. 右侧 Pinned 竖列：按行平均灰度，最亮行为当前 Agent（与 Tab 不同坐标系，作 Tab 失败时的补充）
    if HAS_VISION:
        try:
            side_role = get_sidebar_active_role(state)
            if side_role:
                matched = _name_match(side_role)
                logger.debug("_is_role_active via sidebar_active: %s target=%s → %s",
                             side_role, target_name, matched)
                return matched
        except Exception:
            pass

    # 4. Author / analyze 推断的 agent_role（仅当与目标匹配才认定；否则可能是 unique_roles[0] 占位）
    ar = getattr(state, "agent_role", "") or ""
    if ar:
        matched = _name_match(ar)
        logger.debug("_is_role_active via agent_role: %s target=%s → %s",
                     ar, target_name, matched)
        if matched:
            return True

    # 5. 聊天区左上角角色大标题（可能被会话标题占位，仅作兜底）
    if HAS_VISION:
        try:
            title = get_chat_title_role(state)
            if title:
                matched = _name_match(title)
                logger.debug("_is_role_active via chat_title: %s target=%s → %s",
                             title, target_name, matched)
                return matched
        except Exception:
            pass

    return False


def _is_role_active_for_greet(state: 'CursorState', target_role: str) -> bool:
    """巡检**首次打招呼**专用：宁可不发也不发错窗口。

    - 图钉 / **顶部 Tab** 命中目标 → 通过
    - **侧栏 + Author 行**同时匹配目标且二者角色名一致 → 通过（title OCR 常串到其它 Agent，不以此否决）
    - Tab 未识别时：须 **会话标题** 与 **侧栏** 同时命中目标且二者一致；或仅会话标题命中、侧栏未识别
    - **禁止**仅凭侧栏、且 Author 也不支持目标时判定为已切换
    """
    if not state or not state.found:
        return False
    target = target_role.upper().strip()
    target_name = re.sub(r"^\d+[-_\s]*", "", target).strip()
    if not target_name:
        return False

    def _nm(candidate: str) -> bool:
        c = candidate.upper().strip()
        c_name = re.sub(r"^\d+[-_\s]*", "", c).strip()
        return (c_name == target_name or
                target_name in c or
                c == target)

    pinned = getattr(state, "pinned_active_role", "") or ""
    if pinned and _nm(pinned):
        return True

    if not HAS_VISION:
        return False

    try:
        tab = get_active_tab_role(state) or ""
    except Exception:
        tab = ""
    if tab and _nm(tab):
        return True

    try:
        thread = get_chat_title_role(state) or ""
    except Exception:
        thread = ""
    try:
        side = get_sidebar_active_role(state) or ""
    except Exception:
        side = ""
    ar = getattr(state, "agent_role", "") or ""

    # 严格三重校验：sidebar + author 同时匹配且一致（最强信号）
    if side and _nm(side) and ar and _nm(ar):
        s1 = re.sub(r"^\d+[-_\s]*", "", side.upper()).strip()
        a1 = re.sub(r"^\d+[-_\s]*", "", ar.upper()).strip()
        if s1 == a1:
            logger.info("[greet_strict] 侧栏+Author 均匹配目标且一致 → 通过")
            return True
        else:
            logger.warning(
                "[greet_strict] 侧栏与Author不一致，UI尚未稳定: side=%s author=%s",
                side, ar,
            )
            return False

    # sidebar + title 同时匹配且一致
    if side and _nm(side) and thread and _nm(thread):
        s1 = re.sub(r"^\d+[-_\s]*", "", side.upper()).strip()
        t1 = re.sub(r"^\d+[-_\s]*", "", thread.upper()).strip()
        if s1 == t1:
            logger.info("[greet_strict] 侧栏+会话标题均匹配目标且一致 → 通过")
            return True
        else:
            logger.warning(
                "[greet_strict] 侧栏与会话标题不一致，UI尚未稳定: side=%s title=%s",
                side, thread,
            )
            return False

    # 顶部 Tab / 图钉已命中 → 通过（Tab 是最高优先级信号，已在函数开头处理）
    # sidebar 单独匹配但 author/title 都缺失（OCR 未识别）→ 拒绝，等下轮重扫
    if side and _nm(side) and not ar and not thread:
        logger.warning(
            "[greet_strict] 侧栏匹配但 author/title 均未识别，等待UI稳定 | side=%s",
            side,
        )
        return False

    # 仅 title 匹配、侧栏未识别
    if thread and _nm(thread) and not side:
        return True

    return False


def _run_command_palette_goto_agent(label: str) -> None:
    """
    Ctrl+Shift+P 打开命令面板，粘贴 label 后回车（与手动搜「2-DEV」进 Agent 一致）。
    用剪贴板避免连字符与键盘布局问题。
    """
    pyautogui.hotkey("ctrl", "shift", "p")
    time.sleep(0.65)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    old_clip = ""
    try:
        old_clip = pyperclip.paste()
    except Exception:
        pass
    try:
        pyperclip.copy(label)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.28)
        pyautogui.press("enter")
    finally:
        try:
            if old_clip:
                pyperclip.copy(old_clip)
        except Exception:
            pass


def _wait_while_agent_busy(phase: str) -> None:
    """当前 Agent 处于生成/思考等忙碌状态时等待，避免打断或抢输入。
    CDP 优先（精确检测 Stop 按钮），OCR 兜底。"""
    max_rounds = 48
    poll_s = 4.0
    waited = 0.0
    for _ in range(max_rounds):
        is_busy = False
        hint = ""
        # CDP 优先
        if _cdp_active and HAS_CDP:
            try:
                cdp_st = cdp_scan()
                if not cdp_st.found:
                    return
                is_busy = cdp_st.is_busy
                hint = cdp_st.busy_hint or "cdp"
            except Exception:
                pass
        # OCR 兜底
        if not is_busy and HAS_VISION:
            try:
                st = vision_scan()
                if not st.found:
                    return
                is_busy = getattr(st, "is_busy", False)
                hint = (getattr(st, "busy_hint", None) or "").strip() or "ocr"
            except Exception:
                return
        if not is_busy:
            if waited > 0:
                logger.info("[闲] %s：Agent 已空闲（曾等待 %.1fs）", phase, waited)
            return
        logger.info(
            "[忙] %s：检测到忙碌 [%s]，%.1fs 后再扫（已累计 %.1fs）",
            phase, hint, poll_s, waited,
        )
        time.sleep(poll_s)
        waited += poll_s
    logger.warning(
        "[忙] %s：等待空闲超时（约 %.0fs），仍继续后续步骤",
        phase,
        max_rounds * poll_s,
    )


def _check_cursor_connection_error(config: Any | None = None) -> bool:
    """
    截图 Cursor 窗口，OCR 检测是否出现 Connection Error / Try again 提示。
    返回 True 表示检测到错误需要 Reload。
    """
    try:
        from cursor_vision import capture_cursor_tab_strip
        import winocr
        win = find_cursor_window(config)
        if not win:
            return False
        hwnd, _ = win
        import ctypes
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w < 100 or h < 100:
            return False
        # 截取窗口中间区域（Composer 区域，避免标题栏干扰）
        import pyautogui
        region = (rect.left, rect.top + h // 3, w, h // 2)
        img = pyautogui.screenshot(region=region)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = winocr.recognize_pil_sync(img, lang="en")
        text = result.text if hasattr(result, "text") else str(result)
        text_lower = text.lower()
        keywords = ["connection error", "connection failed", "try again", "please try again",
                    "waiting for extension host", "extension host"]
        found = any(kw in text_lower for kw in keywords)
        if found:
            logger.info("_check_cursor_connection_error: OCR 发现异常关键词: %r", text[:200])
        return found
    except Exception as e:
        logger.debug("_check_cursor_connection_error 异常: %s", e)
        return False


def reload_cursor_window(config: Any | None = None) -> bool:
    """
    通过命令面板执行 Developer: Reload Window，用于长时间无进展时恢复卡死的 Cursor UI。
    执行后窗口句柄可能失效，调用方应重新 find_cursor_window 并等待 reload_window_wait_s。
    """
    win = find_cursor_window(config)
    if not win:
        logger.warning("reload_cursor_window: 未找到 Cursor 窗口")
        return False
    hwnd, _ = win
    if not focus_window(hwnd):
        return False
    try:
        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "shift", "p")
        time.sleep(0.6)
        old_clip = ""
        try:
            old_clip = pyperclip.paste()
        except Exception:
            pass
        try:
            pyperclip.copy("Developer: Reload Window")
            time.sleep(0.06)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.35)
            pyautogui.press("enter")
            # 等待确认对话框弹出，按回车选默认项（通常是"确认重载"）
            time.sleep(1.2)
            pyautogui.press("enter")
        finally:
            try:
                if old_clip:
                    pyperclip.copy(old_clip)
            except Exception:
                pass
        logger.info("reload_cursor_window: 已触发 Developer: Reload Window")
        patrol_trace("cursor_reload", _T("tr_reload_stuck"))
        return True
    except Exception as e:
        logger.warning("reload_cursor_window 失败: %s", e)
        return False


# ─── 核心操作：看→判断→操作→验证 ─────────────────────────


def _switch_and_send_with_cdp(role: str, resolved: str, message: str,
                               *, msg_factory=None) -> bool:
    """CDP 快速通道：通过 DOM 切换角色并发送消息，<200ms 完成。"""
    if not HAS_CDP:
        return False
    try:
        full_role = _UI_LABELS.get(resolved) or role
        logger.info("CDP[点] 切换角色 → %s (full=%s)", resolved, full_role)
        clicked = cdp_click_role(full_role)
        if not clicked:
            clicked = cdp_click_role(resolved)
        if not clicked:
            logger.info("CDP[点] 未找到角色 %s", resolved)
            return False
        time.sleep(0.5)

        # CDP scan 验证切换
        state = cdp_scan()
        if state.found and state.agent_role:
            cdp_role = re.sub(r'^\d+[-_\s]*', '', state.agent_role).upper()
            if cdp_role != resolved:
                logger.info("CDP[验] 切换后角色=%s 期望=%s，不匹配", cdp_role, resolved)
                return False
        logger.info("CDP[验] 角色切换确认: %s", state.agent_role or resolved)

        msg = msg_factory(resolved) if msg_factory else message
        if not msg:
            return False

        logger.info("CDP[发] 输入消息: %s", msg[:60])
        typed = cdp_type_and_send(msg)
        if not typed:
            typed = cdp_insert_text(msg)
        if not typed:
            logger.info("CDP[发] 输入失败")
            return False
        time.sleep(0.3)

        sent = cdp_press_enter()
        if sent:
            logger.info("CDP[完成] 消息已发送 → %s", resolved)
        return sent

    except Exception as e:
        logger.info("CDP 发送异常: %s", e)
        return False


def switch_and_send(hwnd: int, role: str, message,
                    input_offset: tuple[float, float] = (0, 0),
                    *,
                    greet_strict: bool = False) -> bool:
    """切换到目标角色并发送消息。

    ``message`` 可以是字符串，也可以是 ``callable(role) -> str``。
    当传入 callable 时，将在 OCR 确认切换成功、即将粘贴前才调用，
    确保消息内容与当前窗口角色严格一致。
    """
    resolved = _role_key_for_task(role) or re.sub(r'^\d+[-_\s]*', '', role.upper()).strip() or role.upper()

    if not focus_window(hwnd):
        patrol_trace("send_fail", _T("tr_focus_fail"), role=resolved)
        return False

    # 如果 message 是 callable，在切换确认后延迟生成（greet 场景专用）
    msg_factory = message if callable(message) else None
    msg_str = "" if msg_factory else (message or "")

    # ── CDP 快速通道 ──
    if _cdp_active and HAS_CDP:
        ok = _switch_and_send_with_cdp(role, resolved, msg_str, msg_factory=msg_factory)
        if ok:
            prev = (msg_str or "").replace("\n", " ").strip()[:48]
            patrol_trace("send_ok", _T("tr_sent_cdp"),
                         role=resolved, preview=prev, mode="cdp")
            return True
        logger.info("CDP 发送失败，降级到 OCR 模式 → %s", resolved)

    # ── OCR 通道 ──
    vision_sig = ""
    ok, vision_sig = _switch_and_send_with_vision(
        hwnd, role, resolved, msg_str,
        greet_strict=greet_strict, msg_factory=msg_factory,
    )
    if ok:
        prev = (msg_str or "").replace("\n", " ").strip()[:48]
        patrol_trace(
            "send_ok",
            _T("tr_sent"),
            role=resolved,
            preview=prev,
            signals=vision_sig or "(无)",
        )
    else:
        patrol_trace(
            "send_fail",
            _T("tr_switch_paste_fail"),
            role=resolved,
            vision=HAS_VISION,
            signals=vision_sig or "",
        )
    return ok


def _switch_and_send_with_vision(hwnd: int, role: str, resolved: str,
                                 message: str,
                                 *,
                                 greet_strict: bool = False,
                                 msg_factory=None) -> tuple[bool, str]:
    """
    点击侧栏角色名切换 Agent，等待渲染，用 vision 判定是否已切到目标，再粘贴发送。

    ``greet_strict=True``（仅巡检首次打招呼）：使用 `_is_role_active_for_greet`，
    禁止仅凭侧栏判定，避免首条问候发错 Agent。

    时间参数**一律慢速**（与是否打招呼无关）：准确优先，不追求速度。
    """
    # 统一用 _is_role_active（侧栏图钉 / 顶部Tab / 聊天标题 多路径）
    # greet_strict 只保留顶部 Tab 防串台，不再要求 author 三重一致
    def _check(st: 'CursorState', r: str) -> bool:
        return _is_role_active(st, r)

    _MAX_CLICK_TRIES = 6
    if greet_strict:
        _WAIT_AFTER_CLICK = 8.0    # 打招呼多等一会，让 UI 稳定
        _WAIT_RETRY_EXTRA = 3.0
        _PRECHECK_SCANS = 3
        _PRECHECK_GAP = 3.0
        _PRECHECK_INITIAL_SLEEP = 2.0
    else:
        _WAIT_AFTER_CLICK = 6.0
        _WAIT_RETRY_EXTRA = 2.8
        _PRECHECK_SCANS = 4
        _PRECHECK_GAP = 2.8
        _PRECHECK_INITIAL_SLEEP = 2.2
    _inp_retries = 4
    _inp_sleep = 1.0
    _PASTE_SETTLE = 1.2
    _ENTER_WAIT = 2.5
    _PASTE_BEFORE_RECHECK_SLEEP = 2.0
    last_sig = ""

    try:
        # ── Step 1: 确认窗口可见 ──
        state = vision_scan()
        if not state.found:
            logger.warning("vision: Cursor 窗口不可见，放弃发送")
            return False, ""

        _wait_while_agent_busy("发送流程开始")

        # ── Step 2: 点击侧栏角色名，多次重试；每次等待足够长时间再 OCR 验证 ──
        state = vision_scan()
        if not state.found:
            logger.warning("vision: 等待忙碌后窗口不可见，放弃发送")
            return False, ""
        switched_ok = _check(state, role)
        if switched_ok:
            last_sig = describe_vision_role_signals(state)
            logger.info("vision[看] 当前已是目标角色 %s，无需切换 | %s", role, last_sig)
        else:
            # 用 _UI_LABELS 映射找完整 Agent 名（COLLECTOR → 02-COLLECTOR）
            # _UI_LABELS 在预检时注册，与面板显示的映射表一致
            role_key = _normalize_role(role).upper()
            full_name = _UI_LABELS.get(role_key) or role

            for attempt in range(1, _MAX_CLICK_TRIES + 1):
                logger.info("vision[点] 第%d次 目标=%s AgentName=%s",
                            attempt, role, full_name)
                clicked = False
                if state.found:
                    # 优先用完整名（02-COLLECTOR）点击
                    if vision_click_role(state, full_name):
                        logger.info("vision[点] 第%d次点击 %s", attempt, full_name)
                        clicked = True
                    elif full_name != role and vision_click_role(state, role.upper()):
                        logger.info("vision[点] 第%d次点击(简名) %s", attempt, role)
                        clicked = True

                if not clicked:
                    logger.warning("vision[点] 第%d次未找到 %s 坐标，等待重试", attempt, full_name)

                # 等待 Cursor 渲染
                time.sleep(_WAIT_AFTER_CLICK)

                # OCR 重新扫，与「全部实测」同一套 _is_role_active（Tab/侧栏优先于正文标题）
                state = vision_scan()
                sig = describe_vision_role_signals(state)
                last_sig = sig
                logger.info("vision[验] 第%d次 目标=%s 信号=%s all_roles=%s",
                            attempt, role, sig, state.all_roles)

                if _check(state, role):
                    logger.info("vision[确认] 切换成功 → %s", sig)
                    switched_ok = True
                    break
                else:
                    logger.warning("vision[确认] 第%d次未切到目标，信号=%s，再等 %.1fs 重扫",
                                   attempt, sig, _WAIT_RETRY_EXTRA)
                    time.sleep(_WAIT_RETRY_EXTRA)
                    state = vision_scan()
                    sig2 = describe_vision_role_signals(state)
                    last_sig = sig2
                    logger.info("vision[验+] 第%d次额外扫 目标=%s 信号=%s",
                                attempt, role, sig2)
                    if _check(state, role):
                        logger.info("vision[确认+] 延迟确认切换成功 → %s", sig2)
                        switched_ok = True
                        break

            if not switched_ok:
                logger.warning(
                    "vision: %d次尝试均未切换到 %s，放弃%s",
                    _MAX_CLICK_TRIES,
                    role,
                    "（greet_strict：未同时满足 Tab 或 会话标题+侧栏）" if greet_strict else "",
                )
                return False, last_sig

        # ── Step 2b：发送前多轮复核（静止等待 + 连续 vision_scan），宁可慢不可错 ──
        time.sleep(_PRECHECK_INITIAL_SLEEP)
        pre_ok = False
        for vi in range(_PRECHECK_SCANS):
            state = vision_scan()
            last_sig = describe_vision_role_signals(state)
            if _check(state, role):
                logger.info("vision[复核] 第 %d/%d 次 角色一致，可继续输入 | %s",
                            vi + 1, _PRECHECK_SCANS, last_sig)
                pre_ok = True
                break
            logger.warning(
                "vision[复核] 第 %d/%d 次 仍未确认目标=%s | %s，%.1fs 后再扫",
                vi + 1, _PRECHECK_SCANS, role, last_sig, _PRECHECK_GAP,
            )
            time.sleep(_PRECHECK_GAP)
        if not pre_ok:
            logger.warning("vision: 发送前复核未通过，放弃发送（避免错发窗口）")
            return False, last_sig

        # greet_strict：顶部 Tab 防串台终检（识别不到直接放行，不阻塞）
        if greet_strict and HAS_VISION:
            try:
                active_tab = get_active_tab_role(state)
                if active_tab:
                    target_name = re.sub(r"^\d+[-_\s]*", "", role.upper()).strip()
                    tab_name = re.sub(r"^\d+[-_\s]*", "", active_tab.upper()).strip()
                    if tab_name != target_name:
                        logger.warning(
                            "vision[greet] 顶部Tab不匹配 tab=%s target=%s，放弃发送",
                            active_tab, role,
                        )
                        return False, last_sig
                    logger.info("vision[greet] 顶部Tab匹配 %s ✓", active_tab)
                else:
                    logger.info("vision[greet] 顶部Tab未识别，信任已通过的角色校验，继续发送")
            except Exception as _te:
                logger.debug("vision[greet] Tab终检异常: %s", _te)

        # ── Step 3: 定位并点击输入框，验证焦点 ──
        def _locate_and_click_input(st) -> bool:
            """点击输入框，返回是否成功定位"""
            if st.input_box:
                ix = int(st.input_box.cx)
                iy = int(st.input_box.cy)
                logger.info("vision[点] OCR输入框 (%d,%d)", ix, iy)
                pyautogui.click(ix, iy)
                return True
            elif st.window:
                w = st.window
                ix = w.left + w.width // 2
                iy = w.top + int(w.height * 0.92)
                logger.info("vision[点] 估算输入框底部92%% (%d,%d)", ix, iy)
                pyautogui.click(ix, iy)
                return True
            return False

        input_ok = False
        for inp_try in range(_inp_retries):
            if _locate_and_click_input(state):
                time.sleep(_inp_sleep)
                state = vision_scan()
                if state.input_box:
                    logger.info("vision[输入框] 已获得焦点")
                    input_ok = True
                    break
                else:
                    logger.warning("vision[输入框] 第%d次点击后未检测到输入框", inp_try + 1)
            else:
                logger.warning("vision[输入框] 第%d次无法定位", inp_try + 1)
                time.sleep(_inp_sleep)
                state = vision_scan()

        if not input_ok:
            logger.warning("vision: 无法确认输入框焦点，仍尝试发送")

        time.sleep(_PASTE_BEFORE_RECHECK_SLEEP)
        state = vision_scan()
        last_sig = describe_vision_role_signals(state)
        if not _check(state, role):
            logger.warning(
                "vision[粘贴前] 角色不一致，放弃发送（避免错发） | %s",
                last_sig,
            )
            return False, last_sig
        # 粘贴前顶部 Tab 防串台（识别不到放行）
        if HAS_VISION and greet_strict:
            try:
                active_tab = get_active_tab_role(state)
                if active_tab:
                    target_name = re.sub(r"^\d+[-_\s]*", "", role.upper()).strip()
                    tab_name = re.sub(r"^\d+[-_\s]*", "", active_tab.upper()).strip()
                    if tab_name != target_name:
                        logger.warning(
                            "vision[粘贴前] 顶部Tab不匹配 tab=%s target=%s，放弃",
                            active_tab, role,
                        )
                        return False, last_sig
            except Exception as _te:
                logger.debug("vision[粘贴前] Tab校验异常: %s", _te)
        logger.info("vision[粘贴前] 角色再确认通过 | %s", last_sig)

        # msg_factory：角色确认后才生成消息，确保消息内容与当前窗口角色严格一致
        if msg_factory:
            message = msg_factory(resolved)
            logger.info("vision[msg_factory] 角色确认后生成消息: %s", message[:60])

        _wait_while_agent_busy("粘贴发送前")

        # ── Step 4: 粘贴，验证内容进入输入框 ──
        old_clip = ""
        try:
            old_clip = pyperclip.paste()
        except Exception:
            pass

        pyperclip.copy(message)
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(_PASTE_SETTLE)

        # OCR 验证输入框里有内容（不再是 placeholder）
        state = vision_scan()
        msg_preview = message[:20].strip()
        pasted_ok = False
        if state.input_box and state.lines:
            # 在输入框附近找是否有粘贴的文字
            ib = state.input_box
            for ln in state.lines:
                if not ln.words:
                    continue
                fw = ln.words[0]
                # 输入框区域内（y坐标接近输入框）
                if abs((fw.rect.y + state.window.top) - ib.cy) < 60:
                    txt = ln.text.strip()
                    # 不是 placeholder 且有实际内容
                    if txt and not any(h in txt.lower() for h in ["plan, build", "/ for commands", "@ for context"]):
                        logger.info("vision[粘贴] 输入框内容确认: %r", txt[:30])
                        pasted_ok = True
                        break

        if not pasted_ok:
            logger.warning("vision[粘贴] 未能OCR确认内容进入输入框，继续发送")

        # ── Step 5: 回车发送，验证消息出现在聊天区 ──
        pyautogui.press("enter")
        time.sleep(_ENTER_WAIT)

        # OCR 验证消息出现在聊天区
        state = vision_scan()
        sent_ok = False
        if state.lines:
            for ln in state.lines:
                if msg_preview and msg_preview[:10].lower() in ln.text.lower():
                    logger.info("vision[发送确认] 消息已出现在聊天区: %r", ln.text[:40])
                    sent_ok = True
                    break

        if sent_ok:
            logger.info("vision[发] ✓ 发送成功确认 → %s", role)
        else:
            logger.warning("vision[发] 未能OCR确认消息出现，但已按回车，视为已发送")

        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass

        sig_out = describe_vision_role_signals(state)
        logger.info("vision[发] 已发送到 %s: %s | %s", role, message[:50], sig_out)
        return True, sig_out

    except Exception as e:
        logger.error("vision switch_and_send 异常: %s", e)
        return False, last_sig


# ─── 文件解析 ─────────────────────────────────────────────

_TASK_PATTERN = re.compile(
    r'TASK-(\d{8})-(\d{3})-([A-Za-z0-9]+)-to-([A-Za-z0-9]+)\.md',
    re.IGNORECASE,
)
# 从 reports/、log/ 文件名中提取 TASK-YYYYMMDD-NNN（归档仅在 log/，不与 tasks/ 混放同一份文件）
_TASK_ID_IN_NAME = re.compile(r"TASK-(\d{8})-(\d{3})", re.IGNORECASE)


def parse_recipient(filename: str) -> str | None:
    m = _TASK_PATTERN.search(filename)
    return m.group(4).upper() if m else None


# ─── 情景对话模板 ─────────────────────────────────────────

_MSG_TEMPLATES = {
    "zh": {
        "first_hello": "【码流巡检】你好，你当前的角色是 {role_name}，请阅读 {role_file} 确认身份，然后查看 docs/agents/tasks/ 中待办任务并开始执行。",
        # 首次身份确认之后：新文件 / 定时催办 / 卡住催促 一律短句，由 Agent 自行打开任务文件阅读
        "patrol_ping": "【码流巡检】巡检，开工。请自行查看 docs/agents/tasks/ 等待办任务。",
        "new_task": "新任务到达: {filename}，请读取任务单并执行",
        "new_report": "新报告到达: {filename}，请审核并回复",
        "new_issue": "新问题: {filename}，请查看并处理",
        "new_file": "新文件: {filename}",
        "remind": "催办: {filename} 已等待 {minutes} 分钟，请尽快处理",
        "kick": "继续",
    },
    "en": {
        "first_hello": "[CodeFlow] Hello, your role is {role_name}. Confirm by reading {role_file}, then check docs/agents/tasks/ for pending tasks and proceed.",
        "patrol_ping": "[CodeFlow] Patrol ping — proceed. Open docs/agents/tasks/ for pending items.",
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
_NO_NUDGE_RECIPIENTS = frozenset({"ADMIN", "ADMIN"})


def collect_closed_task_ids(config) -> set[str]:
    """
    已闭环的 TASK-YYYYMMDD-NNN 集合：
    - reports/ 文件名中出现该编号（团队回执）；
    - log/ 文件名中出现该编号（PM 归档；归档文件只放在 log/，不在 tasks/ 重复存放）。
    """
    closed: set[str] = set()
    for d in (config.reports_dir, config.log_dir):
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            for m in _TASK_ID_IN_NAME.finditer(f.name):
                closed.add(f"TASK-{m.group(1)}-{m.group(2)}".upper())
    return closed


def list_nonstandard_task_filenames(config) -> list[str]:
    """tasks/ 下不符合标准 TASK-…-to-….md 命名的文件（仍会被浏览，但不参与自动催办配对）。"""
    td = config.tasks_dir
    if not td.exists():
        return []
    bad: list[str] = []
    for f in td.glob("*.md"):
        if not _TASK_PATTERN.match(f.name):
            bad.append(f.name)
    return sorted(bad)


def list_incomplete_task_files(config) -> list[tuple[str, str, str]]:
    """
    读取 tasks/ 下全部标准任务文件；未完成 = 该 TASK-日期-序号 未在 reports/ 与 log/ 任一侧文件名中出现。
    约定：归档后任务单只放在 log/（或已从 tasks 删除），log 与 tasks 不混放同一份物理文件。
    """
    tasks_dir = config.tasks_dir
    if not tasks_dir.exists():
        return []
    closed_ids = collect_closed_task_ids(config)
    out: list[tuple[str, str, str]] = []
    for f in sorted(tasks_dir.glob("*.md")):
        m = _TASK_PATTERN.match(f.name)
        if not m:
            continue
        task_id = f"TASK-{m.group(1)}-{m.group(2)}".upper()
        if task_id in closed_ids:
            continue
        recipient = m.group(4).upper()
        if recipient in _NO_NUDGE_RECIPIENTS:
            continue
        out.append((f.name, "tasks", str(f)))
    return out


# 单次巡检周期内，同一文件最多自动重试次数（冷却/忙碌/发送失败）
_MAX_NUDGE_ATTEMPTS_PER_FILE = 40


def _fmt_tpl(tpl_str: str, **kwargs) -> str:
    """模板字符串格式化；无占位符时直接返回，未知占位符用空串填充（容错）。"""
    if "{" not in tpl_str:
        return tpl_str
    try:
        return tpl_str.format(**kwargs)
    except KeyError:
        # 用 string.Formatter 提取所有占位符，缺失的补空串后重试
        import string
        missing = {
            fname for _, fname, _, _ in string.Formatter().parse(tpl_str)
            if fname and fname not in kwargs
        }
        kwargs.update({k: "" for k in missing})
        return tpl_str.format(**kwargs)


def _patrol_ping_text(
    tpl: dict,
    lang: str,
    role_file: str,
    filename: str,
    minutes: int,
    config: Any | None,
) -> str:
    """首次问候之后的短句催办（可配置覆盖）。"""
    if config is not None:
        raw = (getattr(config, "patrol_ping_zh", "") or "").strip() if lang == "zh" else (
            getattr(config, "patrol_ping_en", "") or "").strip()
        if raw:
            return _fmt_tpl(raw, role_file=role_file, filename=filename, minutes=minutes)
    return _fmt_tpl(
        tpl["patrol_ping"],
        role_file=role_file, filename=filename, minutes=minutes,
    )


def _role_to_file(role_code: str) -> str:
    """将角色代码映射到 docs/agents/ 下的文件路径，支持标准角色和媒体/MVP团队角色。"""
    # 先去掉前缀数字（如 "03-WRITER" → "WRITER"，"WRITER" → "WRITER"）
    clean = re.sub(r'^\d+[-_\s]*', '', role_code.upper()).strip()
    # 标准 dev 团队
    _KNOWN = {
        # ── dev-team ──
        "PM":        "docs/agents/PM-01.md",
        "DEV":       "docs/agents/DEV-01.md",
        "OPS":       "docs/agents/OPS-01.md",
        "QA":        "docs/agents/QA-01.md",
        "ADMIN":     "docs/agents/README.md",
        # ── media-team ──
        "COLLECTOR": "docs/agents/COLLECTOR.md",
        "WRITER":    "docs/agents/WRITER.md",
        "EDITOR":    "docs/agents/EDITOR.md",
        "PUBLISHER": "docs/agents/PUBLISHER.md",
        # ── mvp-team ──
        "BUILDER":    "docs/agents/BUILDER.md",
        "DESIGNER":   "docs/agents/DESIGNER.md",
        "MARKETER":   "docs/agents/MARKETER.md",
        "RESEARCHER": "docs/agents/RESEARCHER.md",
        # ── qa-team ──
        "LEAD-QA":     "docs/agents/LEAD-QA.md",
        "TESTER":      "docs/agents/TESTER.md",
        "AUTO-TESTER": "docs/agents/AUTO-TESTER.md",
        "PERF-TESTER": "docs/agents/PERF-TESTER.md",
    }
    return _KNOWN.get(clean, f"docs/agents/{clean}.md")


def build_nudge_message(
    filename: str,
    directory: str,
    recipient: str = "",
    lang: str = "zh",
    minutes: int = 0,
    *,
    config: Any | None = None,
    mark_greeted: bool = True,
) -> str:
    """生成催办/打招呼消息。

    ``mark_greeted=False`` 时只生成消息内容，不修改 _greeted_roles 状态；
    调用方确认消息成功发送后再调用 mark_role_greeted() 标记。
    """
    # 归一化：去掉前缀数字（"03-WRITER" → "WRITER"，"WRITER" → "WRITER"）
    role_code = re.sub(r'^\d+[-_\s]*', '', recipient.upper()).strip() if recipient else ""
    role_file = _role_to_file(role_code) if role_code else ""
    # role_name：取文件名部分，不含路径（COLLECTOR.md → COLLECTOR）
    role_name = role_code if role_code else ""
    tpl = _MSG_TEMPLATES.get(lang, _MSG_TEMPLATES["zh"])

    if minutes > 0:
        if role_code and role_code in _greeted_roles:
            return _patrol_ping_text(tpl, lang, role_file, filename, minutes, config)
        return _fmt_tpl(
            tpl["remind"],
            role_file=role_file, role_name=role_name, filename=filename, minutes=minutes,
        )

    if role_code and role_code not in _greeted_roles:
        if mark_greeted:
            _greeted_roles.add(role_code)
        return _fmt_tpl(
            tpl["first_hello"],
            role_file=role_file, role_name=role_name, filename=filename,
        )

    return _patrol_ping_text(tpl, lang, role_file, filename, minutes, config)


def mark_role_greeted(recipient: str) -> None:
    """发送成功后调用，将角色标记为已打过招呼。"""
    role_code = re.sub(r'^\d+[-_\s]*', '', recipient.upper()).strip() if recipient else ""
    if role_code:
        _greeted_roles.add(role_code)


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



# ─── 唤醒器核心 ───────────────────────────────────────────

class TaskTracker:
    """追踪任务生命周期：创建 → 执行中 → 可能卡住 → 超时"""

    def __init__(self, config):
        self.config = config
        self._nudged_at: dict[str, float] = {}  # task_id → 上次催促时间
        self.STUCK_THRESHOLD = float(getattr(config, "task_stuck_threshold_s", 600.0))
        self.TIMEOUT_THRESHOLD = float(getattr(config, "task_timeout_threshold_s", 1200.0))
        self.AUTO_NUDGE_INTERVAL = float(getattr(config, "auto_nudge_interval_s", 300.0))

    def get_stuck_tasks(self) -> list[dict]:
        if not self.config.tasks_dir.exists():
            return []

        closed_ids = collect_closed_task_ids(self.config)

        stuck = []
        now = time.time()
        for f in self.config.tasks_dir.glob("*.md"):
            m = _TASK_PATTERN.match(f.name)
            if not m:
                continue
            task_id = f"TASK-{m.group(1)}-{m.group(2)}".upper()
            recipient = m.group(4).upper()
            if task_id in closed_ids:
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
        self._wake_event = threading.Event()
        self._observer: Any = None  # watchdog.Observer when HAS_WATCHDOG
        self._notified: set[str] = set()
        # 因冷却 / Agent 忙碌 / 发送失败而未能完成催办的文件，下一轮继续处理（否则 FileWatcher 已记入 _known 后会永久丢失）
        self._nudge_pending: list[tuple[str, str, str]] = []
        self._nudge_attempts: dict[str, int] = {}
        # 按**收件人角色**分别冷却：避免「发给 PUBLISHER 后」同一轮里 EDITOR/其它文件全被全局冷却误伤
        self._last_nudge_by_recipient: dict[str, float] = {}
        self._running = False
        self._on_event = on_event or (lambda ev: None)
        self.stats = {"nudge_ok": 0, "nudge_fail": 0, "files_detected": 0, "auto_nudge": 0}
        self._tick_count = 0
        self._kick_times: dict[str, float] = {}  # 角色 → 上次自动 kick 时间
        self._relay_push_version: int = 0  # 递增后中继线程立即推送快照
        self._stuck_reload_done: set[str] = set()  # 已对其实施过 Reload Window 的 TASK 编号

    def _bootstrap_pending_tasks(self) -> int:
        """启动巡检接手：读取 tasks/ 全部标准任务；结合 reports+log 判断闭环；非标准命名另记轨迹。"""
        nonstd = list_nonstandard_task_filenames(self.config)
        if nonstd:
            patrol_trace(
                "tasks_nonstandard",
                _T("tr_nonstandard_files"),
                count=len(nonstd),
                samples=",".join(nonstd[:8]) + (f",…(+{len(nonstd) - 8})" if len(nonstd) > 8 else ""),
            )
        incomplete = list_incomplete_task_files(self.config)
        n = len(incomplete)
        fn_preview = ",".join(x[0] for x in incomplete[:16])
        if n > 16:
            fn_preview += f",…(+{n - 16})"
        n_closed = len(collect_closed_task_ids(self.config))
        patrol_trace(
            "bootstrap_read",
            _T("tr_scan_done"),
            incomplete_count=n,
            closed_ids_marked=n_closed,
            filenames_preview=fn_preview or "(无)",
        )
        for fn, dir_name, full in incomplete:
            self._notified.discard(fn)
            self._nudge_pending.append((fn, dir_name, full))
            rp = parse_recipient(fn) or ""
            patrol_trace(
                "bootstrap_queue",
                _T("tr_open_queued"),
                filename=fn,
                recipient=rp,
            )
        return n

    def _start_file_observer(self):
        if not HAS_WATCHDOG or not getattr(self.config, "use_file_watcher", True):
            return
        if self._observer is not None:
            return
        try:

            class _MdHandler(FileSystemEventHandler):
                def __init__(self, ev: threading.Event):
                    self._ev = ev

                def on_created(self, event):
                    self._go(event)

                def on_modified(self, event):
                    self._go(event)

                def _go(self, event):
                    if event.is_directory:
                        return
                    if str(event.src_path).lower().endswith(".md"):
                        self._ev.set()

            obs = Observer()
            for d in (self.config.tasks_dir, self.config.reports_dir, self.config.issues_dir):
                if d.exists():
                    obs.schedule(_MdHandler(self._wake_event), str(d), recursive=False)
            obs.start()
            self._observer = obs
            logger.info("watchdog: 已监听 tasks/reports/issues（.md 变更将加速下一轮检测）")
            patrol_trace("watchdog_on", _T("tr_watcher_on"), dirs="tasks,reports,issues")
        except Exception as e:
            logger.warning("watchdog 未启用（仍用轮询）: %s", e)

    def _stop_file_observer(self):
        if self._observer is None:
            return
        try:
            self._observer.stop()
            self._observer.join(timeout=3)
        except Exception:
            pass
        self._observer = None

    @property
    def running(self) -> bool:
        return self._running

    def _merge_pending_and_scan(
        self, scan_new: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        """合并待重试队列与本轮 scan 结果，按文件名去重（pending 优先）。"""
        merged: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for item in self._nudge_pending + scan_new:
            fn = item[0]
            if fn in seen:
                continue
            seen.add(fn)
            merged.append(item)
        self._nudge_pending.clear()
        return merged

    def _schedule_retry(self, filename: str, dir_name: str, full_path: str, reason: str) -> bool:
        """返回 True 表示已加入重试；False 表示超过重试上限，放弃并记入 _notified。
        agent_busy 不消耗重试次数，只延后等待。
        """
        # agent_busy 不计入失败次数，直接加队列等下一轮
        if reason == "agent_busy":
            self._nudge_pending.append((filename, dir_name, full_path))
            patrol_trace(
                "defer",
                _T("tr_agent_busy"),
                filename=filename,
                reason=reason,
                attempt=self._nudge_attempts.get(filename, 0),
                max_attempts=_MAX_NUDGE_ATTEMPTS_PER_FILE,
            )
            return True
        n = self._nudge_attempts.get(filename, 0) + 1
        self._nudge_attempts[filename] = n
        if n >= _MAX_NUDGE_ATTEMPTS_PER_FILE:
            logger.warning(
                "催办 %s 已达最大重试次数 (%d)，原因=%s，标记为已处理",
                filename, _MAX_NUDGE_ATTEMPTS_PER_FILE, reason,
            )
            patrol_trace(
                "giveup",
                _T("tr_max_retries"),
                filename=filename,
                reason=reason,
                attempts=n,
            )
            self._notified.add(filename)
            self._nudge_attempts.pop(filename, None)
            return False
        self._nudge_pending.append((filename, dir_name, full_path))
        logger.debug("催办延后重试 (%d/%d): %s 原因=%s", n, _MAX_NUDGE_ATTEMPTS_PER_FILE, filename, reason)
        _defer_reason_key = {
            "cooldown": "tr_cooldown",
            "agent_busy": "tr_agent_busy",
            "send_failed": "tr_switch_paste_fail",
            "no_cursor_window": "tr_no_cursor",
        }
        patrol_trace(
            "defer",
            _T(_defer_reason_key.get(reason, "tr_cooldown")),
            filename=filename,
            reason=reason,
            attempt=n,
            max_attempts=_MAX_NUDGE_ATTEMPTS_PER_FILE,
        )
        return True

    def check_and_nudge(self) -> list[dict]:
        if not self._running:
            return []
        scan_new = self.watcher.scan()
        new_files = self._merge_pending_and_scan(scan_new)
        events = []
        did_switch = False

        for filename, dir_name, full_path in new_files:
            if filename in self._notified:
                continue
            # 仅首次进入队列算「检测到新文件」；重试队列不重复累计
            if self._nudge_attempts.get(filename, 0) == 0:
                self.stats["files_detected"] += 1

            recipient = parse_recipient(filename)
            patrol_trace(
                "file_in",
                _T("tr_processing"),
                filename=filename,
                dir=dir_name,
                recipient=recipient or "?",
                retry=self._nudge_attempts.get(filename, 0),
            )

            ev = {
                "action": "file_detected",
                "path": f"docs/agents/{dir_name}/{filename}",
                "recipient": recipient or "",
                "time": datetime.now().strftime("%H:%M:%S"),
                "nudged": False,
            }

            if not recipient:
                patrol_trace("skip", _T("tr_parse_fail"), filename=filename)
                events.append(ev)
                self._on_event(ev)
                self._notified.add(filename)
                continue

            if recipient.upper() in _NO_NUDGE_RECIPIENTS:
                logger.info("文件 %s → %s（人工角色，仅通知 PWA，不催办）", filename, recipient)
                patrol_trace("skip", _T("tr_human_skip"), filename=filename, recipient=recipient)
                events.append(ev)
                self._on_event(ev)
                self._notified.add(filename)
                continue

            now = time.time()
            rk = recipient.upper()
            last_for_r = self._last_nudge_by_recipient.get(rk, 0.0)
            if now - last_for_r < self.config.nudge_cooldown:
                logger.debug("冷却中（收件人=%s），延后 %s", rk, filename)
                if self._schedule_retry(filename, dir_name, full_path, "cooldown"):
                    ev["action"] = "deferred_cooldown"
                    events.append(ev)
                    self._on_event(ev)
                continue

            # 先看目标 Agent 是否在忙 — 忙碌时不打断，等它干完
            # CDP 优先（精确检测 Stop 按钮），OCR 兜底
            _target_busy = False
            _busy_hint_str = ""
            target_rk = _role_key_for_task(recipient) or _normalize_role(recipient).upper()
            target_full = _UI_LABELS.get(target_rk) or recipient

            if _cdp_active and HAS_CDP:
                try:
                    # CDP：先切到目标 Agent，再检测 is_busy
                    cdp_click_role(target_full) or cdp_click_role(target_rk)
                    time.sleep(0.5)
                    cdp_st = cdp_scan()
                    if cdp_st.found and cdp_st.is_busy:
                        _target_busy = True
                        _busy_hint_str = cdp_st.busy_hint or "cdp:stop_button"
                        logger.info("CDP 检测：目标 %s 正忙（%s）", target_rk, _busy_hint_str)
                    else:
                        logger.debug("CDP 检测：目标 %s 空闲", target_rk)
                except Exception as e:
                    logger.debug("CDP 忙碌检测异常: %s", e)

            if not _target_busy and HAS_VISION:
                try:
                    peek = vision_scan()
                    if peek.found and peek.is_busy:
                        busy_role = (peek.agent_role or peek.busy_hint or "").upper()
                        if target_rk in busy_role or busy_role in (
                            _UI_LABELS.get(target_rk, "").upper(), target_rk
                        ):
                            _target_busy = True
                            _busy_hint_str = peek.busy_hint or "ocr:spinner"
                        else:
                            logger.debug("忙碌的是 %s，目标是 %s，不影响催办",
                                         busy_role, target_rk)
                except Exception as e:
                    logger.debug("OCR 忙碌检测异常: %s", e)

            if _target_busy:
                logger.info("目标 Agent %s 正忙（%s），暂缓催办 %s",
                            target_rk, _busy_hint_str, filename)
                ev["action"] = "deferred_busy"
                ev["busy_hint"] = _busy_hint_str
                if self._schedule_retry(filename, dir_name, full_path, "agent_busy"):
                    events.append(ev)
                    self._on_event(ev)
                continue

            win = find_cursor_window(self.config)
            msg = build_nudge_message(
                filename, dir_name, recipient, self.config.lang, config=self.config,
            )

            if win:
                hwnd, title = win
                logger.info("催办 %s ← %s", recipient, filename)
                patrol_trace("cursor_ok", _T("tr_cursor_found"), title=(title or "")[:56])
                if switch_and_send(hwnd, recipient, msg,
                                   self.config.input_offset):
                    self._notified.add(filename)
                    self._nudge_attempts.pop(filename, None)
                    self._last_nudge_by_recipient[rk] = time.time()
                    self.stats["nudge_ok"] += 1
                    ev["nudged"] = True
                    did_switch = True
                    logger.info("已发送: %s", msg[:60])
                    patrol_trace(
                        "task_done",
                        _T("tr_nudge_done"),
                        filename=filename,
                        recipient=recipient,
                    )
                else:
                    self.stats["nudge_fail"] += 1
                    logger.warning("发送失败: %s", recipient)
                    if self._schedule_retry(filename, dir_name, full_path, "send_failed"):
                        ev["action"] = "deferred_send_failed"
                        events.append(ev)
                        self._on_event(ev)
                    continue
            else:
                self.stats["nudge_fail"] += 1
                logger.warning("找不到 Cursor 窗口")
                patrol_trace("cursor_fail", _T("tr_no_cursor"), filename=filename, recipient=recipient)
                if self._schedule_retry(filename, dir_name, full_path, "no_cursor_window"):
                    ev["action"] = "deferred_no_window"
                    events.append(ev)
                    self._on_event(ev)
                continue

            events.append(ev)
            self._on_event(ev)

        return events

    def detect_and_kick_idle(self) -> list[dict]:
        """检测 Agent 是否在等确认，是则自动发"继续"。CDP 优先，OCR 兜底。"""
        if not self._running:
            return []

        events = []
        waiting_hit = ""
        role = ""

        # ── CDP 优先：精确检测 pending_approvals ──
        if _cdp_active and HAS_CDP:
            try:
                cdp_st = cdp_scan()
                if not cdp_st.found:
                    pass
                elif cdp_st.is_busy:
                    logger.debug("idle 检测(CDP): Agent 正忙（%s），跳过", cdp_st.busy_hint)
                    return []
                elif cdp_st.agent_status == "waiting_approval" or len(cdp_st.pending_approvals) > 0:
                    waiting_hit = "cdp:pending_approval"
                    role = cdp_st.agent_role or "PM"
                    logger.info("idle 检测(CDP): %s 有 %d 个待审批",
                                role, len(cdp_st.pending_approvals))
            except Exception as e:
                logger.debug("idle 检测(CDP) 异常: %s", e)

        # ── OCR 兜底 ──
        if not waiting_hit and HAS_VISION:
            try:
                state = vision_scan()
            except Exception as e:
                logger.debug("idle 检测(OCR) scan 异常: %s", e)
                return []

            if not state.found or not state.chat_panel_open:
                return []

            if state.is_busy:
                logger.debug("idle 检测(OCR): Agent 正忙（%s），跳过", state.busy_hint)
                return []

            lang = self.config.lang
            keywords = _WAITING_KEYWORDS_ZH if lang == "zh" else _WAITING_KEYWORDS_EN

            half_h = state.window.height * 0.50 if state.window else 500
            right_half = state.window.width * 0.40 if state.window else 400

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

            role = state.agent_role or "PM"

        if not waiting_hit:
            return []

        role_std = _normalize_role(role)
        now_str = datetime.now().strftime("%H:%M:%S")

        # 冷却：同一角色 60 秒内不重复 kick
        kick_key = f"kick_{role_std}"
        last_kick = self._kick_times.get(kick_key, 0)
        if time.time() - last_kick < 60:
            return []

        logger.info("idle 检测: %s 在等确认 (命中: \"%s\")，自动发「继续」", role, waiting_hit)

        win = find_cursor_window(self.config)
        if not win:
            return []

        hwnd, _ = win
        tpl = _MSG_TEMPLATES.get(lang, _MSG_TEMPLATES["zh"])
        kick_msg = tpl["kick"]

        if switch_and_send(hwnd, role_std, kick_msg,
                           self.config.input_offset):
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
            patrol_trace(
                "idle_kick",
                _T("tr_auto_continue"),
                role=role_std,
                keyword=waiting_hit,
            )

        return events

    def auto_nudge_stuck(self) -> list[dict]:
        if not self._running:
            return []

        # 先检测当前 Agent 是否在忙，忙碌时整体跳过催促
        # CDP 优先（精确检测 Stop 按钮）
        if _cdp_active and HAS_CDP:
            try:
                cdp_st = cdp_scan()
                if cdp_st.found and cdp_st.is_busy:
                    logger.info("auto_nudge: CDP 检测 Agent 正忙（%s），跳过本轮催促", cdp_st.busy_hint)
                    return []
            except Exception:
                pass
        if HAS_VISION:
            try:
                peek = vision_scan()
                if peek.found and peek.is_busy:
                    logger.info("auto_nudge: OCR 检测 Agent 正忙（%s），跳过本轮催促", peek.busy_hint)
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

            win = find_cursor_window(self.config)
            if not win:
                break

            hwnd, _ = win
            mins = int(item["age_seconds"] / 60)
            min_age = float(getattr(self.config, "stuck_reload_min_age_s", 600.0))
            once = bool(getattr(self.config, "stuck_reload_once_per_task", True))
            want_reload = bool(getattr(self.config, "stuck_reload_window", True))
            if want_reload and item["age_seconds"] >= min_age:
                if not once or item["task_id"] not in self._stuck_reload_done:
                    logger.info(
                        "自动催促前 Reload Window（task=%s age≈%.0fs）",
                        item["task_id"],
                        item["age_seconds"],
                    )
                    if reload_cursor_window(self.config):
                        self._stuck_reload_done.add(item["task_id"])
                        wait_r = float(getattr(self.config, "reload_window_wait_s", 12.0))
                        time.sleep(max(3.0, wait_r))
                        win2 = find_cursor_window(self.config)
                        if not win2:
                            logger.warning("Reload 后未找到 Cursor，跳过本轮催促")
                            continue
                        hwnd, _ = win2

            auto_msg = build_nudge_message(
                item["filename"],
                "tasks",
                recipient,
                self.config.lang,
                minutes=max(1, mins),
                config=self.config,
            )
            logger.info("自动催促 %s: %s", recipient, item["task_id"])
            patrol_trace(
                "stuck_check",
                _T("tr_stuck_nudge"),
                task_id=item["task_id"],
                filename=item["filename"],
                recipient=recipient,
                age_min=int(item["age_seconds"] / 60),
            )
            if switch_and_send(hwnd, recipient, auto_msg,
                               self.config.input_offset):
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
                patrol_trace(
                    "stuck_nudge_ok",
                    _T("tr_stuck_sent"),
                    task_id=item["task_id"],
                    recipient=recipient,
                )
            time.sleep(self.config.nudge_cooldown)

        return events

    def greet_all_roles(self):
        """按热键序号顺序（01→02→03→04）依次切换并发打招呼消息。

        逻辑：
        1. 按快捷键（Ctrl+Alt+1/2/3/4）切到对应 Agent Tab
        2. 等待渲染后 OCR 确认顶部激活 Tab 序号与目标一致
        3. 消息内容用该序号对应的角色生成，直接发送
        最多重试 3 次，失败则跳过该角色继续下一个。
        """
        win = find_cursor_window(self.config)
        if not win:
            logger.warning("未找到 Cursor 窗口，跳过打招呼")
            patrol_trace("greet_skip", _T("tr_greet_skip"))
            return

        hwnd, title = win
        logger.info("找到 Cursor 窗口: %s", title[:60])

        # 按 _UI_LABELS 里的序号（01-/02-/03-/04-）排序，无序号的排最后
        def _role_seq(r: str) -> int:
            lbl = _UI_LABELS.get(r.upper(), "")
            m = re.match(r"(\d+)", lbl)
            return int(m.group(1)) if m else 99

        # 从 _UI_LABELS（预检时注册）读取已知角色，按序号排序
        roles_from_labels = list(_UI_LABELS.keys())
        if not roles_from_labels:
            # 兜底：从 tasks/ 中的收件人推断
            roles_from_labels = list({
                re.sub(r'^\d+[-_\s]*', '', r.upper()).strip()
                for r in self._get_active_recipients()
            })
        roles_sorted = sorted(roles_from_labels, key=_role_seq)
        patrol_trace("greet_begin", _T("tr_greet_start"), roles=len(roles_sorted))

        greeted = 0
        _lang = self.config.lang

        for role in roles_sorted:
            if not self._running:
                logger.warning("巡检已停止，中断打招呼")
                return

            patrol_trace("greet_role", _T("tr_greeting"), role=role)
            logger.info("打招呼 → %s", role)

            sent = False

            # ── CDP 快速打招呼 ──
            if _cdp_active and HAS_CDP:
                msg = build_nudge_message("", "", role, _lang, mark_greeted=False)
                logger.info("打招呼(CDP) → %s: %s", role, msg[:60])
                if _switch_and_send_with_cdp(role, role, msg):
                    mark_role_greeted(role)
                    greeted += 1
                    sent = True
                    patrol_trace("greet_ok", _T("tr_greet_cdp"), role=role, attempt=1)
                    logger.info("打招呼成功(CDP) → %s", role)
                    time.sleep(max(float(self.config.nudge_cooldown), 5.0))
                else:
                    logger.info("CDP 打招呼失败，降级 OCR → %s", role)

            # ── OCR 打招呼（CDP 未激活或失败时）──
            if not sent:
              for attempt in range(1, 4):
                focus_window(hwnd)
                state = vision_scan()
                clicked = vision_click_role(state, role)
                if not clicked:
                    logger.warning("打招呼第%d次：侧栏找不到 %s，重试", attempt, role)
                    patrol_trace("greet_retry", _T("tr_sidebar_miss", n=attempt),
                                 role=role, attempt=attempt)
                    time.sleep(3.0)
                    continue
                logger.info("打招呼第%d次：已点击侧栏 %s", attempt, role)
                time.sleep(4.0)

                if HAS_VISION:
                    try:
                        state = vision_scan()
                        confirmed = _is_role_active(state, role)
                        active_tab = ""
                        try:
                            active_tab = get_active_tab_role(state) or ""
                        except Exception:
                            pass
                        logger.info("打招呼第%d次：激活Tab=%s 确认=%s",
                                    attempt, active_tab or "(未识别)", confirmed)
                        if not confirmed:
                            patrol_trace("greet_retry", _T("tr_switch_miss", n=attempt),
                                         role=role, attempt=attempt, active_tab=active_tab)
                            time.sleep(3.0)
                            continue
                    except Exception as e:
                        logger.debug("打招呼 OCR 异常: %s", e)

                msg = build_nudge_message("", "", role, _lang, mark_greeted=False)
                logger.info("打招呼消息: %s", msg[:80])

                if HAS_VISION:
                    try:
                        state = vision_scan()
                        if state.input_box:
                            pyautogui.click(int(state.input_box.cx), int(state.input_box.cy))
                        elif state.window:
                            w = state.window
                            pyautogui.click(w.left + w.width // 2, w.top + int(w.height * 0.92))
                    except Exception:
                        pass
                else:
                    pyautogui.hotkey("ctrl", "l")

                time.sleep(0.5)
                old_clip = ""
                try:
                    old_clip = pyperclip.paste()
                except Exception:
                    pass
                pyperclip.copy(msg)
                time.sleep(0.15)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)
                pyautogui.press("enter")
                time.sleep(0.3)
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass

                mark_role_greeted(role)
                greeted += 1
                sent = True
                patrol_trace("greet_ok", _T("tr_greet_sent"), role=role, attempt=attempt)
                logger.info("打招呼成功 → %s", role)

                time.sleep(max(float(self.config.nudge_cooldown), 8.0))
                break

            if not sent:
                logger.warning("打招呼失败（3次均未成功）: %s，跳过", role)
                patrol_trace("greet_fail", _T("tr_greet_fail"), role=role)

        logger.info("打招呼完成，成功 %d/%d 个角色", greeted, len(roles_sorted))

    def start_patrol(self):
        """启动巡检（由 PWA/面板明确触发）：接手未闭环任务、向各 Agent 问候、立即进入轮询。"""
        if self._running:
            logger.info("巡检已在运行，忽略重复启动")
            return
        _probe_cdp(retries=6, delay=5.0)
        _greeted_roles.clear()
        self._running = True
        self._tick_count = 0
        n_inc = self._bootstrap_pending_tasks()
        self._start_file_observer()
        self._relay_push_version += 1
        logger.info("巡检已启动，监听: %s（未闭环任务 %d 条已入队）", self.config.agents_dir, n_inc)
        patrol_trace(
            "patrol_on",
            _T("tr_patrol_on") + "：" + _T("tr_patrol_on_detail"),
            poll_interval=self.config.poll_interval,
            nudge_cooldown=self.config.nudge_cooldown,
            file_watcher=bool(self._observer),
            incomplete_queued=n_inc,
        )
        try:
            self.greet_all_roles()
        except Exception as e:
            logger.warning("启动问候异常（可稍后重试）: %s", e)
            patrol_trace("greet_error", _T("tr_greet_error"), error=str(e)[:120])
        self._wake_event.set()

    def stop_patrol(self):
        """停止巡检 — 清除所有运行时状态"""
        self._running = False
        self._tick_count = 0
        self._kick_times.clear()
        self._last_nudge_by_recipient.clear()
        self._nudge_pending.clear()
        self._nudge_attempts.clear()
        _greeted_roles.clear()
        self._stop_file_observer()
        logger.info("巡检已停止，所有状态已清除")
        patrol_trace("patrol_off", _T("tr_patrol_off"))

    def start_loop(self):
        """后台轮询线程（仅当 _running=True 时才真正执行操作）"""
        scan_s = max(0.5, float(getattr(self.config, "poll_interval", 5.0)))
        idle_n = max(1, int(getattr(self.config, "idle_check_every_n", 6)))
        stuck_n = max(1, int(getattr(self.config, "stuck_check_every_n", 30)))

        logger.info(
            "轮询线程已就绪（间隔 %.1fs，idle 每 %d 轮，stuck 每 %d 轮）",
            scan_s, idle_n, stuck_n,
        )
        # Connection Error 检测：连续多少轮不动才 reload
        _conn_err_n = max(1, int(getattr(self.config, "conn_error_check_every_n", 1)))
        _last_reload_t: float = 0.0
        _reload_cooldown = float(getattr(self.config, "conn_error_reload_cooldown_s", 120.0))

        try:
            while True:
                if self._running:
                    # ── Connection Error 检测（每轮都检查）──────────────
                    if self._tick_count % _conn_err_n == 0:
                        now = time.time()
                        if now - _last_reload_t > _reload_cooldown:
                            if _check_cursor_connection_error(self.config):
                                logger.warning("检测到 Cursor 异常（Connection Error / Extension Host 卡住），执行 Reload Window")
                                patrol_trace("conn_error_reload", _T("tr_anomaly_reload"))
                                reload_cursor_window(self.config)
                                _last_reload_t = time.time()
                                time.sleep(float(getattr(self.config, "reload_window_wait_s", 12.0)))
                    # ── CDP 延迟探测（未激活时每 30 轮重试一次）────────
                    if not _cdp_active and HAS_CDP and self._tick_count > 0 and self._tick_count % 30 == 0:
                        _probe_cdp(retries=1)
                    # ────────────────────────────────────────────────────
                    self.check_and_nudge()
                    self._tick_count += 1
                    if self._tick_count % stuck_n == 0:
                        self.auto_nudge_stuck()
                    if self._tick_count % idle_n == 0:
                        self.detect_and_kick_idle()
                deadline = time.time() + scan_s
                while time.time() < deadline:
                    rem = deadline - time.time()
                    if rem <= 0:
                        break
                    if self._wake_event.wait(timeout=min(0.25, rem)):
                        self._wake_event.clear()
                        break
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self._stop_file_observer()
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
        inc = list_incomplete_task_files(self.config)
        result["incomplete_tasks"] = len(inc)
        result["incomplete_filenames"] = [x[0] for x in inc[:24]]
        return result

    def get_status(self) -> dict:
        win = find_cursor_window(self.config)
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
            "has_vision": HAS_VISION,
            "has_cdp": HAS_CDP,
            "cdp_active": _cdp_active,
            "poll_interval_s": float(getattr(self.config, "poll_interval", 5.0)),
            "file_observer_active": bool(self._observer),
            "has_watchdog": HAS_WATCHDOG,
            "patrol_tuning": {
                "find_cursor_max_attempts": int(getattr(self.config, "find_cursor_max_attempts", 4)),
                "find_cursor_retry_delay_s": float(getattr(self.config, "find_cursor_retry_delay_s", 0.12)),
                "idle_check_every_n": int(getattr(self.config, "idle_check_every_n", 6)),
                "stuck_check_every_n": int(getattr(self.config, "stuck_check_every_n", 30)),
                "poll_interval_s": float(getattr(self.config, "poll_interval", 5.0)),
                "nudge_cooldown_s": float(getattr(self.config, "nudge_cooldown", 15.0)),
                "task_stuck_threshold_s": float(getattr(self.config, "task_stuck_threshold_s", 600.0)),
                "task_timeout_threshold_s": float(getattr(self.config, "task_timeout_threshold_s", 1200.0)),
                "auto_nudge_interval_s": float(getattr(self.config, "auto_nudge_interval_s", 300.0)),
                "stuck_reload_window": bool(getattr(self.config, "stuck_reload_window", True)),
                "stuck_reload_min_age_s": float(getattr(self.config, "stuck_reload_min_age_s", 600.0)),
                "use_file_watcher": bool(getattr(self.config, "use_file_watcher", True)),
            },
        }
        return status

    def get_cursor_state(self) -> dict:
        """扫描 Cursor 窗口状态。优先 CDP，降级到 OCR。"""
        if _cdp_active:
            try:
                state = cdp_scan()
                if state.found:
                    return state.to_dict()
                logger.info("CDP scan 未找到目标，降级到 OCR")
            except Exception as e:
                logger.info("CDP scan 异常 %s，降级到 OCR", e)
        if not HAS_VISION:
            return {"error": _T("vision_not_loaded"), "has_vision": False, "has_cdp": HAS_CDP}
        try:
            state = vision_scan(save_screenshot=True)
            return state.to_dict()
        except Exception as e:
            return {"error": str(e), "has_vision": True, "has_cdp": HAS_CDP}


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

    MAX_WS_BYTES = 200 * 1024  # 中继已调整为 256KB，留余量

    async def _send_chunked(ws_conn, event_type: str, payload: dict):
        """尝试整包发送；超限则拆分 items 分批发。"""
        full = _make_msg(event_type, payload)
        if len(full.encode("utf-8")) <= MAX_WS_BYTES:
            await ws_conn.send(full)
            return
        items = payload.pop("items", [])
        # 第一包：meta（team_roles + stats，不含 items）
        meta_payload = {**payload, "items": [], "_chunked": True, "_total_items": len(items)}
        await ws_conn.send(_make_msg(event_type, meta_payload))
        # 后续包：逐条发送 items
        batch = []
        for item in items:
            batch.append(item)
            trial = _make_msg(event_type, {"items": batch, "_chunk": True})
            if len(trial.encode("utf-8")) > MAX_WS_BYTES:
                if len(batch) > 1:
                    await ws_conn.send(_make_msg(event_type, {"items": batch[:-1], "_chunk": True}))
                    batch = [batch[-1]]
                else:
                    item["markdown"] = item.get("markdown", "")[:300]
                    item["raw_markdown"] = item.get("raw_markdown", "")[:300]
                    await ws_conn.send(_make_msg(event_type, {"items": batch, "_chunk": True}))
                    batch = []
        if batch:
            await ws_conn.send(_make_msg(event_type, {"items": batch, "_chunk": True}))

    while not _stop.is_set():
        try:
            async with websockets.connect(
                config.relay_url, ping_interval=30, ping_timeout=60, max_size=2**20,
            ) as ws:
                hello = {
                    "room_key": config.room_key,
                    "sender": "Nudger",
                    "client_type": "desktop_nudger",
                    "event_type": "hello",
                    "payload": {
                        "device_id": config.device_id,
                        "device_name": "CodeFlow Desktop",
                        "owner_role": "SYSTEM",
                    },
                }
                await ws.send(json.dumps(hello, ensure_ascii=False))
                global _relay_connected
                _relay_connected = True
                logger.info("已连接中继: %s", config.relay_url)

                # 连接后推送初始 dashboard（3s + 10s 各一次，确保 PWA 收到）
                async def _delayed_init_dashboard():
                    for delay in (3, 10):
                        await asyncio.sleep(delay if delay == 3 else 7)  # 3s 后第一次，再等 7s 第二次
                        try:
                            await _send_chunked(ws, "dashboard_state", _build_dashboard(config, nudger))
                            logger.info("已推送初始 dashboard_state (delay=%ds)", delay)
                        except Exception as _init_exc:
                            logger.warning("推送初始 dashboard 失败: %s", _init_exc)
                            break
                asyncio.ensure_future(_delayed_init_dashboard())

                async def _send(event_type: str, payload: dict):
                    try:
                        msg = _make_msg(event_type, payload)
                        logger.debug("_send %s (%d bytes)", event_type, len(msg.encode("utf-8")))
                        await ws.send(msg)
                    except Exception as _send_exc:
                        logger.warning("_send %s 失败: %s", event_type, _send_exc)

                async def recv_loop():
                    while not _stop.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        except Exception as _recv_exc:
                            logger.warning("recv_loop 异常退出: %s", _recv_exc)
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        et = str(data.get("event_type", ""))
                        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}

                        if et in ("command_from_admin", "admin_command"):
                            admin_text = str(payload.get("text", payload.get("body", ""))).strip()
                            target_role = str(payload.get("target_role", "")).strip()
                            admin_priority = str(payload.get("priority", "P1")).strip() or "P1"

                            if admin_text:
                                filename = _handle_admin_command(
                                    config, admin_text,
                                    target_role=target_role,
                                    priority=admin_priority,
                                )
                                file_list = nudger.get_file_list()
                                await _send("file_list", file_list)
                                await _send("task_created", {
                                    "target_role": target_role or "PM",
                                    "filename": filename,
                                    "text": admin_text[:80],
                                    "status": "ok",
                                })
                                if nudger.running:
                                    resolved = target_role or "PM"
                                    _relay_say_to_cursor(nudger, config, resolved,
                                                         f"收到新任务 {filename}，请查看 docs/agents/tasks/ 并执行")
                            else:
                                if nudger.running:
                                    _relay_say_to_cursor(nudger, config,
                                                         target_role or "PM", "")
                                else:
                                    logger.info("收到空指令但巡检未启动，忽略")

                        elif et == "request_dashboard":
                            await _send_chunked(ws, "dashboard_state", _build_dashboard(config, nudger))

                        elif et == "request_task_detail":
                            fname = str(payload.get("filename", "")).strip()
                            logger.info("收到 request_task_detail: filename=%s", fname)
                            detail = _build_task_detail(config, fname)
                            logger.info("task_detail 响应: filename=%s, has_md=%s, error=%s",
                                        fname, bool(detail.get("markdown")), detail.get("error", ""))
                            await _send("task_detail", detail)

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
                            if result.get("status") == "bound":
                                await _send_chunked(ws, "dashboard_state", _build_dashboard(config, nudger))

                        elif et == "execute_desktop_action":
                            action = str(payload.get("action", "")).strip()
                            result = _handle_desktop_action(action, nudger)
                            await _send("desktop_action_result", result)

                        elif et == "request_agent_live":
                            logger.info("收到 PWA request_agent_live 请求")
                            try:
                                cursor_state = nudger.get_cursor_state()
                                live_payload = {
                                    "found": bool(cursor_state.get("found")),
                                    "has_cdp": cursor_state.get("has_cdp", HAS_CDP),
                                    "cdp_active": _cdp_active,
                                    "agent_role": cursor_state.get("agent_role", ""),
                                    "all_roles": cursor_state.get("all_roles", []),
                                    "agent_status": cursor_state.get("agent_status", "unknown"),
                                    "is_busy": cursor_state.get("is_busy", False),
                                    "busy_hint": cursor_state.get("busy_hint", ""),
                                    "model_name": cursor_state.get("model_name", ""),
                                    "current_mode": cursor_state.get("current_mode", ""),
                                    "message_count": cursor_state.get("message_count", 0),
                                    "pending_approvals": cursor_state.get("pending_approvals", 0),
                                    "recent_messages": cursor_state.get("recent_messages", []),
                                }
                                if cursor_state.get("error"):
                                    live_payload["error"] = str(cursor_state["error"])[:200]
                                await _send("agent_live_state", live_payload)
                                logger.info("已响应 request_agent_live: found=%s role=%s", live_payload["found"], live_payload["agent_role"])
                            except Exception as _req_exc:
                                logger.warning("响应 request_agent_live 失败: %s", _req_exc)
                                await _send("agent_live_state", {"found": False, "error": str(_req_exc)})

                async def _push_desktop_snapshot(reason: str = "interval"):
                    """文件变化时推送列表+轨迹+Agent状态；心跳时推文件列表+Agent状态。"""
                    try:
                        file_list = nudger.get_file_list()
                        await ws.send(_make_msg("file_list", file_list))
                        if reason != "heartbeat":
                            trace = get_patrol_trace(20)
                            slim_trace = []
                            for rec in trace:
                                slim_trace.append({
                                    "t": rec.get("t", ""),
                                    "stage": rec.get("stage", ""),
                                    "detail": (rec.get("detail", "") or "")[:500],
                                })
                            await ws.send(_make_msg("patrol_trace", {
                                "entries": slim_trace,
                                "reason": reason,
                            }))
                        # Agent 实时状态推送（CDP 状态 + 消息摘要）
                        try:
                            cursor_state = nudger.get_cursor_state()
                            live_payload = {
                                "found": bool(cursor_state.get("found")),
                                "has_cdp": cursor_state.get("has_cdp", HAS_CDP),
                                "cdp_active": _cdp_active,
                                "agent_role": cursor_state.get("agent_role", ""),
                                "all_roles": cursor_state.get("all_roles", []),
                                "agent_status": cursor_state.get("agent_status", "unknown"),
                                "is_busy": cursor_state.get("is_busy", False),
                                "busy_hint": cursor_state.get("busy_hint", ""),
                                "model_name": cursor_state.get("model_name", ""),
                                "current_mode": cursor_state.get("current_mode", ""),
                                "message_count": cursor_state.get("message_count", 0),
                                "pending_approvals": cursor_state.get("pending_approvals", 0),
                                "recent_messages": cursor_state.get("recent_messages", []),
                            }
                            if cursor_state.get("error"):
                                live_payload["error"] = str(cursor_state["error"])[:200]
                            msg = _make_msg("agent_live_state", live_payload)
                            msg_kb = len(msg.encode("utf-8")) / 1024
                            await ws.send(msg)
                            logger.info("已推送 agent_live_state (%.1fKB) found=%s role=%s msgs=%d",
                                        msg_kb, live_payload.get("found"), live_payload.get("agent_role", ""), len(live_payload.get("recent_messages", [])))
                        except Exception as _cdp_exc:
                            logger.warning("推送 agent_live_state 失败: %s", _cdp_exc)
                        logger.debug("已推送 PWA 快照 (%s)", reason)
                    except Exception as ex:
                        logger.warning("推送 PWA 快照失败: %s", ex)

                async def poll_and_push():
                    _last_file_snapshot = ""
                    _last_push_ver = -1
                    _push_interval = 5
                    _heartbeat_counter = 0
                    _consecutive_errors = 0
                    while not _stop.is_set():
                        await asyncio.sleep(_push_interval)
                        try:
                            ver = getattr(nudger, "_relay_push_version", 0)
                            file_list = nudger.get_file_list()
                            snapshot = json.dumps(
                                {k: [f["filename"] for f in v if isinstance(f, dict) and "filename" in f]
                                 for k, v in file_list.items()
                                 if isinstance(v, list) and k in ("tasks", "reports", "issues")},
                                sort_keys=True,
                            )
                            changed = snapshot != _last_file_snapshot
                            ver_changed = ver != _last_push_ver
                            if changed:
                                _last_file_snapshot = snapshot
                            if ver_changed:
                                _last_push_ver = ver
                            if changed or ver_changed:
                                await _push_desktop_snapshot("file_change" if changed else "patrol_event")
                                if changed:
                                    try:
                                        await _send_chunked(ws, "dashboard_state", _build_dashboard(config, nudger))
                                    except Exception as _db_exc:
                                        logger.warning("推送 dashboard_state 失败: %s", _db_exc)
                            else:
                                _heartbeat_counter += 1
                                if _heartbeat_counter % 3 == 0:
                                    await _push_desktop_snapshot("heartbeat")
                            _consecutive_errors = 0
                        except websockets.exceptions.ConnectionClosed as _cc:
                            logger.warning("poll_and_push: 连接已关闭 %s，退出", _cc)
                            break
                        except Exception as _poll_exc:
                            _consecutive_errors += 1
                            logger.error("poll_and_push 异常 (#%d): %s", _consecutive_errors, _poll_exc, exc_info=True)
                            if _consecutive_errors >= 5:
                                logger.error("poll_and_push 连续 5 次异常，退出重连")
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

def _read_team_info(config) -> dict:
    """从 codeflow.json 读取团队信息，返回 {roles: [...], team_name: "..."}。"""
    try:
        bf_path = config.agents_dir / "codeflow.json"
        if not bf_path.exists():
            bf_path = config.agents_dir / "bridgeflow.json"
        if not bf_path.exists():
            return {"roles": [], "team_name": ""}
        cfg = json.loads(bf_path.read_text(encoding="utf-8"))
        team_id = cfg.get("team", cfg.get("team_id", "dev-team"))
        team_name = cfg.get("team_name", "")
        role_defs = cfg.get("roles") or []
        if not role_defs:
            TEAM_TEMPLATES = {
                "dev-team":   [{"code":"PM"},{"code":"DEV"},{"code":"QA"},{"code":"OPS"}],
                "media-team": [{"code":"COLLECTOR"},{"code":"WRITER"},{"code":"EDITOR"},{"code":"PUBLISHER"}],
                "mvp-team":   [{"code":"BUILDER"},{"code":"DESIGNER"},{"code":"MARKETER"},{"code":"RESEARCHER"}],
                "qa-team":    [{"code":"LEAD-QA"},{"code":"TESTER"},{"code":"AUTO-TESTER"},{"code":"PERF-TESTER"}],
            }
            role_defs = TEAM_TEMPLATES.get(team_id, [])
        roles = [rd.get("code","").upper() for rd in role_defs if rd.get("code")]
        return {"roles": roles, "team_name": team_name}
    except Exception:
        return {"roles": [], "team_name": ""}


def _build_dashboard(config, nudger: Nudger) -> dict:
    """构建 PWA dashboard_state 响应"""
    items = []
    for d in ["tasks", "reports", "issues", "log"]:
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
            # 正文：去掉 YAML front matter 后的内容（最多 2000 字，够 PWA 展示）
            if text.startswith("---"):
                parts = text.split("---", 2)
                body_text = parts[2].strip() if len(parts) >= 3 else text
            else:
                body_text = text
            summary = front.get("body", front.get("summary", ""))
            if not summary:
                for line in body_text.splitlines():
                    line = line.strip()
                    if line:
                        summary = line.lstrip("# ").strip()[:80]
                        break
            items.append({
                "filename": f.name,
                "dir": d,
                "task_id": front.get("task_id", f.stem),
                "sender": front.get("sender", "") or front.get("reporter", "") or front.get("author", ""),
                "recipient": front.get("recipient", ""),
                "priority": front.get("priority", ""),
                "progress": front.get("progress") or front.get("status", "pending"),
                "type": front.get("type", d.rstrip("s")),
                "created_at": front.get("created_at", ""),
                "thread_key": front.get("thread_key", ""),
                "body": summary,
                "markdown": body_text[:8000],
                "raw_markdown": text[:8000],
            })

    if items:
        i0 = items[0]
        logger.info("_build_dashboard: %d items, 第一条: fn=%s, body=%r, md_len=%d, raw_len=%d, dir=%s",
                     len(items), i0.get("filename"), (i0.get("body",""))[:40],
                     len(i0.get("markdown","")), len(i0.get("raw_markdown","")), i0.get("dir"))
    else:
        logger.info("_build_dashboard: 0 items (agents_dir=%s)", config.agents_dir)

    status = nudger.get_status()
    tasks_count = status.get("tasks_count", 0)
    reports_count = status.get("reports_count", 0)
    stats = status.get("stats", {})
    team_info = _read_team_info(config)

    return {
        "items": items,
        "team_roles": team_info["roles"],
        "team_name": team_info["team_name"],
        "stats": {
            "today_tasks": tasks_count,
            "today_replies": reports_count,
            "in_progress_threads": sum(1 for i in items if i.get("progress") in ("pending", "in_progress")),
            "replied_threads": sum(1 for i in items if i.get("dir") == "reports" and "ADMIN" in str(i.get("recipient", "")).upper()),
            "nudge_ok": stats.get("nudge_ok", 0),
            "nudge_fail": stats.get("nudge_fail", 0),
        },
    }


def _build_patrol_state(nudger: Nudger) -> dict:
    inc = list_incomplete_task_files(nudger.config)
    trace = get_patrol_trace(48)
    return {
        "running": nudger.running,
        "round": nudger._tick_count,
        "incomplete_tasks": len(inc),
        "incomplete_filenames": [x[0] for x in inc[:20]],
        "patrol_trace": trace,
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


def _build_task_detail(config, filename: str) -> dict:
    """根据文件名查找任务文件，返回完整内容给 PWA。"""
    if not filename:
        logger.warning("_build_task_detail: filename 为空")
        return {"error": "missing filename"}
    for d in ["tasks", "reports", "issues", "log"]:
        p = config.agents_dir / d / filename
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                text = ""
            front = {}
            body_text = text
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            front[k.strip()] = v.strip()
                    body_text = parts[2].strip()
            logger.info("_build_task_detail: 找到 %s/%s (%d bytes, body %d bytes)",
                        d, filename, len(text), len(body_text))
            return {
                "filename": filename,
                "task_id": front.get("task_id", ""),
                "sender": front.get("sender", ""),
                "recipient": front.get("recipient", ""),
                "priority": front.get("priority", ""),
                "progress": front.get("progress", "pending"),
                "type": front.get("type", d.rstrip("s")),
                "created_at": front.get("created_at", ""),
                "thread_key": front.get("thread_key", ""),
                "body": front.get("body", front.get("summary", "")),
                "markdown": body_text[:8000],
                "raw_markdown": text[:8000],
            }
    logger.warning("_build_task_detail: 未找到文件 %s (搜索: tasks/reports/issues/log in %s)",
                   filename, config.agents_dir)
    return {"error": "file not found", "filename": filename}


def _build_bind_state(config) -> dict:
    bf_path = config.agents_dir / "codeflow.json"
    if not bf_path.exists():
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
    bf_path = config.agents_dir / "codeflow.json"
    if not bf_path.exists():
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
        win = find_cursor_window(nudger.config)
        if win:
            focus_window(win[0])
            patrol_trace("desktop", _T("tr_relay_focus"), action=action, ok=True)
            return {"action": action, "ok": True, "message": _T("cursor_focused")}
        patrol_trace("desktop", _T("tr_relay_focus_fail"), action=action, ok=False)
        return {"action": action, "ok": False, "message": _T("cursor_win_not_found_s")}
    elif action == "inspect":
        status = nudger.get_status()
        return {"action": action, "ok": True, "message": json.dumps(status, ensure_ascii=False)}
    elif action == "start_work":
        if not nudger.running:
            _relay_start_patrol(nudger)
            return {"action": action, "ok": True, "message": _T("patrol_started")}
        return {"action": action, "ok": True, "message": _T("patrol_already_running")}
    elif action == "stop_work":
        if nudger.running:
            _relay_stop_patrol(nudger)
            return {"action": action, "ok": True, "message": _T("patrol_stopped")}
        return {"action": action, "ok": True, "message": _T("patrol_not_running")}
    elif action == "restart":
        nudger.stop_patrol()
        import time as _time
        _time.sleep(1)
        _relay_start_patrol(nudger)
        patrol_trace("desktop", _T("tr_relay_restart"), action=action, ok=True)
        return {"action": action, "ok": True, "message": _T("patrol_restarted")}
    else:
        return {"action": action, "ok": False, "message": _T("unknown_action", action=action)}


def _handle_admin_command(config, text: str, target_role: str = "",
                          priority: str = "P1") -> str:
    """PWA 发来指令 → 写任务文件到 docs/agents/tasks/，返回文件名"""
    logger.info("收到 PWA 指令: %s", text[:80])
    config.tasks_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    existing = list(config.tasks_dir.glob(f"TASK-{today}-*.md"))
    seq = len(existing) + 1
    task_id = f"TASK-{today}-{seq:03d}"

    leader = target_role.strip().upper() if target_role else "PM"
    if not leader:
        cfg_path = config.agents_dir / "codeflow.json"
        if not cfg_path.exists():
            cfg_path = config.agents_dir / "bridgeflow.json"
        if cfg_path.exists():
            try:
                leader = json.loads(cfg_path.read_text(encoding="utf-8")).get("leader", "PM")
            except Exception:
                leader = "PM"

    filename = f"{task_id}-ADMIN-to-{leader}.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        f"---\nprotocol: agent_bridge\nversion: 1\nkind: task\n"
        f"task_id: {task_id}\nsender: ADMIN\nrecipient: {leader}\n"
        f"created_at: {now_str}\npriority: {priority}\n"
        f"type: admin_command\nsource: ADMIN-mobile\n---\n\n"
        f"# {text[:60]}\n\n"
        f"- 任务类型：`ADMIN请求`\n"
        f"- 发送方：`ADMIN`\n"
        f"- 接收方：`{leader}`\n"
        f"- 优先级：`{priority}`\n"
        f"- 时间：`{now_str}`\n\n"
        f"## 正文\n\n{text}\n"
    )
    (config.tasks_dir / filename).write_text(content, encoding="utf-8")
    logger.info("已写入任务文件: %s", filename)
    return filename


def _relay_say_to_cursor(nudger: 'Nudger', config, role: str, text: str):
    """切到 Cursor 对应角色窗口发送消息"""
    logger.info("通知 Cursor → %s: %s", role, text[:80] if text else "(开工)")
    patrol_trace(
        "relay_notify",
        _T("tr_relay_notify"),
        role=role,
        preview=(text or "")[:60],
    )
    win = find_cursor_window(config)
    if not win:
        logger.warning("未找到 Cursor 窗口，无法通知 Agent")
        return
    hwnd, title = win
    msg = text if text else ("巡检，开工" if config.lang == "zh" else "Patrol, let's go")
    if switch_and_send(hwnd, role, msg, config.input_offset):
        logger.info("已通知 %s", role)
    else:
        logger.warning("通知 %s 失败", role)
