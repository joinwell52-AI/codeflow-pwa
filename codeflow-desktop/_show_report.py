import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
data = json.loads(Path('cursor_vision_report.json').read_text(encoding='utf-8'))
print('=== 所有 OCR 行（含坐标）===')
for ln in data['all_lines']:
    print(f"  [{ln['x']:.0f},{ln['y']:.0f}] {ln['text']!r}")
