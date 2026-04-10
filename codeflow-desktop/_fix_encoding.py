"""修复 web_panel.py 的 BOM 头问题"""
with open('web_panel.py', 'rb') as f:
    data = f.read()

# 去掉 UTF-8 BOM
if data.startswith(b'\xef\xbb\xbf'):
    data = data[3:]
    print('BOM removed')

# 写回
with open('web_panel.py', 'wb') as f:
    f.write(data)

# 验证语法
import ast
try:
    ast.parse(data.decode('utf-8'))
    print('web_panel.py syntax OK')
except SyntaxError as e:
    print('SyntaxError:', e)
