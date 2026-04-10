path = r'd:\BridgeFlow\codeflow-desktop\panel\index.html'
with open(path, encoding='utf-8') as f:
    html = f.read()

old = '<script src="qrcode.min.js">\n\n/* \u2500\u2500 \u6280\u80fd\u5e02\u573a\uff1a\u4ed3\u5e93\u4e0b\u8f7d \u2500\u2500 */'
new = '<script src="qrcode.min.js"></script>\n<script>\n/* \u2500\u2500 \u6280\u80fd\u5e02\u573a\uff1a\u4ed3\u5e93\u4e0b\u8f7d \u2500\u2500 */'

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('修复成功')
else:
    idx = html.find('qrcode.min.js')
    print('未找到目标，实际内容:')
    print(repr(html[idx-2:idx+120]))
