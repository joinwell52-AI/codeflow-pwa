"""
测试 UIAutomation vtable 索引 — 仅用于开发调试，不会打包进 exe
"""
import ctypes, ctypes.wintypes, uuid, sys, io, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import win32gui

# ── 找 Cursor hwnd ──────────────────────────────────────────────────
wins = []
def _e(hwnd, _):
    if not win32gui.IsWindowVisible(hwnd): return
    pid = ctypes.wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
    if not h: return
    buf = (ctypes.c_wchar * 520)()
    sz = ctypes.wintypes.DWORD(520)
    ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
    ctypes.windll.kernel32.CloseHandle(h)
    if 'cursor.exe' in buf.value.lower():
        l,t,r,b = win32gui.GetWindowRect(hwnd)
        wins.append((hwnd, win32gui.GetWindowText(hwnd), r-l, b-t))
win32gui.EnumWindows(_e, None)
if not wins: sys.exit('未找到 Cursor')
wins.sort(key=lambda x:x[2]*x[3], reverse=True)
hwnd, title, W, H = wins[0]
print(f'Cursor hwnd={hwnd}  {title}  {W}x{H}')


# ── GUID 工具 ─────────────────────────────────────────────────────────
class GUID(ctypes.Structure):
    _fields_=[('D1',ctypes.c_ulong),('D2',ctypes.c_ushort),('D3',ctypes.c_ushort),('D4',ctypes.c_ubyte*8)]

def mguid(s):
    u=uuid.UUID(s);b=u.bytes_le;g=GUID()
    g.D1=int.from_bytes(b[0:4],'little')
    g.D2=int.from_bytes(b[4:6],'little')
    g.D3=int.from_bytes(b[6:8],'little')
    for i in range(8): g.D4[i]=b[8+i]
    return g


# ── 初始化 IUIAutomation ──────────────────────────────────────────────
CLSID = mguid('FF48DBA4-60EF-4201-AA87-54103EEF594E')
IID   = mguid('30CBE57D-D9D0-452A-AB13-7AC5AC4825EE')
ole32   = ctypes.windll.ole32
oleaut  = ctypes.windll.oleaut32
ole32.CoInitializeEx(None, 0)

uia_p = ctypes.c_void_p()
hr = ole32.CoCreateInstance(ctypes.byref(CLSID), None, 1, ctypes.byref(IID), ctypes.byref(uia_p))
if hr != 0 or not uia_p.value:
    sys.exit(f'CoCreateInstance hr=0x{hr&0xFFFFFFFF:08x}')
print(f'IUIAutomation: 0x{uia_p.value:x}')

uia_vt = ctypes.cast(uia_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]

# IUIAutomation vtable（来自 UIAutomation.h SDK）：
# 0  QueryInterface
# 1  AddRef
# 2  Release
# 3  CompareElements
# 4  CompareRuntimeIds
# 5  GetRootElement
# 6  ElementFromHandle
# 7  ElementFromPoint
# 8  GetFocusedElement
# 9  GetRootElementBuildCache
# 10 ElementFromHandleBuildCache
# 11 ElementFromPointBuildCache
# 12 GetFocusedElementBuildCache
# 13 CreateTreeWalker
# 14 get_ControlViewWalker
# 15 get_ContentViewWalker
# 16 get_RawViewWalker
# 17 get_RawViewCondition
# 18 get_ControlViewCondition
# 19 get_ContentViewCondition
# 20 CreateCacheRequest
# 21 CreateTrueCondition       ← index 21
# 22 CreateFalseCondition
# 23 CreatePropertyCondition
# 24 CreatePropertyConditionEx
# 25 CreateAndCondition
# 26 CreateAndConditionFromArray
# 27 CreateAndConditionFromNativeArray
# 28 CreateOrCondition
# ...

# ElementFromHandle
EFH = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.wintypes.HWND, ctypes.POINTER(ctypes.c_void_p))
el_p = ctypes.c_void_p()
hr2 = EFH(uia_vt[6])(uia_p, hwnd, ctypes.byref(el_p))
print(f'ElementFromHandle hr=0x{hr2&0xFFFFFFFF:08x} el=0x{el_p.value or 0:x}')
if not el_p.value:
    sys.exit('ElementFromHandle 失败')

# CreateTrueCondition (index 21)
CTC = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
cond_p = ctypes.c_void_p()
hr3 = CTC(uia_vt[21])(uia_p, ctypes.byref(cond_p))
print(f'TrueCondition hr=0x{hr3&0xFFFFFFFF:08x} cond=0x{cond_p.value or 0:x}')
if not cond_p.value:
    sys.exit('CreateTrueCondition 失败')

# IUIAutomationElement vtable：
# 0  QI  1 AddRef  2 Release
# 3  SetFocus  4 GetRuntimeId  5 FindFirst  6 FindAll  7 FindFirstBuildCache ...
# get_CurrentName は index 19

el_vt = ctypes.cast(el_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]

# FindAll(scope=7=Subtree, condition, **array)  → index 6
FA = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
arr_p = ctypes.c_void_p()
t0 = time.perf_counter()
hr4 = FA(el_vt[6])(el_p, 7, cond_p, ctypes.byref(arr_p))
ms = (time.perf_counter()-t0)*1000
print(f'FindAll hr=0x{hr4&0xFFFFFFFF:08x} arr=0x{arr_p.value or 0:x}  ({ms:.0f}ms)')
if not arr_p.value:
    sys.exit('FindAll 失败')

# IUIAutomationElementArray: vtable 3=get_Length, 4=GetElement
arr_vt = ctypes.cast(arr_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
GL = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
length = ctypes.c_int(0)
GL(arr_vt[3])(arr_p, ctypes.byref(length))
print(f'元素总数: {length.value}')

GE = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
GN = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))

ROLES = {'PM','DEV','QA','OPS','PUBLISHER','COLLECTOR','WRITER','EDITOR'}
RE_AGENT = re.compile(
    r'(?:(?P<idx>\d{1,2})\s*[-\.\s]\s*)?(?P<role>' + '|'.join(ROLES) + r')\b',
    re.IGNORECASE
)

found: list[str] = []
seen: set[str] = set()

for i in range(min(length.value, 8000)):
    item_p = ctypes.c_void_p()
    hr_ge = GE(arr_vt[4])(arr_p, i, ctypes.byref(item_p))
    if hr_ge != 0 or not item_p.value:
        continue
    item_vt = ctypes.cast(item_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    bstr = ctypes.c_void_p()
    GN(item_vt[19])(item_p, ctypes.byref(bstr))
    if bstr.value:
        try:
            name = ctypes.wstring_at(bstr)
        except Exception:
            name = ''
        oleaut.SysFreeString(bstr)
        if name.strip():
            m = RE_AGENT.search(name)
            if m:
                role = m.group('role').upper()
                idx_s = m.group('idx')
                label = f"{int(idx_s):02d}-{role}" if idx_s else role
                if label not in seen:
                    seen.add(label)
                    found.append(label)
                    print(f'  [{i}] {name!r} → {label}')
    # Release
    item_rel = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(item_vt[2])
    item_rel(item_p)

print('\n最终 Agents:', found)
