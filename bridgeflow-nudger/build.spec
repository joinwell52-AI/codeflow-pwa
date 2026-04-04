# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for BridgeFlow Desktop

import os

block_cipher = None
base_dir = os.path.dirname(os.path.abspath(SPECPATH if 'SPECPATH' in dir() else __file__))

a = Analysis(
    ['main.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[
        ('panel/index.html', 'panel'),
        ('panel/qrcode.min.js', 'panel'),
        ('panel/logo-sm.png', 'panel'),
        ('panel/logo.png', 'panel'),
        ('panel/app.ico', 'panel'),
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'pyautogui',
        'pyperclip',
        'win32gui',
        'win32con',
        'win32api',
        'win32ui',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.client',
        'winocr',
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'cursor_vision',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'tkinter.test'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BridgeFlow-Desktop',
    icon='panel/app.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
