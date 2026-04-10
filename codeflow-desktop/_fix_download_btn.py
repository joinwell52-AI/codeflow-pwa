path = r'd:\BridgeFlow\codeflow-desktop\panel\index.html'
with open(path, encoding='utf-8') as f:
    html = f.read()

old = "+'<button class=\"btn sm\" onclick=\"downloadRepo('+JSON.stringify(r.id)+',this)\">'+(dl?'\u66f4\u65b0':'\u4e0b\u8f7d')+'</button>'"
new = "+'<button class=\"btn sm\" onclick=\"downloadRepo(\\''+r.id+'\\',this)\">'+(dl?'\u66f4\u65b0':'\u4e0b\u8f7d')+'</button>'"

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('修复成功')
else:
    idx = html.find('downloadRepo(')
    print('未找到目标，实际:')
    print(repr(html[idx-5:idx+80]))
