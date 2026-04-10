"""
OCR 定位诊断脚本 - 直接运行看结果
用法: py -3.10 diagnose_ocr.py
"""
import sys, time, os

# 加入当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("CodeFlow OCR 定位诊断")
print("=" * 60)

# 1. 测试 winocr 是否可用
print("\n[1] 检测 winocr...")
try:
    import winocr
    langs = winocr.get_available_recognizer_languages()
    print(f"    可用语言包: {[str(l) for l in langs]}")
    has_en = any("en" in str(l).lower() for l in langs)
    has_zh = any("zh" in str(l).lower() for l in langs)
    print(f"    英文(en): {'✓' if has_en else '✗ 缺失!'}")
    print(f"    中文(zh): {'✓' if has_zh else '✗ 缺失!'}")
    if not has_en:
        print("    >>> 缺少英文语言包，OCR 识别 Agent 名称会失败！")
        print("    >>> 安装命令（管理员 PowerShell）：")
        print("    >>> Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'")
except Exception as e:
    print(f"    ✗ winocr 不可用: {e}")
    sys.exit(1)

# 2. 测试截图 Cursor 窗口
print("\n[2] 查找 Cursor 窗口...")
try:
    from cursor_vision import find_main_cursor_window, capture_window
    win = find_main_cursor_window()
    if not win:
        print("    ✗ 未找到 Cursor 窗口，请确认 Cursor 已打开")
        sys.exit(1)
    print(f"    ✓ 找到 Cursor 窗口: left={win.left}, top={win.top}, {win.width}x{win.height}")
    img = capture_window(win)
    if img:
        img.save("_diagnose_screenshot.png")
        print(f"    ✓ 截图成功，已保存为 _diagnose_screenshot.png")
    else:
        print("    ✗ 截图失败")
        sys.exit(1)
except Exception as e:
    print(f"    ✗ 出错: {e}")
    sys.exit(1)

# 3. OCR 扫描
print("\n[3] OCR 扫描...")
try:
    from cursor_vision import ocr_dual
    lines = ocr_dual(img)
    print(f"    识别到 {len(lines)} 行文字")
    print("    前20行内容:")
    for i, ln in enumerate(lines[:20]):
        print(f"      [{i:2d}] {ln.text!r}")
except Exception as e:
    print(f"    ✗ OCR 失败: {e}")
    sys.exit(1)

# 4. 分析 Agent 角色
print("\n[4] 分析 Agent 角色...")
try:
    from cursor_vision import analyze, find_keyword_position
    state = analyze(win, lines)
    print(f"    agent_role: {state.agent_role!r}")
    print(f"    all_roles:  {state.all_roles}")
    if not state.all_roles:
        print("    >>> 没有识别到任何 Agent，可能原因:")
        print("    >>> 1. Agent 名称不是 01-XXX 格式")
        print("    >>> 2. Cursor 侧栏没有打开 Agents 列表")
        print("    >>> 3. OCR 语言包缺失")
except Exception as e:
    print(f"    ✗ 分析失败: {e}")

# 5. 搜索特定标签
print("\n[5] 搜索 Agent 标签位置...")
test_labels = ["01-PUBLISHER", "02-COLLECTOR", "03-WRITER", "04-EDITOR",
               "01-PM", "02-DEV", "03-QA", "04-OPS"]
found_any = False
for label in test_labels:
    try:
        from cursor_vision import scan
        # 直接在已有的 lines 里搜索
        import re
        for ln in lines:
            if label.lower() in ln.text.lower():
                if ln.words:
                    fw = ln.words[0]
                    abs_x = int(win.left + fw.rect.cx)
                    abs_y = int(win.top + fw.rect.cy)
                    print(f"    ✓ 找到 {label!r} → 坐标 ({abs_x}, {abs_y})")
                    found_any = True
                    break
    except Exception:
        pass

if not found_any:
    print("    没有找到任何已知标签")
    print("    OCR 识别到的所有行（包含数字的）:")
    for ln in lines:
        if any(c.isdigit() for c in ln.text):
            print(f"      {ln.text!r}")

print("\n" + "=" * 60)
print("诊断完成，请把以上输出发给开发者")
print("=" * 60)
input("\n按回车退出...")
