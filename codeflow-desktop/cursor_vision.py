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

logger = logging.getLogger("codeflow.vision")

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
    pinned_active_role: str = ""    # 侧栏图钉标记的当前激活 Agent（最可靠）
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
    role_positions: dict = field(default_factory=dict)  # {角色名: (abs_x, abs_y)} 来自 Pinned 区域
    screenshot: object = None            # 扫描时的截图（PIL Image），供亮度分析复用

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

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


def get_process_exe_path(hwnd: int) -> str:
    """
    解析窗口所属进程的可执行文件路径。
    优先使用 PROCESS_QUERY_LIMITED_INFORMATION + QueryFullProcessImageName，
    在部分机器上比 VM_READ 方案更不易因权限/会话差异而间歇失败。
    """
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    # 先试低权限句柄（跨完整性级别时 OpenProcess 更容易成功）
    for access in (PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_QUERY_INFORMATION | PROCESS_VM_READ):
        handle = kernel32.OpenProcess(access, False, pid.value)
        if not handle:
            continue
        try:
            buf = (ctypes.c_wchar * 520)()
            size = wintypes.DWORD(520)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return buf.value
            buf2 = (ctypes.c_wchar * 520)()
            psapi.GetModuleFileNameExW(handle, None, buf2, 520)
            if buf2.value:
                return buf2.value
        except Exception:
            pass
        finally:
            kernel32.CloseHandle(handle)
    return ""


def _get_exe_path(hwnd: int) -> str:
    return get_process_exe_path(hwnd)


def find_all_cursor_windows() -> list[CursorWindow]:
    results: list[CursorWindow] = []

    def _enum(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        # Electron 偶发空标题；仍以进程名为准，避免「已开 Cursor 却枚举不到」
        title = win32gui.GetWindowText(hwnd) or ""
        exe = get_process_exe_path(hwnd)
        if not exe.lower().endswith("cursor.exe"):
            return
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        if (r - l) > 100 and (b - t) > 100:
            display = title if title.strip() else "Cursor"
            results.append(CursorWindow(hwnd=hwnd, title=display,
                                        left=l, top=t, right=r, bottom=b))

    win32gui.EnumWindows(_enum, None)
    results.sort(key=lambda w: w.width * w.height, reverse=True)
    return results


def find_main_cursor_window() -> Optional[CursorWindow]:
    """找到主 Cursor 编辑器窗口（排除 CodeFlow 控制面板自身）。
    控制面板标题含「控制面板」，Agent 聊天窗口不含，以此区分。
    """
    windows = find_all_cursor_windows()
    if not windows:
        return None
    # 第一优先：含 " - Cursor" 且不含「控制面板」
    for w in windows:
        if " - Cursor" in w.title and "控制面板" not in w.title:
            return w
    # 第二优先：含 " - Cursor"（包括控制面板，兜底）
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
        logger.warning("PrintWindow 失败(%s)，回退到屏幕截图", e)
        try:
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=(win.left, win.top, win.right, win.bottom),
                                  all_screens=True)
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


def check_ocr_languages() -> dict:
    """
    检查 Windows OCR 语言包，缺少的自动后台安装（需管理员权限）。
    返回 {"en": True/False, "zh": True/False, "missing": [], "installing": []}
    """
    result = {"en": False, "zh": False, "missing": [], "installing": []}
    try:
        import winocr
        # 兼容旧版 winocr（无 get_available_recognizer_languages）
        if hasattr(winocr, "get_available_recognizer_languages"):
            available = winocr.get_available_recognizer_languages()
            tags = [str(l).lower() for l in available]
        else:
            # 旧版：直接尝试识别一张空白图来检测语言包
            import PIL.Image as _PI
            _blank = _PI.new("RGB", (10, 10), (255, 255, 255))
            tags = []
            for _lang in ("en", "zh-Hans"):
                try:
                    winocr.recognize_pil_sync(_blank, _lang)
                    tags.append(_lang)
                except Exception as _le:
                    if "language" not in str(_le).lower() and "recognizer" not in str(_le).lower():
                        tags.append(_lang)  # 其他错误不代表语言包缺失
        result["en"] = any("en" in t for t in tags)
        result["zh"] = any("zh" in t or "chinese" in t for t in tags)
        if not result["en"]:
            result["missing"].append("en-US")
        if not result["zh"]:
            result["missing"].append("zh-Hans")
    except Exception as e:
        logger.warning("OCR 语言检测失败: %s", e)
        return result

    # 自动后台安装缺失的语言包（用 ShellExecuteW runas 提权）
    if result["missing"]:
        import subprocess, threading, ctypes

        def _install(lang_tag: str):
            cap_name = f"Language.OCR~~~{lang_tag}~0.0.1.0"
            ps_cmd = f"Add-WindowsCapability -Online -Name '{cap_name}'"
            try:
                logger.info("[OCR] 尝试安装语言包（需管理员权限）: %s", cap_name)
                # 先尝试直接运行（已是管理员时有效）
                ret = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive",
                     "-Command", ps_cmd],
                    capture_output=True, timeout=120,
                    creationflags=0x08000000  # CREATE_NO_WINDOW
                )
                if ret.returncode == 0:
                    logger.info("[OCR] 语言包安装成功: %s", cap_name)
                    return
                # 不是管理员，用 ShellExecuteW runas 提权
                logger.info("[OCR] 非管理员，尝试 UAC 提权安装: %s", cap_name)
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "powershell",
                    f'-NoProfile -NonInteractive -Command "{ps_cmd}"',
                    None, 0  # SW_HIDE
                )
                logger.info("[OCR] 已请求 UAC 提权安装: %s", cap_name)
            except Exception as e:
                logger.warning("[OCR] 语言包安装失败 %s: %s", cap_name, e)

        for lang in result["missing"]:
            result["installing"].append(lang)
            threading.Thread(target=_install, args=(lang,), daemon=True).start()

    return result


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
    """英文 + 中文并行双扫，合并结果（英文为主，中文补漏）"""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(ocr_image, img, "en")
        fut_zh = pool.submit(ocr_image, img, "zh-Hans")
        lines_en = fut_en.result()
        lines_zh = fut_zh.result()

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
    # Cursor Agent 模式输入框 placeholder
    "plan, build", "plan,build", "/ for commands", "@ for context",
    "for commands", "for context",
    # 通用
    "ask anything", "type your", "send a message",
    "ask or search", "type a message", "type /",
    "ask a question", "follow-up", "follow up",
    "add a follow",
]

