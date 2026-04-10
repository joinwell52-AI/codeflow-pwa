"""
独立子进程：监听左键点击，把坐标写到 stdout，然后退出。
由 web_panel.py 的定位功能启动，完全独立于 Electron 进程。
用法: py -3.10 snap_click.py <timeout_seconds>
"""
import sys, time, ctypes, ctypes.wintypes, os

timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
u32 = ctypes.windll.user32
VK_LBUTTON = 0x01

# 等 1.5s 让调用方的按钮点击释放
time.sleep(1.5)
while u32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
    time.sleep(0.02)

deadline = time.time() + timeout
prev = False

while time.time() < deadline:
    pressed = bool(u32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    if pressed and not prev:
        pt = ctypes.wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        # 输出坐标到 stdout，调用方读取
        print(f"{pt.x},{pt.y}", flush=True)
        sys.exit(0)
    prev = pressed
    time.sleep(0.01)

# 超时
print("timeout", flush=True)
sys.exit(1)
