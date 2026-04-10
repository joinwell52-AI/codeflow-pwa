path = r'd:\BridgeFlow\codeflow-desktop\panel\index.html'
with open(path, encoding='utf-8') as f:
    html = f.read()

old = '        <div id="reposList"><div class="empty" style="font-size:var(--fs-sm)">\u70b9\u51fb\u300c\u5237\u65b0\u300d\u67e5\u770b\u53ef\u4e0b\u8f7d\u7684\u6280\u80fd\u5305</div></div>'

new = ('        <div id="noGitTip" style="display:none;align-items:flex-start;gap:8px;'
       'background:#2a1a0a;border:1px solid #f59e0b;border-radius:6px;padding:8px 10px;margin-bottom:8px">'
       '<span style="font-size:16px">\u26a0\ufe0f</span>'
       '<div style="font-size:var(--fs-sm);line-height:1.6;color:#fbbf24">'
       '<b>\u672a\u68c0\u6d4b\u5230 git</b>\uff0c\u8bf7\u5148\u5b89\u88c5 <b>Git for Windows</b>\uff1a<br>'
       '<a href="https://git-scm.com/download/win" target="_blank" '
       'style="color:#60a5fa;text-decoration:underline">https://git-scm.com/download/win</a><br>'
       '<span style="color:var(--dim)">\u5b89\u88c5\u540e\u91cd\u542f\u672c\u7a0b\u5e8f\u5373\u53ef\u3002</span>'
       '</div>'
       '<button onclick="document.getElementById(\'noGitTip\').style.display=\'none\'" '
       'style="background:none;border:none;color:var(--dim);cursor:pointer;font-size:14px;padding:0 4px;margin-left:auto">\u00d7</button>'
       '</div>\n'
       '        <div id="reposList"><div class="empty" style="font-size:var(--fs-sm)">\u70b9\u51fb\u300c\u5237\u65b0\u300d\u67e5\u770b\u53ef\u4e0b\u8f7d\u7684\u6280\u80fd\u5305</div></div>')

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('\u63d0\u793a\u6761\u6dfb\u52a0\u6210\u529f')
else:
    print('\u672a\u627e\u5230\u76ee\u6807')
    idx = html.find('reposList')
    print(repr(html[idx-10:idx+120]))