import re as _re

# ─── Agent 命名规范：强制 01-NAME 格式 ───────────────────────────────
# 用户必须在 Cursor 中将 Agent 命名为 01-XXX / 02-XXX / 03-XXX / 04-XXX
# OCR 容错：数字前缀中 0→O/o、1→I/l/i，连字符→空格/点
#
# _RE_AGENT_LABEL  : 匹配侧栏 Agent 标题行，提取 (序号, 后缀名)
# _RE_AGENT_STRICT : 仅匹配规范格式（用于 Pinned 列精确提取）

_RE_AGENT_LABEL = _re.compile(
    r'(?:^|(?<=\s))'           # 行首或空格后
    r'([0O][0-9OoIil1])'       # 两位数字前缀（容错 0→O, 1→I/l）
    r'[\s\-\.]+'               # 连字符/空格/点（容错）
    r'([A-Za-z][A-Za-z0-9\-]+)',  # 后缀：字母开头，允许字母数字和连字符
)

# 严格匹配，用于从一行文字提取标准 "NN-NAME" 标签
_RE_AGENT_STRICT = _re.compile(
    r'\b(\d{1,2})[\s\-\.]+([A-Za-z][A-Za-z0-9\-]+)\b'
)


def _extract_agent_label(text: str) -> str:
    """
    从一行 OCR 文字中提取 Agent 标签，返回规范大写形式如 "01-PM"，或空串。
    强制要求：必须有数字前缀（01-、02- 等）+ 字母后缀。
    OCR 容错：O→0，I/l→1，连字符→空格/点。
    """
    text = text.strip()
    if not text:
        return ""

    # 先规范化 OCR 常见误读（仅处理前两个字符可能是数字的情况）
    normalized = text
    # 行首的 O 极可能是 0（在两位数字前缀场景下）
    normalized = _re.sub(r'^O(\d)', r'0\1', normalized)
    normalized = _re.sub(r'^(\d)I', r'\g<1>1', normalized)
    normalized = _re.sub(r'^([0O][0-9OoIil1])[\s\.\,]+', r'\1-', normalized)

    m = _RE_AGENT_STRICT.match(normalized)
    if m:
        num = int(m.group(1))
        suffix = m.group(2).upper()
        return f"{num:02d}-{suffix}"

    # 容错：再试原始文字
    m2 = _RE_AGENT_LABEL.search(text)
    if m2:
        num_str = m2.group(1).upper().replace('O', '0').replace('I', '1').replace('L', '1')
        try:
            num = int(num_str)
        except ValueError:
            num = 0
        suffix = m2.group(2).upper()
        if 1 <= num <= 99 and suffix:
            return f"{num:02d}-{suffix}"

    return ""


def register_roles(labels: list[str]) -> None:
    """兼容旧接口，现在不需要预注册，动态识别。"""
    pass


def register_confirmed_roles(labels: list[str]) -> None:
    """兼容旧接口。"""
    pass


def _find_role_in_text(text: str) -> str:
    """从文字中提取 Agent 标签（01-NAME 格式），返回规范大写或空串。"""
    return _extract_agent_label(text)


