"""
修复被 PowerShell Set-Content 写坏后 GBK->UTF8 转换产生的多余空行。
规则：连续超过 2 个空行的，压缩为最多 2 个空行（保留正常的段落间距）。
"""
import re

for fname in ['main.py', 'web_panel.py']:
    txt = open(fname, encoding='utf-8').read()
    # 把 3 个以上连续空行压缩为 2 个
    fixed = re.sub(r'\n{4,}', '\n\n\n', txt)
    # 函数体内、类体内不应有连续 2 个空行，压缩为 1 个
    fixed = re.sub(r'(\n    [^\n]+)\n\n\n', r'\1\n\n', fixed)
    open(fname, 'w', encoding='utf-8').write(fixed)
    print(f'fixed: {fname}')

import ast
for fname in ['main.py', 'web_panel.py']:
    try:
        ast.parse(open(fname, encoding='utf-8').read())
        print(f'syntax OK: {fname}')
    except SyntaxError as e:
        print(f'syntax ERROR: {fname}: {e}')
