"""
cursor_agents_uia.py — 通过 Windows UIAutomationCore.dll (纯 ctypes) 读取
Cursor 侧栏 Pinned Agents 列表，不依赖任何第三方包。

返回 list[str]，如 ["01-PUBLISHER", "02-COLLECTOR", "03-WRITER", "04-EDITOR"]
返回空列表时调用方回退到截图 OCR。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import re
import uuid

logger = logging.getLogger("codeflow.agents_uia")

# ─── 角色匹配 ─────────────────────────────────────────────────────────
_ROLE_SUFFIXES = {
    "PM", "DEV", "QA", "OPS",
    "PUBLISHER", "COLLECTOR", "WRITER", "EDITOR",
}
_RE_AGENT = re.compile(
    r"(?:(?P<idx>\d{1,2})\s*[-\.\s]\s*)?"
    r"(?P<role>" + "|".join(_ROLE_SUFFIXES) + r")\b",
    re.IGNORECASE,
)


def _normalize(raw: str) -> str:
    m = _RE_AGENT.search(raw.strip())
    if not m:
        return ""
    role = m.group("role").upper()
    idx_s = m.group("idx")
    if idx_s:
        return f"{int(idx_s):02d}-{role}"
    return role


# ─── GUID 工具 ────────────────────────────────────────────────────────
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _make_guid(s: str) -> _GUID:
    u = uuid.UUID(s)
    b = u.bytes_le
    g = _GUID()
    g.Data1 = int.from_bytes(b[0:4], "little")
    g.Data2 = int.from_bytes(b[4:6], "little")
    g.Data3 = int.from_bytes(b[6:8], "little")
    for i in range(8):
        g.Data4[i] = b[8 + i]
    return g


# ─── UIAutomationCore COM 接口（纯 ctypes vtable 调用）──────────────
# 只需要最少的方法：
#   IUIAutomation::ElementFromHandle → IUIAutomationElement
#   IUIAutomationElement::FindAll(scope, cond) → IUIAutomationElementArray
#   IUIAutomationElement::get_CurrentName → BSTR
#   IUIAutomationElementArray::get_Length / GetElement

_CLSID_CUIAutomation = _make_guid("FF48DBA4-60EF-4201-AA87-54103EEF594E")
_IID_IUIAutomation   = _make_guid("30CBE57D-D9D0-452A-AB13-7AC5AC4825EE")

_ole32   = ctypes.windll.ole32
_oleaut  = ctypes.windll.oleaut32

CLSCTX_INPROC_SERVER = 1
TreeScope_Subtree    = 7   # self + descendants
VARIANT_FALSE = 0
VARIANT_TRUE  = -1


def _co_init():
    try:
        _ole32.CoInitializeEx(None, 0)
    except Exception:
        pass


def _bstr_to_str(bstr: ctypes.c_void_p) -> str:
    if not bstr:
        return ""
    try:
        s = ctypes.wstring_at(bstr)
        _oleaut.SysFreeString(bstr)
        return s
    except Exception:
        return ""


class _IUnknown(ctypes.Structure):
    """最小 IUnknown vtable — QueryInterface / AddRef / Release"""
    pass


def _vtbl_call(obj: ctypes.c_void_p, idx: int, *args):
    """通过 vtable 调用 COM 方法。obj 是接口指针（c_void_p 值）。"""
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))
    fn_ptr = vtable[idx]
    fn = ctypes.cast(fn_ptr, ctypes.c_void_p)
    return fn, vtable


# 因为 Electron/Chromium 渲染的 UI 树节点极多，纯 vtable 遍历很脆，
# 改用更稳健的方案：IUIAutomation::GetRootElement + FindAll + get_CurrentName
# 用 ctypes.WINFUNCTYPE 包装每个方法调用

def _read_all_names_uia(hwnd: int) -> list[str]:
    """
    通过 UIAutomationCore.dll CoCreateInstance + vtable，
    枚举 hwnd 下所有 UI 元素的 CurrentName，返回原始字符串列表。
    """
    _co_init()
    pUIA = ctypes.c_void_p()
    hr = _ole32.CoCreateInstance(
        ctypes.byref(_CLSID_CUIAutomation),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(_IID_IUIAutomation),
        ctypes.byref(pUIA),
    )
    if hr != 0 or not pUIA.value:
        logger.debug("CoCreateInstance IUIAutomation hr=0x%08x", hr & 0xFFFFFFFF)
        return []

    # ── 调用 ElementFromHandle(hwnd) → pElement
    # IUIAutomation vtable 方法顺序（从 UIAutomation.h 数）：
    #   0 QueryInterface  1 AddRef  2 Release
    #   3 CompareElements  4 CompareRuntimeIds  5 GetRootElement
    #   6 ElementFromHandle  7 ElementFromPoint  8 GetFocusedElement
    # ElementFromHandle 在 vtable index 6

    vtable = ctypes.cast(pUIA, ctypes.POINTER(ctypes.c_void_p))
    ElementFromHandle_fn = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        ctypes.c_void_p,   # this
        ctypes.wintypes.HWND,   # hwnd
        ctypes.POINTER(ctypes.c_void_p),  # *ppElement
    )(vtable[0][6])  # vtable[0] → vtable ptr array; [6] = 7th method

    pElement = ctypes.c_void_p()
    hr2 = ElementFromHandle_fn(pUIA, hwnd, ctypes.byref(pElement))
    if hr2 != 0 or not pElement.value:
        logger.debug("ElementFromHandle hr=0x%08x", hr2 & 0xFFFFFFFF)
        # Release IUIAutomation
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[0][2])
        release(pUIA)
        return []

    # ── 创建 TrueCondition：CreateTrueCondition 在 IUIAutomation vtable index 24
    # IUIAutomation 有很多方法，CreateTrueCondition 比较靠后，用更简单的方案：
    # 直接用 FindAll with scope=Subtree, condition=TrueCondition
    # 但构造 TrueCondition 需要 vtable...
    #
    # 更简单：用 get_CurrentName 直接从根元素递归 FirstChild/NextSibling 遍历
    # IUIAutomationElement vtable：
    #   0 QI  1 AddRef  2 Release
    #   3..N: FindFirst, FindAll, ...
    #   get_CurrentName 在 index 19（IUIAutomationElement 接口定义顺序）
    #
    # 用 GetFirstChildElement / GetNextSiblingElement via TreeWalker 更安全
    # CreateTreeWalker(TrueCondition) → TreeWalker，但仍需 TrueCondition...
    #
    # 最可靠方案：用 IUIAutomation::ElementFromHandle + FindAll + PropertyCondition
    # 但方法太多，改为直接枚举 get_CurrentName via AccessibleObjectFromWindow

    # 释放资源
    el_vtable = ctypes.cast(pElement, ctypes.POINTER(ctypes.c_void_p))
    el_release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(el_vtable[0][2])
    el_release(pElement)

    release_uia = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[0][2])
    release_uia(pUIA)

    return []  # vtable 路径太脆，回退到 oleacc


def _read_all_names_oleacc(hwnd: int) -> list[str]:
    """
    用 oleacc.dll AccessibleObjectFromWindow + IAccessible（win32api 不需要）
    递归收集所有 accName。
    完全纯 ctypes + win32gui（pywin32 已在依赖中）。
    """
    try:
        import win32com.client as _wcc
        import pythoncom as _pycom
    except ImportError:
        logger.debug("win32com 不可用")
        return []

    try:
        _pycom.CoInitialize()
    except Exception:
        pass

    oleacc = ctypes.windll.oleacc
    OBJID_CLIENT = -4

    IID_IAccessible_str = "618736E0-3C3D-11CF-810C-00AA00389B71"
    iid = _make_guid(IID_IAccessible_str)
    ppv = ctypes.c_void_p()

    try:
        hr = oleacc.AccessibleObjectFromWindow(
            hwnd,
            ctypes.c_long(OBJID_CLIENT),
            ctypes.byref(iid),
            ctypes.byref(ppv),
        )
    except Exception as e:
        logger.debug("AccessibleObjectFromWindow 异常: %s", e)
        return []

    if hr != 0 or not ppv.value:
        logger.debug("AccessibleObjectFromWindow hr=0x%08x", hr & 0xFFFFFFFF)
        return []

    # 用 pythoncom 把指针包装成 IDispatch
    try:
        acc = _pycom.ObjectFromAddress(ppv.value, _pycom.IID_IDispatch)
    except Exception as e:
        logger.debug("ObjectFromAddress 失败: %s", e)
        return []

    names: list[str] = []
    _MAX = 2000  # 防止 Electron UI 树过深

    def _walk(a, depth: int = 0):
        if depth > 20 or len(names) > _MAX:
            return
        try:
            n = a.accName(0)
            if n and n.strip():
                names.append(n.strip())
        except Exception:
            pass
        try:
            cnt = a.accChildCount
        except Exception:
            cnt = 0
        for i in range(1, min(cnt + 1, 200)):
            try:
                child = a.accChild(i)
                if child:
                    _walk(child, depth + 1)
            except Exception:
                pass

    try:
        _walk(acc)
    except Exception as e:
        logger.debug("IAccessible walk 异常: %s", e)

    logger.debug("oleacc 总节点名 %d 个", len(names))
    return names


# ─── 公共接口 ─────────────────────────────────────────────────────────

def read_pinned_agents(hwnd: int) -> list[str]:
    """
    读取 Cursor 侧栏 Pinned Agents 名称列表（规范化格式）。
    空列表 → 调用方回退到截图 OCR。
    """
    all_names = _read_all_names_oleacc(hwnd)

    results: list[str] = []
    seen: set[str] = set()
    for n in all_names:
        label = _normalize(n)
        if label and label not in seen:
            seen.add(label)
            results.append(label)

    if results:
        logger.info("UIA(oleacc) Agents: %s", results)
    else:
        logger.debug("UIA 无 Agent 命中，回退 OCR")
    return results


# ─── 独立测试 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    import win32gui
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")

    def _find_cursor(hwnd, out):
        if not win32gui.IsWindowVisible(hwnd):
            return
        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return
        buf = (ctypes.c_wchar * 520)()
        sz = ctypes.wintypes.DWORD(520)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
        ctypes.windll.kernel32.CloseHandle(h)
        if "cursor.exe" in buf.value.lower():
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            out.append((hwnd, win32gui.GetWindowText(hwnd), r - l, b - t))

    wins = []
    win32gui.EnumWindows(_find_cursor, wins)
    if not wins:
        print("未找到 Cursor 窗口")
        sys.exit(1)
    wins.sort(key=lambda x: x[2] * x[3], reverse=True)
    hwnd, title, w, h = wins[0]
    print(f"Cursor hwnd={hwnd}  {title}  {w}x{h}\n")

    agents = read_pinned_agents(hwnd)
    print("\n最终识别 Agents:", agents if agents else "(空 → 回退 OCR)")