def _agent_seq(role: str) -> int:
    """从 '01-PM' 提取序号整数，用于排序；未匹配返回 99。"""
    m = _re.match(r'^(\d+)-', role)
    return int(m.group(1)) if m else 99


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
    # Step 1: 找 Pinned 侧栏 → 提取 Agent 列表（主路径）
    #
    # 支持两种布局（左侧 / 右侧竖列），不限位置。
    # 命名规范：01-NAME、02-NAME ... 两位数字前缀 + 字母后缀。
    # OCR 容错：0→O、1→I/l，连字符→空格/点。
    # ══════════════════════════════════════════════════════

    role_hits: list[dict] = []   # 侧栏内识别到的 Agent 行
    author_role = ""             # 当前激活的角色（"Author" 标记）

    pinned_line = None
    for ln in lines:
        txt = ln.text.strip().lower()
        if (txt == "pinned" or txt == "pinned agents") and ln.words:
            pinned_line = ln
            break

    if pinned_line:
        pin_x = pinned_line.words[0].rect.x
        pin_y = pinned_line.words[0].rect.y
        state.sidebar_visible = True

        # 侧栏水平范围（Pinned 标题 ±150px）
        x_min = pin_x - 30
        x_max = pin_x + 150

        # 收集 Pinned 下方侧栏列内的行，按 y 排序
        panel_lines = [
            ln for ln in lines
            if ln.words
            and x_min <= ln.words[0].rect.x <= x_max
            and 8 < ln.words[0].rect.y - pin_y < 700
        ]
        panel_lines.sort(key=lambda l: l.words[0].rect.y)

        # 去重：按序号，同序号只取第一个（OCR 双重识别兜底）
        seen_seqs: set[int] = set()
        for ln in panel_lines:
            role = _find_role_in_text(ln.text)
            if not role:
                continue
            seq = _agent_seq(role)
            if seq in seen_seqs:
                continue
            seen_seqs.add(seq)
            fw = ln.words[0]
            role_hits.append({
                "role": role,
                "x": fw.rect.x,
                "y": fw.rect.y,
                "text": ln.text.strip(),
            })
            raw_text = ln.text.strip()
            logger.debug("[role_hit] role=%s raw=%r prefix_chars=%s",
                         role, raw_text[:20],
                         [hex(ord(c)) for c in raw_text[:5]])
            # 图钉前缀 = 当前激活 Agent
            _PIN_CHARS = {'\U0001F4CC', '\U0001F4CD', '\U0001F588',
                          '\u272F', '\u2756', '\u2316'}
            if raw_text and raw_text[0] in _PIN_CHARS:
                author_role = role
                state.pinned_active_role = role
                logger.debug("[role_hit] 图钉激活: %s (U+%04X)", role, ord(raw_text[0]))
            # 当前 Agent 标记（被选中行通常出现在主视图"Author"标注）
            elif "author" in ln.text.lower():
                author_role = role

        # 按序号排序
        role_hits.sort(key=lambda h: _agent_seq(h["role"]))

    # ── 激活高亮行补偿：侧栏被选中行因背景高亮导致 OCR 识别失败 ──
    # Cursor 选中某 Agent 后，该行背景变亮（高亮），OCR 有时认不出来。
    # 策略：如果 role_hits 数量比预期少，尝试用截图亮度找"缺失"行，
    # 并根据相邻行的序号推断其角色名。
    if pinned_line and len(role_hits) >= 1:
        try:
            # 找出已识别行之间的 y 间距（估算每行高度）
            if len(role_hits) >= 2:
                y_vals = sorted(h["y"] for h in role_hits)
                row_height = (y_vals[-1] - y_vals[0]) / (len(y_vals) - 1)
            else:
                row_height = 30.0  # 默认估算行高

            # 检查序号是否连续，找出缺失的序号
            seqs_found = sorted(_agent_seq(h["role"]) for h in role_hits)
            if seqs_found and seqs_found[0] <= 4:
                expected_count = seqs_found[-1]  # 从1到最大序号应连续
                for missing_seq in range(1, expected_count + 1):
                    if missing_seq in seqs_found:
                        continue
                    # 推算缺失行的 y 坐标（线性插值）
                    prev_hits = [h for h in role_hits if _agent_seq(h["role"]) < missing_seq]
                    next_hits = [h for h in role_hits if _agent_seq(h["role"]) > missing_seq]
                    if prev_hits and next_hits:
                        prev_h = max(prev_hits, key=lambda h: _agent_seq(h["role"]))
                        next_h = min(next_hits, key=lambda h: _agent_seq(h["role"]))
                        est_y = (prev_h["y"] + next_h["y"]) / 2
                        est_x = prev_h["x"]
                        logger.debug("[active_fix] seq=%d 行在OCR中缺失，估算y=%.0f（可能是激活高亮行）",
                                     missing_seq, est_y)
                        # 记录估算坐标（用于点击），角色名用推测值（稍后由 chat_title 确认）
                        # 不加入 role_hits，只在 role_positions 里记占位
                        est_abs_x = int(win.left + est_x + 30)
                        est_abs_y = int(win.top + est_y + 8)
                        # 用序号占位符记录，供 find_keyword_position 后续搜索
                        placeholder_key = f"{missing_seq:02d}-?"
                        state.role_positions[placeholder_key] = (est_abs_x, est_abs_y)
                        logger.info("[active_fix] 已记录激活高亮行估算坐标 seq=%d → (%d,%d)",
                                    missing_seq, est_abs_x, est_abs_y)
        except Exception as _ae:
            logger.debug("[active_fix] 激活行补偿异常: %s", _ae)

    # ── 兜底：Pinned 未找到时全屏扫描 ──────────────────────
    # （仅用于 Pinned 面板未打开的情况，结果可信度较低）
    if not role_hits:
        fallback_seen: set[int] = set()
        for ln in lines:
            if not ln.words:
                continue
            role = _find_role_in_text(ln.text)
            if not role:
                continue
            seq = _agent_seq(role)
            if seq in fallback_seen:
                continue
            fallback_seen.add(seq)
            fw = ln.words[0]
            role_hits.append({
                "role": role,
                "x": fw.rect.x,
                "y": fw.rect.y,
                "text": ln.text.strip(),
            })
            if "author" in ln.text.lower() and not author_role:
                author_role = role
        role_hits.sort(key=lambda h: _agent_seq(h["role"]))

    # ── 全屏扫描补充 author_role（Author 标注只在聊天区出现）──
    if not author_role:
        for ln in lines:
            if not ln.words:
                continue
            if "author" in ln.text.lower():
                role = _find_role_in_text(ln.text)
                if role:
                    author_role = role
                    break

    # 构建 unique_roles（有序、无重复）
    unique_roles: list[str] = [h["role"] for h in role_hits]
    seen_roles: set[str] = set(unique_roles)
    state.all_roles = unique_roles

    # 填充 role_positions：Pinned 区域内精确定位的坐标（屏幕绝对值）
    for h in role_hits:
        abs_x = int(win.left + h["x"] + 30)   # 加偏移点到文字中心
        abs_y = int(win.top  + h["y"] + 8)
        role_upper = _re.sub(r'^\d+[-\s]*', '', h["role"].upper())  # "01-PUBLISHER" → "PUBLISHER"
        state.role_positions[h["role"].upper()] = (abs_x, abs_y)    # "01-PUBLISHER"
        state.role_positions[role_upper] = (abs_x, abs_y)           # "PUBLISHER"

    # 竖排布局：读取每个角色行下方的状态文字（如 "Edited ...", "Awaiting ..."）
    if len(role_hits) >= 1:
        y_vals = [h["y"] for h in role_hits]
        x_vals = [h["x"] for h in role_hits]
        y_spread = max(y_vals) - min(y_vals) if len(y_vals) > 1 else 999
        x_spread = max(x_vals) - min(x_vals) if len(x_vals) > 1 else 0
        is_vertical = y_spread > x_spread or len(role_hits) == 1

        if is_vertical:
            sorted_lines = sorted(lines, key=lambda l: l.words[0].rect.y if l.words else 9999)
            for rh in role_hits:
                if rh["role"] in state.role_states:
                    continue
                role_y = rh["y"]
                role_x = rh["x"]
                for ln in sorted_lines:
                    if not ln.words:
                        continue
                    fw = ln.words[0]
                    dy = fw.rect.y - role_y
                    dx = abs(fw.rect.x - role_x)
                    if 5 < dy < 45 and dx < 100:
                        txt = ln.text.strip()
                        if _find_role_in_text(txt):
                            continue
                        if len(txt) >= 3:
                            state.role_states[rh["role"]] = txt
                            break

    # ══════════════════════════════════════════════════════
    # Step 2: 判定当前激活角色
    #
    # 优先级：
    #   1. "Author" 行中的角色名（100% 可信，当前正在对话的）
    #   2. 兜底：列表第一个（序号最小）
    # ══════════════════════════════════════════════════════
    if unique_roles:
        state.agent_mode = True
        state.chat_panel_open = True
        state.current_mode = "agent"

    if author_role:
        state.agent_role = author_role
    elif unique_roles:
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
    # 唯一依据：侧栏角色行的前缀图标
    #   ✓ / ✔ / 📌 图钉 = 空闲，可发送
    #   其他特殊符号（转圈圈 spinner）= 忙碌，等待
    # 不扫任何文字内容，避免误判
    # ══════════════════════════════════════════════════════
    _IDLE_PREFIXES = {
        '\u2713',      # ✓ 钩子（完成/空闲）
        '\u2714',      # ✔ 粗钩
        '\u2611',      # ☑ 方框钩
        '\u25cb',      # ○ 空心圆
        '\U0001F4CC',  # 📌 图钉（当前选中）
        '\U0001F4CD',  # 📍 图钉2
        '\U0001F588',  # 🖈 图钉3
        '\u2316',      # ⌖
        '\u272F',      # ✯
        '\u2756',      # ❖
    }

    for rh in role_hits:
        raw = rh.get("text", "")
        if not raw:
            continue
        first_ch = raw[0]
        # 明确空闲标记 → 跳过
        if first_ch in _IDLE_PREFIXES:
            logger.debug("[busy] idle: role=%s ch=U+%04X", rh['role'], ord(first_ch))
            continue
        # 特殊符号（非字母、非数字）→ spinner = 忙碌
        if not first_ch.isalnum() and first_ch not in (' ', '-', '_', '.'):
            state.is_busy = True
            state.busy_hint = f"spinner:U+{ord(first_ch):04X} {rh['role']}"
            logger.debug("[busy] spinner: role=%s ch=U+%04X raw=%r",
                         rh['role'], ord(first_ch), raw[:12])
            break

    # 短行状态文案（Composer 下方「Generating…」等），避免扫长段用户正文
    if not state.is_busy:
        _busy_phrases = (
            "generating", "thinking", "planning next",
            "running terminal", "running command", "applying patch",
        )
        for ln in lines:
            if not ln.words:
                continue
            tl = ln.text.strip().lower()
            if len(tl) > 72:
                continue
            for ph in _busy_phrases:
                if ph in tl:
                    state.is_busy = True
                    state.busy_hint = f"status:{tl[:56]}"
                    logger.debug("[busy] phrase: %r", tl[:60])
                    break
            if state.is_busy:
                break

    return state


