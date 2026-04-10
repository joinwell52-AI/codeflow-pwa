"""
调试 Tab 激活识别——在 Cursor 有多个 Agent Tab 时运行此脚本。
py -3.12 _debug_tab.py
"""
import sys, time
sys.path.insert(0, r'd:\BridgeFlow\codeflow-desktop')

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s %(message)s')

import cursor_vision as cv

print("=== 找 Cursor 窗口 ===")
win = cv.find_main_cursor_window()
if not win:
    print("未找到 Cursor 窗口！")
    sys.exit(1)
print(f"窗口: {win.title[:60]}")
print(f"rect: left={win.left} top={win.top} w={win.width} h={win.height}")

print("\n=== 截图 ===")
img = cv.capture_window(win)
if img is None:
    print("截图失败！")
    sys.exit(1)
print(f"截图尺寸: {img.width}x{img.height}")

# 保存顶部 60px 供肉眼确认
top = img.crop((0, 0, img.width, 60))
top.save(r'd:\BridgeFlow\_tab_top60.png')
print("已保存顶部60px → d:\\BridgeFlow\\_tab_top60.png")

# 横向亮度扫描
gray = img.convert("L")
print("\n=== Tab栏亮度(y=5~50，每列) ===")
TAB_Y0, TAB_Y1 = 5, 50
brightness = []
for x in range(50, img.width - 50, 10):
    b = sum(gray.getpixel((x, y)) for y in range(TAB_Y0, TAB_Y1)) / (TAB_Y1 - TAB_Y0)
    brightness.append((x, b))

# 找峰值
peak = max(brightness, key=lambda t: t[1])
print(f"亮度峰值: x={peak[0]} brightness={peak[1]:.1f}")

# 打印亮度分布（每50px）
print("\n每50px亮度:")
for x, b in brightness[::5]:
    bar = '#' * int(b / 3)
    print(f"  x={x:5d}  {b:5.1f}  {bar}")

print("\n=== OCR 全扫 ===")
state = cv.scan()
print(f"found={state.found} roles={state.all_roles}")
print(f"所有OCR行(y<100):")
for ln in state.lines:
    if ln.words and ln.words[0].rect.y <= 100:
        print(f"  y={ln.words[0].rect.y:5.1f} x={ln.words[0].rect.x:5.1f}  {ln.text!r}")

print(f"\nall_roles: {state.all_roles}")
print(f"role_positions keys: {list(state.role_positions.keys())}")

# 打印 Tab 栏区域亮度分布（x=0~70%宽，y=8~50）
img_w = img.width
TAB_X_START, TAB_X_END = 0, int(img_w * 0.70)
TAB_Y0, TAB_Y1 = 8, 50
step = max(10, (TAB_X_END - TAB_X_START) // 40)
print(f"\nTab栏亮度分布 x={TAB_X_START}~{TAB_X_END} y={TAB_Y0}~{TAB_Y1} (每{step}px):")
for x in range(TAB_X_START, TAB_X_END, step):
    b = sum(gray.getpixel((x, y)) for y in range(TAB_Y0, TAB_Y1)) / (TAB_Y1 - TAB_Y0)
    bar = '#' * int(b / 2)
    print(f"  x={x:5d}  {b:5.1f}  {bar}")

print("\n=== get_active_tab_role ===")
result = cv.get_active_tab_role(state)
print(f"结果: {result!r}")

print("\n=== get_chat_title_role ===")
result2 = cv.get_chat_title_role(state)
print(f"结果: {result2!r}")
