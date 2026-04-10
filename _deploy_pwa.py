"""
PWA 发布脚本：把 web/pwa/ 里的文件推送到 codeflow-pwa 仓库（GitHub Pages）。

用法：
    py -3 _deploy_pwa.py

每次修改 web/pwa/ 后运行此脚本即可发布到手机端。
"""
import urllib.request
import urllib.error
import json
import base64
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────
REPO = "joinwell52-AI/codeflow-pwa"
BRANCH = "main"
PWA_DIR = Path(__file__).parent / "web" / "pwa"
FILES = [
    "index.html",
    "config.js",
    "sw.js",
    "manifest.json",
    "logo-CodeFlow-125.png",
]

# Token 从本地文件读取，避免硬编码
TOKEN_FILE = Path(__file__).parent / ".github_token"
if TOKEN_FILE.exists():
    TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
else:
    import os
    TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not TOKEN:
    print("错误：未找到 GitHub Token")
    print(f"请把 Token 写入文件：{TOKEN_FILE}")
    exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
    "User-Agent": "codeflow-deploy",
}

def api(method, path, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read()
            return r.status, json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        txt = e.read()
        return e.code, json.loads(txt) if txt else {}

# 读取 config.js 里的版本号
version = "?"
cfg = PWA_DIR / "config.js"
if cfg.exists():
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if "appVersion" in line:
            version = line.strip().split('"')[1]
            break

print(f"发布 PWA v{version} → {REPO}")
print("-" * 40)

ok_count = 0
for fname in FILES:
    fpath = PWA_DIR / fname
    if not fpath.exists():
        print(f"  跳过（不存在）: {fname}")
        continue

    content = base64.b64encode(fpath.read_bytes()).decode()
    status, existing = api("GET", f"/repos/{REPO}/contents/{fname}?ref={BRANCH}")
    sha = existing.get("sha") if status == 200 else None

    body = {
        "message": f"deploy: {fname} v{version}",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        body["sha"] = sha

    status, result = api("PUT", f"/repos/{REPO}/contents/{fname}", body)
    if status in (200, 201):
        print(f"  OK  {fname}")
        ok_count += 1
    else:
        print(f"  FAIL {fname}: {status} {result.get('message','')}")

print("-" * 40)
print(f"完成：{ok_count}/{len(FILES)} 个文件")
print(f"PWA 地址：https://joinwell52-ai.github.io/codeflow-pwa/")
print("手机刷新后版本号变为", version)