# ═══════════════════════════════════════════════════════════
#  一键扫描
# ═══════════════════════════════════════════════════════════

def scan(save_screenshot: bool = False,
         screenshot_path: str = "cursor_screenshot.png",
         sidebar_only: bool = False) -> CursorState:
    """扫描 Cursor 窗口。sidebar_only=True 时只截左侧侧栏区域，速度更快、噪音更少。"""
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

    # sidebar_only 参数保留兼容，但不再裁图——侧栏可能在左也可能在右
    # 由 find_keyword_position 负责排除面板噪音

    lines = ocr_dual(img)
    state = analyze(win, lines)
    state.screenshot = img          # 保留截图供亮度分析复用
    state.scan_ms = (time.perf_counter() - t0) * 1000
    return state


# ═══════════════════════════════════════════════════════════
#  聊天区标题识别：当前激活 Agent 是谁
# ═══════════════════════════════════════════════════════════

def get_chat_title_role(state: CursorState) -> str:
    """
    识别**当前会话**对应的 Agent 标题（Tab 正下方、聊天区顶部的 ``NN-NAME``），
    表示「正在和谁对话」——区别于消息正文里偶然出现的角色名。

    y 范围：与 get_active_tab_role 使用同一套 Tab 下沿（约 55+50 逻辑像素），
    仅取 Tab 带下方一条窄带，避免把滚动区消息里的 ``04-EDITOR`` 当成标题。
    """
    if not state or not getattr(state, "lines", None) or not state.window:
        return ""

    win = state.window
    win_w = max(1, win.right - win.left)
    win_h = max(1, win.bottom - win.top)
    img = getattr(state, "screenshot", None)
    ih = img.size[1] if img is not None else win_h
    sy = ih / win_h
    # 与 get_active_tab_role 中 TAB_MENU_SKIP / TAB_STRIP_H 一致
    tab_bottom = min(int((55 + 50) * sy), ih - 2)

    CHAT_MIN_X = 12
    CHAT_MAX_X = win_w * 0.58
    CHAT_MIN_Y = tab_bottom + 1
    CHAT_MAX_Y = min(tab_bottom + 135, int(ih * 0.24))

    candidates = []
    for ln in state.lines:
        if not ln.words:
            continue
        lx = ln.words[0].rect.x
        ly = ln.words[0].rect.y
        if ly < CHAT_MIN_Y or ly > CHAT_MAX_Y:
            continue
        if lx < CHAT_MIN_X or lx > CHAT_MAX_X:
            continue
        role = _find_role_in_text(ln.text)
        if not role:
            continue
        candidates.append((ly, lx, role, ln.text.strip()))

    logger.debug(
        "[chat_title] 带 y=%.0f~%.0f 候选: %s",
        CHAT_MIN_Y,
        CHAT_MAX_Y,
        [(r, round(y, 1), round(x, 1)) for y, x, r, _ in candidates],
    )

    if not candidates:
        return ""

    candidates.sort(key=lambda c: (c[0], c[1]))
    ly, lx, role, raw_text = candidates[0]
    logger.info("[chat_title] 当前会话标题 → %s (y=%.0f x=%.0f raw=%r)", role, ly, lx, raw_text)
    return role


