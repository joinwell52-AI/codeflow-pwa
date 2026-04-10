"""直接测试 WH_MOUSE_LL 全局鼠标钩子，运行后在任意地方点左键，看能否捕到坐标。"""
import ctypes, ctypes.wintypes, time

u32 = ctypes.windll.user32
captured = [False]

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt",          ctypes.wintypes.POINT),
        ("mouseData",   ctypes.wintypes.DWORD),
        ("flags",       ctypes.wintypes.DWORD),
        ("time",        ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_ulonglong, ctypes.c_ulonglong)

def _hook_cb(nCode, wParam, lParam):
    try:
        if nCode >= 0 and wParam == WM_LBUTTONDOWN:
            ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            print(f"捕获到点击: ({ms.pt.x}, {ms.pt.y})", flush=True)
            captured[0] = True
    except Exception as e:
        print(f"回调异常: {e}", flush=True)
    return u32.CallNextHookEx(None, nCode, wParam, lParam)

cb = HOOKPROC(_hook_cb)
hook = u32.SetWindowsHookExW(WH_MOUSE_LL, cb, None, 0)
if not hook:
    print(f"钩子安装失败，错误码: {ctypes.get_last_error()}")
else:
    print("钩子已安装，请在 10 秒内点击鼠标左键…")

# WH_MOUSE_LL 需要消息泵才能触发回调
msg = ctypes.wintypes.MSG()
deadline = time.time() + 10.0
while time.time() < deadline and not captured[0]:
    r = u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
    if r > 0:
        u32.TranslateMessage(ctypes.byref(msg))
        u32.DispatchMessageW(ctypes.byref(msg))
    else:
        time.sleep(0.005)

if hook:
    u32.UnhookWindowsHookEx(hook)

if captured[0]:
    print("测试通过！钩子正常工作。")
else:
    print("超时，未捕获到点击。")
