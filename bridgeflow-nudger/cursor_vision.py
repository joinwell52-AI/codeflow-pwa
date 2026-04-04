"""
Cursor 窗口视觉识别模块

职责：截图 Cursor 窗口 → OCR 识别 UI 元素 → 返回结构化状态
不做操作，只负责"看"。

识别目标：
1. Cursor 窗口位置和大小（进程名精确匹配 cursor.exe）
2. 标题栏 / 活跃标签
3. Agent/Chat 面板是否打开
4. 输入框位置（"Ask anything" / "Type your message" 等）
5. 侧边栏状态

依赖：
  pip install winocr Pillow pywin32 pyautogui
  Windows OCR 语言包：
    Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
    zh-CN 通常已预装
"""
from __future__ import annotations

import ctypes
import json
import logging
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import win32gui

logger = logging.getLogger("bridgeflow.vision")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


# ═══════════════════════════════════════════════════════════
#  数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class OcrWord:
    text: str
    rect: Rect


@dataclass
class OcrLine:
    text: str
    words: list[OcrWord]


@dataclass
class CursorWindow:
    hwnd: int
    title: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass
class CursorState:
    found: bool = False
    window: Optional[CursorWindow] = None
    active_tab: str = ""
    chat_panel_open: bool = False
    agent_mode: bool = False
    current_mode: str = ""          # "agent" / "ask" / "chat" / "plan" / ""
    agent_role: str = ""            # 当前 Agent 角色名（如 "I-PM"）
    all_roles: list[str] = field(default_factory=list)  # Tab 栏可见的所有角色
    role_states: dict = field(default_factory=dict)   # {角色名: 状态文字} 如 {"1-PM": "Awaiting plan review"}
    input_box: Optional[Rect] = None
    sidebar_visible: bool = False
    bottom_bar_tabs: list[str] = field(default_factory=list)
    lines: list[OcrLine] = field(default_factory=list)
    raw_text: str = ""
    scan_ms: float = 0
    error: str = ""
    is_busy: bool = False           # 当前活跃 Agent 正在工作
    busy_hint: str = ""             # 触发忙碌判断的关键词

    def to_dict(self) -> dict:
        d = {
            "found": self.found,
            "error": self.error,
            "scan_ms": round(self.scan_ms, 1),
        }
        if self.window:
            d["window"] = {
                "hwnd": self.window.hwnd,
                "title": self.window.title,
                "size": f"{self.window.width}x{self.window.height}",
                "pos": f"({self.window.left},{self.window.top})",
            }
        d["active_tab"] = self.active_tab
        d["current_mode"] = self.current_mode
        d["agent_mode"] = self.agent_mode
        d["agent_role"] = self.agent_role
        d["all_roles"] = self.all_roles
        if self.role_states:
            d["role_states"] = self.role_states
        d["chat_panel_open"] = self.chat_panel_open
        d["sidebar_visible"] = self.sidebar_visible
        d["bottom_bar_tabs"] = self.bottom_bar_tabs
        if self.input_box:
            d["input_box"] = {
                "x": self.input_box.x, "y": self.input_box.y,
                "w": self.input_box.w, "h": self.input_box.h,
                "center": f"({self.input_box.cx:.0f},{self.input_box.cy:.0f})",
            }
        d["is_busy"] = self.is_busy
        if self.busy_hint:
            d["busy_hint"] = self.busy_hint
        d["line_count"] = len(self.lines)
        return d


# ═══════════════════════════════════════════════════════════
#  窗口查找（进程名精确匹配 cursor.exe）
# ═══════════════════════════════════════════════════════════

def _get_exe_path(hwnd: int) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x0410, False, pid.value)
    if not handle:
        return ""
    try:
        buf = (ctypes.c_wchar * 520)()
        psapi.GetModuleFileNameExW(handle, None, buf, 520)
        return buf.value
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(handle)


