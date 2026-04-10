import sys
exe = r"D:\BridgeFlow\codeflow-desktop\dist\CodeFlow-Desktop.exe"
data = open(exe, "rb").read()
checks = [b"v2.6.3", b"PC v2.6.3", b"snap_click", b"calibrate_cd", b"20</span>", b"60</span>"]
for c in checks:
    idx = data.find(c)
    print(f"{c!r}: {'found' if idx>=0 else 'NOT FOUND'} pos={idx}")