def _col_brightness(gray_img, x: int, y0: int, y1: int) -> float:
    """某一列 x 在 [y0,y1] 范围内的平均亮度"""
    total, n = 0, 0
    for y in range(y0, min(y1, gray_img.height)):
        total += gray_img.getpixel((x, y))
        n += 1
    return total / n if n else 0.0


def _find_bright_peak_x(gray_img, y0: int, y1: int,
                        min_x: int = 0, max_x: int = -1) -> int:
    """在顶部 Tab 栏横向找亮度最高的 x 列（激活 Tab 中心）"""
    if max_x < 0:
        max_x = gray_img.width
    best_b, best_x = -1.0, min_x
    for x in range(min_x, max_x, 4):   # 每 4px 采样一次，够精度
        b = _col_brightness(gray_img, x, y0, y1)
        if b > best_b:
            best_b, best_x = b, x
    return best_x


def get_sidebar_active_role(state: CursorState) -> str:
    """识别右侧 Pinned 列表里**当前高亮**的那一行（背景更亮）。

    role_positions 里的坐标在侧栏竖列，与顶部 Tab 横坐标不可比；此处按**行**采样灰度，
    取最亮一行对应的 ``01-NAME``（需至少两行且亮度差足够）。
    """
    if not state or not state.window:
        return ""
    img = getattr(state, "screenshot", None)
    if img is None:
        return ""
    win = state.window
    rp = getattr(state, "role_positions", {}) or {}
    if not rp:
        return ""
    iw, ih = img.size
    rows: list[tuple[str, float]] = []
    seen: set[str] = set()
    for key, pos in rp.items():
        ks = str(key).strip().upper()
        if not _re.match(r"^\d{2}-[A-Z]", ks):
            continue
        if ks in seen:
            continue
        seen.add(ks)
        if not pos or len(pos) < 2:
            continue
        abs_x, abs_y = float(pos[0]), float(pos[1])
        rel_x = int(abs_x - win.left)
        rel_y = int(abs_y - win.top)
        if rel_y < 5 or rel_y >= ih - 10:
            continue
        # 仅处理窗口**右半**的侧栏坐标，避免聊天区误匹配
        if rel_x < iw * 0.50:
            continue
        x0 = max(0, rel_x - 60)
        x1 = min(iw, rel_x + 200)
        y0 = max(0, rel_y - 12)
        y1 = min(ih, rel_y + 28)
        crop = img.crop((x0, y0, x1, y1)).convert("L")
        pix = list(crop.getdata())
        if not pix:
            continue
        avg = sum(pix) / len(pix)
        rows.append((ks, avg))

    if len(rows) < 2:
        logger.info("[sidebar_active] 有效行不足(%d)，跳过", len(rows))
        return ""

    rows.sort(key=lambda t: -t[1])
    top_role, top_b = rows[0]
    second_b = rows[1][1]
    margin = top_b - second_b
    logger.info("[sidebar_active] 行亮度 Top4: %s",
                [(r, round(b, 1)) for r, b in rows[:4]])
    if margin < 1.0:
        logger.info("[sidebar_active] 亮度差 %.2f 过小，放弃", margin)
        return ""
    logger.info("[sidebar_active] 高亮行 → %s (Δ=%.1f)", top_role, margin)
    return top_role