def find_all_cursor_windows() -> list[CursorWindow]:
    results: list[CursorWindow] = []

    def _enum(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        exe = _get_exe_path(hwnd)
        if exe.lower().endswith("cursor.exe"):
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            if (r - l) > 100 and (b - t) > 100:
                results.append(CursorWindow(hwnd=hwnd, title=title,
                                            left=l, top=t, right=r, bottom=b))

    win32gui.EnumWindows(_enum, None)
    results.sort(key=lambda w: w.width * w.height, reverse=True)
    return results


def find_main_cursor_window() -> Optional[CursorWindow]:
    windows = find_all_cursor_windows()
    if not windows:
        return None
    for w in windows:
        if " - Cursor" in w.title:
            return w
    return windows[0]


# ═══════════════════════════════════════════════════════════
#  截图
# ═══════════════════════════════════════════════════════════

def capture_window(win: CursorWindow):
    """
    截取窗口内容（即使被遮挡也能截到真实内容）。
    优先用 PrintWindow API，失败则回退到屏幕截图。
    """
    from PIL import Image
    try:
        import win32gui
        import win32ui
        import win32con

        hwnd = win.hwnd
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bottom - top
        if w <= 0 or h <= 0:
            raise ValueError(f"窗口尺寸异常: {w}x{h}")

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # PW_RENDERFULLCONTENT = 2, captures even if occluded
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

        if result == 0:
            raise RuntimeError("PrintWindow 返回 0")

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        img = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1,
        )

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return img

    except Exception as e:
        logger.debug("PrintWindow 失败(%s)，回退到屏幕截图", e)
        try:
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=(win.left, win.top, win.right, win.bottom))
        except Exception as e2:
            logger.warning("截图失败: %s", e2)
            return None


# ═══════════════════════════════════════════════════════════
#  OCR（双语：先 en 再 zh-Hans，合并去重）
# ═══════════════════════════════════════════════════════════

def _parse_ocr_result(raw: dict) -> list[OcrLine]:
    lines: list[OcrLine] = []
    for ln in raw.get("lines", []):
        words: list[OcrWord] = []
        for w in ln.get("words", []):
            br = w.get("bounding_rect", {})
            words.append(OcrWord(
                text=w.get("text", ""),
                rect=Rect(br.get("x", 0), br.get("y", 0),
                          br.get("width", 0), br.get("height", 0)),
            ))
        lines.append(OcrLine(text=ln.get("text", ""), words=words))
    return lines


def _ocr_in_thread(img, lang: str) -> dict:
    """总是在独立线程中运行 winocr，确保不与任何 event loop 冲突"""
    import concurrent.futures
    import winocr

    def _run():
        return winocr.recognize_pil_sync(img, lang)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run).result(timeout=10)


