"""
切换测试：直接按 Ctrl+Alt+2 切到第2个 Agent，然后 OCR 验证结果
"""
import sys, io, time, logging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s %(message)s')

import pyautogui
from cursor_vision import scan, find_main_cursor_window

win = find_main_cursor_window()
if not win:
    print("未找到 Cursor 窗口")
    sys.exit(1)
print(f"窗口: {win.title}  {win.width}x{win.height}")

# 先扫一次，看当前状态
st = scan()
print(f"\n当前 agent_role={st.agent_role!r}  all_roles={st.all_roles}")

# 按 Ctrl+Alt+2
print("\n按 Ctrl+Alt+2 ...")
import win32gui, win32con
win32gui.SetForegroundWindow(win.hwnd)
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'alt', '2')
time.sleep(1.5)

# 再扫
st2 = scan()
print(f"切换后 agent_role={st2.agent_role!r}  all_roles={st2.all_roles}")

# 再按 Ctrl+Alt+3
print("\n按 Ctrl+Alt+3 ...")
pyautogui.hotkey('ctrl', 'alt', '3')
time.sleep(1.5)
st3 = scan()
print(f"切换后 agent_role={st3.agent_role!r}  all_roles={st3.all_roles}")

# 再按 Ctrl+Alt+4
print("\n按 Ctrl+Alt+4 ...")
pyautogui.hotkey('ctrl', 'alt', '4')
time.sleep(1.5)
st4 = scan()
print(f"切换后 agent_role={st4.agent_role!r}  all_roles={st4.all_roles}")