def _active_tab_from_ocr_lines(
    state: CursorState,
    gray_full,  # PIL Image mode L，与 state.lines 坐标同全窗口截图
    y0: int,
    y1: int,
    iw: int,
) -> str:
    """从全屏 OCR 行中找落在 Tab 带内的 ``NN-NAME``，按行区域平均灰度取最亮（激活 Tab）。

    解决：仅用列亮度时最亮段常落在 x≈100 的左侧边饰/控件，而非多 Agent Tab 簇。
    """
    lines = getattr(state, "lines", None) or []
    if not lines:
        return ""
    cluster_x0 = max(100, int(iw * 0.052))
    cluster_x1 = min(int(iw * 0.44), iw - 1)
    per_role_best: dict[str, float] = {}
    for ln in lines:
        if not ln.words:
            continue
        fw = ln.words[0]
        ly, lx = int(fw.rect.y), int(fw.rect.x)
        if ly < y0 - 4 or ly > y1 + 14:
            continue
        if lx < cluster_x0 or lx > cluster_x1:
            continue
        role = _find_role_in_text(ln.text)
        if not role:
            continue
        x_min = min(w.rect.x for w in ln.words)
        x_max = max(w.rect.x + w.rect.w for w in ln.words)
        y_min = min(w.rect.y for w in ln.words)
        y_max = max(w.rect.y + w.rect.h for w in ln.words)
        xi0 = max(0, int(x_min) - 2)
        xi1 = min(gray_full.width, int(x_max) + 2)
        yi0 = max(0, int(y_min) - 1)
        yi1 = min(gray_full.height, int(y_max) + 2)
        if xi1 <= xi0 or yi1 <= yi0:
            continue
        pix = list(gray_full.crop((xi0, yi0, xi1, yi1)).getdata())
        if not pix:
            continue
        avg = sum(pix) / len(pix)
        prev = per_role_best.get(role, -1.0)
        if avg > prev:
            per_role_best[role] = avg
    if not per_role_best:
        return ""
    ranked = sorted(per_role_best.items(), key=lambda t: -t[1])
    top_role, top_b = ranked[0]
    second_b = ranked[1][1] if len(ranked) > 1 else -1.0
    margin = top_b - second_b
    logger.info("[active_tab] Tab带OCR行 候选=%s Top=%s Δ=%.1f",
                [(r, round(b, 1)) for r, b in ranked[:5]], top_role, margin)
    if len(ranked) > 1 and margin < 1.2:
        logger.info("[active_tab] Tab带OCR行 亮度差过小，不采信")
        return ""
    return top_role


