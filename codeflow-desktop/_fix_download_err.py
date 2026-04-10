path = r'd:\BridgeFlow\codeflow-desktop\panel\index.html'
with open(path, encoding='utf-8') as f:
    html = f.read()

old = """      if(d.ok){
        fetchRepos();
        fetchSkills();
      } else if(d.no_git){
        // \u672a\u5b89\u88c5 git \u7684\u7279\u6b8a\u63d0\u793a
        const box=document.getElementById('noGitTip');
        if(box){ box.style.display='flex'; }
      } else {
        alert('\u5931\u8d25: '+(d.message||'\u672a\u77e5\u9519\u8bef'));
      }"""

new = """      if(d.ok){
        fetchRepos();
        fetchSkills();
      } else if(d.no_git){
        const box=document.getElementById('noGitTip');
        if(box){ box.style.display='flex'; }
      } else {
        // \u663e\u793a\u9519\u8bef\u4fe1\u606f\u5728\u5217\u8868\u9876\u90e8
        const el=document.getElementById('reposList');
        if(el){
          const msg=(d.message||'\u672a\u77e5\u9519\u8bef').replace(/\\n/g,'<br>');
          el.insertAdjacentHTML('afterbegin',
            '<div style="background:#2a0a0a;border:1px solid #ef4444;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:var(--fs-sm);color:#fca5a5;line-height:1.6">'
            +'\u26a0\ufe0f \u4e0b\u8f7d\u5931\u8d25\uff1a<br><span style=\"font-family:monospace;color:#f87171\">'
            +msg+'</span></div>');
        }
      }"""

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('\u4fee\u590d\u6210\u529f')
else:
    print('\u672a\u627e\u5230\u76ee\u6807')
    idx = html.find('fetchRepos();\n        fetchSkills();')
    print(repr(html[idx-5:idx+200]))
