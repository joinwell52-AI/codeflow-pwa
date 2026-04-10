"""
版本号同步工具
用法：py _bump_version.py 2.8.17
会同步更新：
  - web_panel.py   _VERSION = "x.x.x"
  - main.py        VERSION  = "x.x.x"
  - panel/index.html  PC vx.x.x
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()

def bump(new_ver: str):
    files = {
        HERE / "web_panel.py":        (r'_VERSION\s*=\s*"[\d.]+"',   f'_VERSION = "{new_ver}"'),
        HERE / "main.py":             (r'VERSION\s*=\s*"[\d.]+"',    f'VERSION = "{new_ver}"'),
        HERE / "panel" / "index.html":(r'PC v[\d.]+',                f'PC v{new_ver}'),
    }
    for path, (pattern, replacement) in files.items():
        text = path.read_text(encoding="utf-8")
        new_text, n = re.subn(pattern, replacement, text)
        if n == 0:
            print(f"  [警告] {path.name}: 未找到匹配，跳过")
            continue
        path.write_text(new_text, encoding="utf-8")
        print(f"  [OK] {path.name} → {replacement}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: py _bump_version.py <新版本号>  例如: py _bump_version.py 2.8.17")
        sys.exit(1)
    ver = sys.argv[1].strip()
    if not re.match(r'^\d+\.\d+\.\d+$', ver):
        print(f"版本号格式错误: {ver}，应为 x.x.x")
        sys.exit(1)
    print(f"同步版本号 → {ver}")
    bump(ver)
    print("完成")
