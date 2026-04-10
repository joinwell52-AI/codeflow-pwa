# -*- coding: utf-8 -*-
import os

BASE = r"D:\BridgeFlow\codeflow-desktop"

html = os.path.join(BASE, "panel", "index.html")
print(f"index.html size: {os.path.getsize(html)}")

exe = os.path.join(BASE, "dist", "CodeFlow-Desktop.exe")
data = open(exe, "rb").read()
print(f"EXE size: {len(data)}")

for kw in [b"index.html", b"switchTestBody", b"2.7.8", b"steps"]:
    print(f"  {kw}: {'FOUND' if kw in data else 'NOT FOUND'}")

# 看 build log 里 index.html 有没有被收集
build_warn = os.path.join(BASE, "build", "build", "warn-CodeFlow-Desktop.txt")
if os.path.isfile(build_warn):
    txt = open(build_warn).read()
    if "index.html" in txt:
        print("WARNING: index.html 在 build 警告里")
    else:
        print("build 警告里没有 index.html 相关")
