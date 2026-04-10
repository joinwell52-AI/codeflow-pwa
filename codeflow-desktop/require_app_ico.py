"""无 panel/app.ico 或非法 ICO 时退出非零，供 pack.cmd 在打包前调用。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ICO = _ROOT / "panel" / "app.ico"


def main() -> int:
    if not _ICO.is_file():
        print(f"ERROR: 缺少图标文件，禁止打包: {_ICO}", file=sys.stderr)
        return 1
    head = _ICO.read_bytes()[:8]
    if len(head) < 4 or head[:4] != b"\x00\x00\x01\x00":
        print(f"ERROR: 不是合法 .ico（文件头应为 00 00 01 00）: {_ICO}", file=sys.stderr)
        return 1
    if _ICO.stat().st_size < 64:
        print(f"ERROR: app.ico 过小，可能损坏: {_ICO}", file=sys.stderr)
        return 1
    print("OK icon:", _ICO)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
