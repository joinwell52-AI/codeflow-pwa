# -*- mode: python ; coding: utf-8 -*-
# PyInstaller — 单文件 EXE：码流（CodeFlow）Desktop
# 用法：在 codeflow-desktop 目录下执行  pyinstaller build.spec --noconfirm
# 产物：dist/CodeFlow-Desktop.exe

import os, subprocess, sys

try:
    BASE = os.path.abspath(SPECPATH)
except NameError:
    BASE = os.path.dirname(os.path.abspath(__file__))


# 图标：用绝对路径，避免相对路径在个别环境下解析异常
_APP_ICO_ABS = os.path.normpath(os.path.join(BASE, "panel", "app.ico"))
if not os.path.isfile(_APP_ICO_ABS):
    raise SystemExit(
        "打包失败：缺少 %s ，请放入码流（CodeFlow）应用图标后再打包。" % (_APP_ICO_ABS,)
    )


# ── 先把 snap_click.py 打成独立单文件 EXE ──────────────────────────────────
snap_src = os.path.join(BASE, "snap_click.py")
snap_exe = os.path.join(BASE, "dist_snap", "snap_click.exe")

if os.path.isfile(snap_src):
    print("[build.spec] 正在打包 snap_click.exe …")
    r = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--noconsole", "--noconfirm",
            "--distpath", os.path.join(BASE, "dist_snap"),
            "--workpath", os.path.join(BASE, "build_snap"),
            "--specpath", os.path.join(BASE, "build_snap"),
            snap_src,
        ],
        cwd=BASE,
    )
    if r.returncode != 0 or not os.path.isfile(snap_exe):
        print("[build.spec] WARNING: snap_click.exe 打包失败，坐标定位将降级到内置轮询")
        snap_exe = None
    else:
        print(f"[build.spec] snap_click.exe 已生成: {snap_exe}")
else:
    print(f"[build.spec] WARNING: 找不到 {snap_src}")
    snap_exe = None


def _collect_datas():
    """只打包存在的文件，避免缺 logo/ico 时构建失败。"""
    out = []
    panel_dir = os.path.join(BASE, "panel")
    if os.path.isdir(panel_dir):
        for name in (
            "index.html",
            "qrcode.min.js",
            "logo-sm.png",
            "logo.png",
            "app.ico",
            "product.png",
        ):
            p = os.path.join(panel_dir, name)
            if os.path.isfile(p):
                out.append((p, "panel"))
    tpl = os.path.join(BASE, "templates")
    if os.path.isdir(tpl):
        out.append((tpl, "templates"))
    # snap_click.exe — 独立坐标捕获进程，放到 _MEIPASS 根目录
    if snap_exe and os.path.isfile(snap_exe):
        out.append((snap_exe, "."))
    return out


block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[BASE],
    binaries=[],
    datas=_collect_datas(),
    hiddenimports=[
        "pyautogui",
        "pyperclip",
        "win32gui",
        "win32con",
        "win32api",
        "win32ui",
        "win32process",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.client",
        "winocr",
        "PIL",
        "PIL.Image",
        "PIL.ImageGrab",
        "PIL.ImageTk",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "cursor_vision",
        "nudger",
        "config",
        "web_panel",
        "win_snap",
        "cursor_acp",
        "cursor_embed",
        "watchdog",
        "watchdog.observers",
        "watchdog.events",
        "watchdog.utils",
        "psutil",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas",
        "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
        "PyQt5.QtNetwork", "PyQt5.QtSvg", "PyQt5.QtXml",
        "PyQt5.Qt5", "PyQt5_Qt5", "PyQt5_sip",
        "cv2", "scipy", "torch", "tensorflow",
        "fastapi", "uvicorn", "starlette",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CodeFlow-Desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_APP_ICO_ABS,
)
