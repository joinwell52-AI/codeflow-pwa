path = r'd:\BridgeFlow\codeflow-desktop\panel\index.html'
with open(path, encoding='utf-8') as f:
    html = f.read()

old = """function downloadRepo(id, btn){
  const orig=btn.textContent;
  btn.disabled=true; btn.textContent='\u4e0b\u8f7d\u4e2d...';
  fetch('/api/skills/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})})
    .then(r=>r.json()).then(d=>{
      btn.disabled=false; btn.textContent=orig;
      if(d.ok){
        fetchRepos();   // \u5237\u65b0\u4ed3\u5e93\u72b6\u6001
        fetchSkills();  // \u5237\u65b0\u5df2\u4e0b\u8f7d\u5217\u8868
      } else {
        alert('\u5931\u8d25: '+(d.message||'\u672a\u77e5\u9519\u8bef'));
      }
    }).catch(e=>{ btn.disabled=false; btn.textContent=orig; alert('\u8bf7\u6c42\u5931\u8d25: '+e); });
}"""

new = """function downloadRepo(id, btn){
  const orig=btn.textContent;
  btn.disabled=true; btn.textContent='\u4e0b\u8f7d\u4e2d...';
  fetch('/api/skills/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})})
    .then(r=>r.json()).then(d=>{
      btn.disabled=false; btn.textContent=orig;
      if(d.ok){
        fetchRepos();
        fetchSkills();
      } else if(d.no_git){
        // \u672a\u5b89\u88c5 git \u7684\u7279\u6b8a\u63d0\u793a
        const box=document.getElementById('noGitTip');
        if(box){ box.style.display='flex'; }
      } else {
        alert('\u5931\u8d25: '+(d.message||'\u672a\u77e5\u9519\u8bef'));
      }
    }).catch(e=>{ btn.disabled=false; btn.textContent=orig; alert('\u8bf7\u6c42\u5931\u8d25: '+e); });
}"""

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('downloadRepo \u4fee\u590d\u6210\u529f')
else:
    idx = html.find('function downloadRepo')
    print('\u672a\u627e\u5230\u76ee\u6807\uff0c\u5b9e\u9645:')
    print(repr(html[idx:idx+300]))