def get_active_tab_role(state: CursorState) -> str:
    """识别当前激活的 Agent Tab（亮度法）。

    策略：
    1. 截图顶部 Tab 区域
    2. 逐列采样亮度，找最亮的连续区段（激活 Tab 背景更亮）
    3. 对该区段做 OCR，提取 Agent 名
    （侧栏距离兜底已移除：role_positions 在右侧竖列，与 Tab 横坐标不同域）

    INFO 级别日志，每次调用都可见。
    """
    if not state or not state.window:
        logger.info("[active_tab] state 或 window 为空，跳过")
        return ""

    win = state.window

    # ── 优先用 scan() 留下的全窗口截图（PrintWindow），与 OCR 同一像素网格 ──
    # 高 DPI（如 200%）下 pyautogui.screenshot(region=GetWindowRect) 常与逻辑/物理混用导致截到菜单栏或错位。
    img_full = getattr(state, "screenshot", None)
    if img_full is None:
        img_full = capture_window(win)
    if img_full is None:
        logger.info("[active_tab] 无全窗口截图且 capture_window 失败")
        return ""

    iw, ih = img_full.size
    win_w = max(1, win.right - win.left)
    win_h = max(1, win.bottom - win.top)
    # PrintWindow 位图与 GetWindowRect 在多数情况下一致；若不一致则按尺寸比例映射 Tab 带
    sx = iw / win_w
    sy = ih / win_h
    TAB_MENU_SKIP = 55   # 跳过顶部菜单栏（逻辑 px）
    TAB_STRIP_H = 50     # Agent Tab 栏高度（逻辑 px）
    y0 = min(int(TAB_MENU_SKIP * sy), max(0, ih - 2))
    y1 = min(int((TAB_MENU_SKIP + TAB_STRIP_H) * sy), ih)
    if y1 <= y0:
        y0, y1 = 0, min(50, ih)

    gray_full = img_full.convert("L")
    r_tab_line = _active_tab_from_ocr_lines(state, gray_full, y0, y1, iw)
    if r_tab_line:
        logger.info("[active_tab] Tab带OCR行优先 → %s", r_tab_line)
        return r_tab_line

    img = img_full.crop((0, y0, iw, y1))
    logger.info(
        "[active_tab] 从全窗口截图裁剪 Tab 带: win=%dx%d img=%dx%d scale=%.3fx%.3f y=%d~%d",
        win_w, win_h, iw, ih, sx, sy, y0, y1,
    )

    img_w, img_h = img.width, img.height
    gray = img.convert("L")
    dpi_scale = sy

    # 保存截图供调试（每次覆盖）— 写到项目 .codeflow\ 目录
    try:
        import os as _os
        # 优先用 exe 所在目录（项目根），开发模式退回到脚本父目录
        import sys as _sys
        if getattr(_sys, "frozen", False):
            _proj_dir = _os.path.dirname(_sys.executable)
        else:
            _proj_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        _save_dir = _os.path.join(_proj_dir, ".codeflow")
        _os.makedirs(_save_dir, exist_ok=True)
        img.save(_os.path.join(_save_dir, "tab_debug.png"))
        logger.info("[active_tab] 截图已保存: %s\\tab_debug.png", _save_dir)
    except Exception:
        pass

    # 跳过左边窗口边框；列亮度最亮段若在 x≈100 多为边饰/控件，非 Agent Tab 簇
    border_skip = max(10, abs(win.left) + 5)
    TAB_CLUSTER_X0 = max(border_skip + 90, int(img_w * 0.055))
    TAB_CLUSTER_X0 = min(TAB_CLUSTER_X0, int(img_w * 0.22))
    TAB_Y0 = 8
    TAB_Y1 = img_h
    TAB_X_START = TAB_CLUSTER_X0
    # Agent 多 Tab 只在**左侧**成簇；扫到 0.78 宽会把中部空白/分隔条误判为最亮（见日志 seg_cx≈1536）
    TAB_X_END = min(int(img_w * 0.42), 1600)
    TAB_X_END = max(TAB_X_END, TAB_X_START + 80)

    logger.info("[active_tab] Tab栏截图 %dx%d DPI=%.2f y=%d~%d x=%d~%d",
                img_w, img_h, dpi_scale,
                TAB_Y0, TAB_Y1, TAB_X_START, TAB_X_END)

    # ── 策略1：OCR × 符号（鼠标悬停时出现）────────────────
    close_chars = {'\u00D7', '\u2715', '\u2717', '\u2A09', '\u2716'}
    if getattr(state, "lines", None):
        for ln in state.lines:
            if not ln.words or ln.words[0].rect.y > 80:
                continue
            txt = ln.text.strip()
            if not any(c in txt for c in close_chars):
                continue
            cleaned = txt
            for c in close_chars:
                cleaned = cleaned.replace(c, ' ')
            role = _find_role_in_text(cleaned.strip())
            if role:
                logger.info("[active_tab] ×法命中: %r → %s", txt, role)
                return role

    # ── 策略2：逐列亮度，找最亮连续区段 ───────────────────
    xs = list(range(TAB_X_START, TAB_X_END, 3))
    bs = []
    for x in xs:
        total = sum(gray.getpixel((x, y)) for y in range(TAB_Y0, TAB_Y1, 2))
        bs.append(total / max(1, (TAB_Y1 - TAB_Y0) // 2))

    if not bs:
        logger.info("[active_tab] 亮度数据为空")
        return ""

    max_b = max(bs)
    min_b = min(bs)
    span = max(0.0, max_b - min_b)
    # 固定 max_b-4 在暗色主题/低对比下易整行超阈值；按列亮度极差自适应 margin
    margin = max(3.0, min(14.0, 4.0 + span * 0.12))
    threshold = max_b - margin
    logger.info("[active_tab] 亮度 max=%.1f min=%.1f span=%.1f margin=%.1f 阈值=%.1f",
                max_b, min_b, span, margin, threshold)

    # 找最长超阈值连续区段
    best_s, best_e = 0, 0
    cur_s = None
    for i, b in enumerate(bs):
        if b >= threshold:
            if cur_s is None:
                cur_s = i
        else:
            if cur_s is not None:
                if i - cur_s > best_e - best_s:
                    best_s, best_e = cur_s, i
                cur_s = None
    if cur_s is not None and len(bs) - cur_s > best_e - best_s:
        best_s, best_e = cur_s, len(bs)

    if best_e <= best_s:
        logger.info("[active_tab] 未找到亮区段，放弃")
        return ""

    seg_x0 = xs[best_s]
    seg_x1 = xs[min(best_e, len(xs) - 1)]
    seg_cx = (seg_x0 + seg_x1) // 2
    logger.info("[active_tab] 最亮区段 x=%d~%d cx=%d (亮度%.1f)",
                seg_x0, seg_x1, seg_cx, max_b)

    # ── 策略3：对亮区做 OCR ────────────────────────────────
    crop = img.crop((max(0, seg_x0 - 20), 0,
                     min(img_w, seg_x1 + 20), TAB_Y1 + 5))
    try:
        crop_lines = ocr_image(crop, "en")
        ocr_texts = [ln.text for ln in crop_lines]
        logger.info("[active_tab] 亮区OCR结果: %s", ocr_texts)
        for ln in crop_lines:
            role = _find_role_in_text(ln.text)
            if role:
                logger.info("[active_tab] OCR命中: %r → %s", ln.text, role)
                return role
    except Exception as e:
        logger.info("[active_tab] 亮区OCR异常: %s", e)

    logger.info("[active_tab] 所有策略失败，返回空")
    return ""


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
    """
    返回 keyword 对应 Agent 的屏幕坐标。
    优先查 analyze() 从 Pinned 区域精确定位的 role_positions，
    避免被面板（Simple Browser）里显示的角色文字误导。
    """
    if not state.found or not state.window:
        return None

    kw = keyword.strip().upper()
    # 去掉序号前缀，得到纯角色名
    kw_suf = _re.sub(r'^\d+[-\s]*', '', kw)

    # ── 优先：Pinned 区域精确坐标 ──
    for key in (kw, kw_suf):
        if key in state.role_positions:
            return state.role_positions[key]

    # ── 次优：激活高亮行占位坐标（高亮行OCR失败时的估算坐标）──
    # 格式 "NN-?" 表示该序号行因高亮未被OCR识别，但坐标已估算
    m_seq = _re.match(r'^(\d+)', kw)
    if m_seq:
        placeholder = f"{int(m_seq.group(1)):02d}-?"
        if placeholder in state.role_positions:
            logger.debug("[find_kw] 命中激活高亮占位坐标 %s → %s",
                         kw, placeholder)
            return state.role_positions[placeholder]

    # ── 兜底：全文本搜索（Pinned 未找到时）──
    win = state.window
    kw_lower = kw.lower()
    m = _re.match(r'^(\d+)[-\s]+(.+)$', kw_lower)
    kw_num = m.group(1).lstrip('0') if m else None
    kw_suf_lower = m.group(2) if m else kw_suf.lower()

    def _line_matches(ln_text: str) -> bool:
        lt = ln_text.lower()
        if kw_lower in lt:
            return True
        if kw_num and kw_suf_lower:
            extracted = _extract_agent_label(ln_text)
            if extracted and extracted.lower() == kw_lower:
                return True
            if kw_num in lt and kw_suf_lower in lt:
                return True
        return False

    min_rel_y = win.height * 0.10
    candidates = []
    for ln in state.lines:
        if not _line_matches(ln.text):
            continue
        if ln.words:
            fw = ln.words[0]
            if fw.rect.y < min_rel_y:
                continue
            abs_x = int(win.left + fw.rect.cx)
            abs_y = int(win.top + fw.rect.cy)
            dist_edge = min(fw.rect.x, win.width - fw.rect.x)
            candidates.append((dist_edge, abs_x, abs_y))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return (candidates[0][1], candidates[0][2])


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
