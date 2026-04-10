import ctypes, ctypes.wintypes, time
u32 = ctypes.windll.user32
VK_LBUTTON = 0x01
print('请在10秒内点击任意位置...', flush=True)
deadline = time.time() + 10
prev = False
while time.time() < deadline:
    pressed = bool(u32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    if pressed and not prev:
        pt = ctypes.wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        print(f'坐标: ({pt.x}, {pt.y})', flush=True)
        with open('C:/tmp_coord.txt','w') as f:
            f.write(f'{pt.x},{pt.y}')
        break
    prev = pressed
    time.sleep(0.01)
print('结束')