def ocr_image(img, lang: str = "en") -> list[OcrLine]:
    """对 PIL Image 做 OCR，返回结构化行列表"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    try:
        raw = _ocr_in_thread(img, lang)
        return _parse_ocr_result(raw)
    except Exception as e:
        logger.warning("OCR(%s) 失败: %s", lang, e)
        return []


def ocr_dual(img) -> list[OcrLine]:
    """英文 + 中文双扫，合并结果（英文为主，中文补漏）"""
    lines_en = ocr_image(img, "en")
    lines_zh = ocr_image(img, "zh-Hans")

    logger.debug("OCR(en) %d 行, OCR(zh) %d 行", len(lines_en), len(lines_zh))

    en_texts = {ln.text.strip().lower() for ln in lines_en}
    merged = list(lines_en)

    for ln in lines_zh:
        if ln.text.strip().lower() not in en_texts:
            merged.append(ln)

    merged.sort(key=lambda ln: (ln.words[0].rect.y if ln.words else 0))
    return merged


# ═══════════════════════════════════════════════════════════
#  UI 状态分析
# ═══════════════════════════════════════════════════════════

_INPUT_HINTS = [
    "ask anything", "type your", "send a message",
    "ask or search", "type a message", "type /",
    "ask a question", "follow-up", "follow up",
    "add a follow",
]

# 只认我们自己起的角色名，Cursor 怎么升级都不影响
# 标准名（含连字符）→ 用于最终输出
_KNOWN_ROLES = ["1-pm", "2-dev", "3-qa", "4-ops",
                "i-pm", "i-dev", "i-ops", "i-qa"]

# OCR 可能把连字符识别成空格、点号或直接丢掉
import re as _re
_ROLE_PATTERNS: list[tuple[_re.Pattern, str]] = []
for _r in _KNOWN_ROLES:
    _prefix, _suffix = _r.split("-", 1)
    # 1-pm → 匹配 "1-pm", "1 pm", "1.pm", "1pm"（前后要有边界）
    pat = _re.compile(
        rf"(?<![a-z0-9]){_re.escape(_prefix)}[\s\-\.]*{_re.escape(_suffix)}(?![a-z0-9])",
        _re.IGNORECASE,
    )
    _ROLE_PATTERNS.append((pat, _r.upper()))


def _find_role_in_text(text: str) -> str:
    """在一段文字里匹配角色名，返回大写标准名或空串"""
    for pat, canonical in _ROLE_PATTERNS:
        if pat.search(text):
            return canonical
    return ""


def analyze(win: CursorWindow, lines: list[OcrLine]) -> CursorState:
    """
    自适应分析 —— 不依赖固定坐标，只靠文字内容和相对位置。

    策略：
    1. 全屏扫描找角色名 → 记录每个角色的 (x, y) 坐标
    2. 角色名位置聚类 → 反推布局（水平排列=Tab / 垂直排列=列表）
    3. 输入框：先找 placeholder，再找角色名附近的可输入行
    4. 模式标签："agent" / "ask" 文字出现就标记
    """
    state = CursorState(found=True, window=win, lines=lines)

    if not lines:
        state.error = "OCR 未识别到文字"
        return state

    full_lower = " ".join(ln.text.lower() for ln in lines)
    state.raw_text = full_lower

    # 活跃标签（从窗口标题取）
    if " - Cursor" in win.title:
        state.active_tab = win.title.split(" - Cursor")[0].strip()

    # ══════════════════════════════════════════════════════
    # Step 1: 全屏搜索角色名（不限区域，保留全部出现位置）
    # ══════════════════════════════════════════════════════
    role_hits: list[dict] = []  # {role, x, y, line_text}
    author_role = ""  # "• Author" 行里的角色 = 最高优先级

    for ln in lines:
        if not ln.words:
            continue
        role = _find_role_in_text(ln.text)
        if role:
            fw = ln.words[0]
            role_hits.append({
                "role": role,
                "x": fw.rect.x,
                "y": fw.rect.y,
                "text": ln.text.strip(),
            })
            # "Author" 标记 = 当前正在对话的角色（最高优先级）
            if "author" in ln.text.lower() and not author_role:
                author_role = role

    # 去重角色列表（供 all_roles 展示用）
    seen_roles: set[str] = set()
    unique_roles: list[str] = []
    for h in role_hits:
        if h["role"] not in seen_roles:
            seen_roles.add(h["role"])
            unique_roles.append(h["role"])

    state.all_roles = unique_roles

    # ══════════════════════════════════════════════════════
    # Step 1.5: Pinned 面板检测 + 竖排状态读取
    # ══════════════════════════════════════════════════════
    pinned_line = None
    for ln in lines:
        if ln.text.strip().lower() == "pinned" and ln.words:
            pinned_line = ln
            break

    # 如果有 Pinned 面板，尝试从面板区域恢复 OCR 漏掉的角色
    if pinned_line:
        pin_x = pinned_line.words[0].rect.x
        pin_y = pinned_line.words[0].rect.y
        # 扫描 Pinned 下方、同一 x 区域的所有行
        panel_lines = []
        for ln in lines:
            if not ln.words:
                continue
            fw = ln.words[0]
            dx = abs(fw.rect.x - pin_x)
            dy = fw.rect.y - pin_y
            # 在 Pinned 下方 10~500px、水平偏移 < 100px
            if 10 < dy < 500 and dx < 100:
                panel_lines.append(ln)
        panel_lines.sort(key=lambda l: l.words[0].rect.y)

        # 推断缺失角色：如果某行带 "@" 前缀且含角色名 → 补充到 role_hits
        # 如果某状态行（如 "Awaiting plan review"）上方没有角色行 → 猜测缺失角色
        _PINNED_EXPECTED = {"1-PM", "2-DEV", "3-QA", "4-OPS"}
        found_in_panel = {h["role"] for h in role_hits
                          if abs(h["x"] - pin_x) < 100}

        missing = _PINNED_EXPECTED - found_in_panel
        if missing and panel_lines:
            first_role_y = None
            for h in role_hits:
                if abs(h["x"] - pin_x) < 100:
                    if first_role_y is None or h["y"] < first_role_y:
                        first_role_y = h["y"]

            if first_role_y is not None:
                # 在第一个识别到的角色 *上方* 有状态行 → 那是缺失角色的状态
                for ln in panel_lines:
                    if not ln.words:
                        continue
                    fw = ln.words[0]
                    if fw.rect.y < first_role_y and not _find_role_in_text(ln.text):
                        # 状态行在所有已知角色上方 → 属于缺失的角色
                        # 取 y 最接近 Pinned 的缺失角色（通常是列表第一个）
                        for m in sorted(missing):
                            role_hits.append({
                                "role": m,
                                "x": pin_x,
                                "y": pin_y + 15,  # 估算位置
                                "text": f"[inferred] {m}",
                            })
                            if m not in seen_roles:
                                seen_roles.add(m)
                                unique_roles.insert(0, m)
                            state.all_roles = unique_roles
                            # 把这个状态行关联到推断的角色
                            txt = ln.text.strip()
                            if len(txt) >= 3:
                                state.role_states[m] = txt
                            missing.discard(m)
                            break

    # 竖排布局时，读取每个角色下方的状态文字
    if len(role_hits) >= 2:
        y_spread = max(h["y"] for h in role_hits) - min(h["y"] for h in role_hits)
        x_spread = max(h["x"] for h in role_hits) - min(h["x"] for h in role_hits)
        is_vertical = y_spread > x_spread

        if is_vertical:
            sorted_lines = sorted(lines, key=lambda l: l.words[0].rect.y if l.words else 9999)

            for rh in role_hits:
                if rh["role"] in state.role_states:
                    continue  # 已经通过推断赋值
                role_y = rh["y"]
                role_x = rh["x"]
                for ln in sorted_lines:
                    if not ln.words:
                        continue
                    fw = ln.words[0]
                    dy = fw.rect.y - role_y
                    dx = abs(fw.rect.x - role_x)
                    if 5 < dy < 40 and dx < 80:
                        txt = ln.text.strip()
                        if _find_role_in_text(txt):
                            continue
                        if len(txt) >= 3:
                            state.role_states[rh["role"]] = txt
                            break

    # ══════════════════════════════════════════════════════
    # Step 2: 判定激活角色
    #
    # 优先级（从高到低）：
    #   1. "Author" 行中的角色名（100% 可信）
    #   2. 聚类离群：列表群之外独立出现的角色名
    #   3. 兜底：第一个角色
    # ══════════════════════════════════════════════════════
    if unique_roles:
        state.agent_mode = True
        state.chat_panel_open = True
        state.current_mode = "agent"

    # Priority 1: Author 标记
    if author_role:
        state.agent_role = author_role

    # Priority 2: 聚类分离
    if not state.agent_role and len(role_hits) >= 3:
        from collections import Counter
        x_buckets: Counter = Counter()
        for h in role_hits:
            x_buckets[int(h["x"] / 50) * 50] += 1

        if x_buckets:
            list_bucket = max(x_buckets, key=x_buckets.get)
            list_x_center = list_bucket + 25
            list_tolerance = win.width * 0.10

            cluster_roles = []
            outlier_roles = []
            for h in role_hits:
                if abs(h["x"] - list_x_center) < list_tolerance:
                    cluster_roles.append(h)
                else:
                    outlier_roles.append(h)

            if cluster_roles:
                avg_x = sum(h["x"] for h in cluster_roles) / len(cluster_roles)
                if avg_x > win.width * 0.55 or avg_x < win.width * 0.35:
                    state.sidebar_visible = True

            if outlier_roles:
                state.agent_role = outlier_roles[0]["role"]

    # Priority 3: 兜底
    if not state.agent_role and unique_roles:
        state.agent_role = unique_roles[0]

    # ══════════════════════════════════════════════════════
    # Step 3: 全屏搜索模式标签（"Agent" / "Ask" 等）
    # ══════════════════════════════════════════════════════
    mode_tabs = {"agent", "ask", "chat", "manual"}
    for ln in lines:
        if not ln.words:
            continue
        txt = ln.text.lower().strip()
        if txt in mode_tabs:
            state.bottom_bar_tabs.append(txt)
            if not state.current_mode:
                state.current_mode = txt
                state.chat_panel_open = True
                if txt == "agent":
                    state.agent_mode = True

    if state.agent_mode and not state.current_mode:
        state.current_mode = "agent"
    if state.current_mode in ("agent", "ask", "chat"):
        state.chat_panel_open = True

    # ══════════════════════════════════════════════════════
    # Step 4: 输入框检测（自适应，不依赖固定坐标）
    # ══════════════════════════════════════════════════════

    # 方式1：placeholder 文字（Cursor 的输入框提示文字）
    for ln in lines:
        ln_lower = ln.text.lower()
        for hint in _INPUT_HINTS:
            if hint in ln_lower and ln.words:
                fw, lw = ln.words[0], ln.words[-1]
                state.input_box = Rect(
                    win.left + fw.rect.x,
                    win.top + fw.rect.y,
                    max((lw.rect.x + lw.rect.w) - fw.rect.x, 300),
                    max(fw.rect.h, 25),
                )
                break
        if state.input_box:
            break

    # 方式2：找 "Author" 标记行附近的输入行
    if not state.input_box and state.chat_panel_open:
        for h in role_hits:
            if "author" not in h["text"].lower():
                continue
            author_y = h["y"]
            # Author 行下方找最近的非角色行
            for ln in sorted(lines, key=lambda l: l.words[0].rect.y if l.words else 9999):
                if not ln.words:
                    continue
                fw = ln.words[0]
                if fw.rect.y <= author_y:
                    continue
                if fw.rect.y > author_y + win.height * 0.10:
                    break
                txt_lower = ln.text.lower().strip()
                if _find_role_in_text(txt_lower):
                    continue
                if len(txt_lower) < 2:
                    continue
                lw = ln.words[-1]
                state.input_box = Rect(
                    win.left + fw.rect.x,
                    win.top + fw.rect.y,
                    max((lw.rect.x + lw.rect.w) - fw.rect.x, 300),
                    max(fw.rect.h, 25),
                )
                break
            break

    # 方式3：底部区域找模型名（"Opus"/"Sonnet"）→ 输入框在其上方
    if not state.input_box and state.chat_panel_open:
        for ln in lines:
            if not ln.words:
                continue
            txt_lower = ln.text.lower()
            if any(m in txt_lower for m in ["opus", "sonnet", "claude", "gpt",
                                            "agent v ", "agent ▾ "]):
                fw = ln.words[0]
                input_y = fw.rect.y - 50
                if input_y < 0:
                    input_y = fw.rect.y
                state.input_box = Rect(
                    win.left + fw.rect.x,
                    win.top + input_y,
                    500, 30,
                )
                break

    # ══════════════════════════════════════════════════════
    # Step 5: Agent 忙碌检测
    # ══════════════════════════════════════════════════════
    _BUSY_KEYWORDS = [
        "awaiting", "in progress", "plan review", "mode switch", "working on",
        "generating", "thinking", "reasoning",
        "searching", "indexing",
        "reading file", "writing file",
        "editing", "creating",
        "applying", "executing", "installing",
        "tool call", "calling tool",
        "looking at", "checking",
        "analyzing", "processing",
        "fetching", "downloading",
        "committing", "pushing",
        "正在生成", "正在思考", "正在搜索",
        "正在读取", "正在写入", "正在编辑",
        "正在执行", "正在安装", "正在运行",
        "正在分析", "正在处理",
    ]

    # 优先用 role_states（竖排列表布局，最可靠）
    if state.role_states:
        for role, st_text in state.role_states.items():
            st_lower = st_text.lower()
            for kw in _BUSY_KEYWORDS:
                if kw in st_lower:
                    state.is_busy = True
                    state.busy_hint = f"{role}: {st_text}"
                    break
            if state.is_busy:
                break

    # 水平 Tab 布局 / 兜底：扫描聊天区域（下半屏）
    if not state.is_busy and state.chat_panel_open:
        half_h = win.height * 0.4
        for ln in lines:
            if not ln.words:
                continue
            fw = ln.words[0]
            if fw.rect.y < half_h:
                continue
            txt_lower = ln.text.lower().strip()
            if len(txt_lower) < 3:
                continue
            for kw in _BUSY_KEYWORDS:
                if kw in txt_lower:
                    state.is_busy = True
                    state.busy_hint = kw
                    break
            if state.is_busy:
                break

    # 补充：独立的 "Stop" 按钮 = 正在生成
    if not state.is_busy:
        for ln in lines:
            if not ln.words:
                continue
            txt = ln.text.strip()
            if txt.lower() in ("stop", "cancel", "停止"):
                state.is_busy = True
                state.busy_hint = txt.lower()
                break

    return state


# ═══════════════════════════════════════════════════════════
#  一键扫描
# ═══════════════════════════════════════════════════════════

def scan(save_screenshot: bool = False,
         screenshot_path: str = "cursor_screenshot.png") -> CursorState:
    t0 = time.perf_counter()

    win = find_main_cursor_window()
    if not win:
        return CursorState(found=False, error="未找到 Cursor 窗口",
                           scan_ms=(time.perf_counter() - t0) * 1000)

    img = capture_window(win)
    if not img:
        return CursorState(found=True, window=win, error="截图失败",
                           scan_ms=(time.perf_counter() - t0) * 1000)

    if save_screenshot:
        img.save(screenshot_path)

    lines = ocr_dual(img)
    state = analyze(win, lines)
    state.scan_ms = (time.perf_counter() - t0) * 1000
    return state


# ═══════════════════════════════════════════════════════════
#  定位输入框并点击（供 nudger 调用）
# ═══════════════════════════════════════════════════════════

def click_input_box(state: CursorState) -> bool:
    """如果识别到输入框，点击其中心；返回是否成功"""
    if not state.input_box:
        return False
    import pyautogui
    x, y = int(state.input_box.cx), int(state.input_box.cy)
    pyautogui.click(x, y)
    return True


def find_keyword_position(state: CursorState, keyword: str) -> Optional[tuple[int, int]]:
    """在 OCR 结果中搜索关键词，返回屏幕绝对坐标 (x, y) 或 None"""
    if not state.found or not state.window:
        return None
    kw = keyword.lower()
    for ln in state.lines:
        if kw not in ln.text.lower():
            continue
        for w in ln.words:
            if kw in w.text.lower():
                abs_x = int(state.window.left + w.rect.cx)
                abs_y = int(state.window.top + w.rect.cy)
                return (abs_x, abs_y)
        if ln.words:
            fw = ln.words[0]
            abs_x = int(state.window.left + fw.rect.cx)
            abs_y = int(state.window.top + fw.rect.cy)
            return (abs_x, abs_y)
    return None


def click_keyword(state: CursorState, keyword: str) -> bool:
    """在 OCR 结果中搜索关键词并点击；返回是否成功"""
    pos = find_keyword_position(state, keyword)
    if not pos:
        return False
    import pyautogui
    pyautogui.click(pos[0], pos[1])
    return True


def click_role(state: CursorState, role: str) -> bool:
    """在 Agent 列表/Tab 栏中点击指定角色名切换；返回是否成功"""
    return click_keyword(state, role)


# ═══════════════════════════════════════════════════════════
#  独立运行：测试识别效果
# ═══════════════════════════════════════════════════════════

def _test():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    SEP = "=" * 60
    print(SEP)
    print("  Cursor 窗口视觉识别器 — 测试模式")
    print(SEP)

    # Step 1: 查找窗口
    print("\n[1] 查找 Cursor 窗口...")
    windows = find_all_cursor_windows()
    if not windows:
        print("  × 未找到任何 Cursor 窗口")
        print("  请先打开 Cursor 再运行此程序")
        sys.exit(1)

    print(f"  找到 {len(windows)} 个 Cursor 窗口:")
    for i, w in enumerate(windows):
        print(f"    [{i}] hwnd={w.hwnd}  \"{w.title}\"  {w.width}x{w.height}")

    main_win = find_main_cursor_window()
    print(f"\n  主窗口: \"{main_win.title}\" ({main_win.width}x{main_win.height})")

    # Step 2: 截图
    print("\n[2] 截取窗口...")
    img = capture_window(main_win)
    if not img:
        print("  × 截图失败")
        sys.exit(1)
    save_path = Path("cursor_screenshot.png")
    img.save(save_path)
    print(f"  截图已保存: {save_path.absolute()} ({img.size[0]}x{img.size[1]})")

    # Step 3: OCR（英文）
    print("\n[3] OCR 识别（EN）...")
    t0 = time.perf_counter()
    lines_en = ocr_image(img, "en")
    ms_en = (time.perf_counter() - t0) * 1000
    print(f"  EN: {len(lines_en)} 行, {ms_en:.0f}ms")
    for ln in lines_en[:15]:
        first = ln.words[0] if ln.words else None
        pos = f"[{first.rect.x:.0f},{first.rect.y:.0f}]" if first else "[?,?]"
        print(f"    {pos} {ln.text}")
    if len(lines_en) > 15:
        print(f"    ... 共 {len(lines_en)} 行")

    # Step 4: OCR（中文）
    print("\n[4] OCR 识别（ZH）...")
    t0 = time.perf_counter()
    lines_zh = ocr_image(img, "zh-Hans")
    ms_zh = (time.perf_counter() - t0) * 1000
    print(f"  ZH: {len(lines_zh)} 行, {ms_zh:.0f}ms")
    for ln in lines_zh[:15]:
        first = ln.words[0] if ln.words else None
        pos = f"[{first.rect.x:.0f},{first.rect.y:.0f}]" if first else "[?,?]"
        print(f"    {pos} {ln.text}")
    if len(lines_zh) > 15:
        print(f"    ... 共 {len(lines_zh)} 行")

    # Step 5: 合并+分析
    print("\n[5] 双语合并 + UI 分析...")
    lines_all = ocr_dual(img)
    state = analyze(main_win, lines_all)

    print(f"\n  窗口标题:  {main_win.title}")
    print(f"  窗口尺寸:  {main_win.width}x{main_win.height}")
    print(f"  活跃标签:  {state.active_tab}")
    print(f"  当前模式:  {state.current_mode or '(未检测到)'}")
    print(f"  Agent角色: {state.agent_role or '(无)'}  全部: {state.all_roles}")
    print(f"  聊天面板:  {'开' if state.chat_panel_open else '关'}")
    print(f"  Agent模式: {'是' if state.agent_mode else '否'}")
    print(f"  侧边栏:    {'显示' if state.sidebar_visible else '隐藏'}")
    print(f"  底部标签:  {state.bottom_bar_tabs or '(无)'}")
    if state.input_box:
        ib = state.input_box
        print(f"  输入框:    ({ib.x:.0f},{ib.y:.0f}) {ib.w:.0f}x{ib.h:.0f}  "
              f"中心=({ib.cx:.0f},{ib.cy:.0f})")
    else:
        print("  输入框:    未识别到")
    if state.error:
        print(f"  错误:      {state.error}")

    # Step 6: JSON 输出
    result = state.to_dict()
    print(f"\n[6] JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Step 7: 保存完整 OCR 结果
    full_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": result,
        "ocr_en_lines": len(lines_en),
        "ocr_zh_lines": len(lines_zh),
        "ocr_merged_lines": len(lines_all),
        "all_lines": [{"text": ln.text,
                        "x": ln.words[0].rect.x if ln.words else -1,
                        "y": ln.words[0].rect.y if ln.words else -1}
                       for ln in lines_all],
    }
    report_path = Path("cursor_vision_report.json")
    report_path.write_text(json.dumps(full_output, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"\n  完整报告: {report_path.absolute()}")

    print(f"\n{SEP}")
    print(f"  识别完成（截图: cursor_screenshot.png）")
    print(SEP)


if __name__ == "__main__":
    _test()
