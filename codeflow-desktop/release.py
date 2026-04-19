# -*- coding: utf-8 -*-
"""
CodeFlow Desktop 统一发版脚本
用法：py -3.10 release.py <版本号> <EXE路径>
示例：py -3.10 release.py 2.9.30 dist/CodeFlow-Desktop.exe

功能：
1. 读取 CHANGELOG.md 中对应版本的说明
2. 同时发布到 GitHub Releases + Gitee Releases
3. 上传 EXE 附件到两个平台
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

# ── 配置（按需修改） ─────────────────────────────────────────────────
GITHUB_REPO  = "joinwell52-AI/codeflow-pwa"
GITEE_OWNER  = "joinwell52"
GITEE_REPO   = "cursor-ai"
ASSET_NAME   = "CodeFlow-Desktop.exe"
CHANGELOG    = "../CHANGELOG.md"   # 相对于脚本所在目录


# ── 工具函数 ─────────────────────────────────────────────────────────
GH_CLI = r"C:\Program Files\GitHub CLI\gh.exe"


def get_github_token() -> str:
    gh = GH_CLI if os.path.isfile(GH_CLI) else "gh"
    result = subprocess.run([gh, "auth", "token"], capture_output=True, text=True)
    token = result.stdout.strip()
    if not token:
        print("错误：gh CLI 未登录，请先运行 gh auth login")
        sys.exit(1)
    return token


def read_changelog(version: str) -> str:
    """从 CHANGELOG.md 提取指定版本的说明。"""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, CHANGELOG)
    if not os.path.isfile(path):
        return f"## v{version}\n\n详见 CHANGELOG.md"
    text = open(path, encoding="utf-8").read()
    # 匹配 ## [2.9.30] 或 ## [2.9.30] - 日期 之后、下一个 ## [ 之前的内容
    pattern = rf"## \[?{re.escape(version)}\]?[^\n]*\n(.*?)(?=\n## \[|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return f"## v{version}\n\n" + m.group(1).strip()
    return f"## v{version}\n\n详见 CHANGELOG.md"


def api_request(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if method:
        req.method = method
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ── GitHub ────────────────────────────────────────────────────────────
def github_create_release(tag: str, title: str, notes: str, token: str) -> int:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    payload = json.dumps({
        "tag_name": tag,
        "name": title,
        "body": notes,
        "draft": False,
        "prerelease": False,
    }).encode("utf-8")
    try:
        result = api_request(url, data=payload, headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json;charset=utf-8",
            "User-Agent": "CodeFlow-Releaser",
            "Accept": "application/vnd.github+json",
        })
        return result["id"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 422 and "already_exists" in body:
            print("  GitHub Release 已存在，查询 ID ...")
            r = api_request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}",
                headers={
                    "Authorization": f"token {token}",
                    "User-Agent": "CodeFlow-Releaser",
                    "Accept": "application/vnd.github+json",
                }
            )
            return r["id"]
        raise


def github_upload_asset(release_id: int, exe_path: str, token: str):
    list_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/{release_id}/assets"
    list_req = urllib.request.Request(list_url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "CodeFlow-Releaser",
    })
    try:
        with urllib.request.urlopen(list_req, timeout=30) as resp:
            existing = json.loads(resp.read())
        for asset in existing:
            if asset.get("name") == ASSET_NAME:
                print(f"  GitHub 资产已存在，跳过上传（size={asset.get('size')}）")
                return asset.get("browser_download_url", "")
    except Exception as e:
        print(f"  [警告] 查询已有资产失败（继续尝试上传）：{e}")

    upload_url = f"https://uploads.github.com/repos/{GITHUB_REPO}/releases/{release_id}/assets?name={ASSET_NAME}"
    with open(exe_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(upload_url, data=data, headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream",
        "User-Agent": "CodeFlow-Releaser",
    })
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    return result.get("browser_download_url", "")


# ── Gitee ─────────────────────────────────────────────────────────────
def gitee_get_token() -> str:
    """从环境变量或配置文件读取 Gitee token。"""
    token = os.environ.get("GITEE_TOKEN", "").strip()
    if token:
        return token
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(here, ".gitee_token")
    if os.path.isfile(cfg):
        return open(cfg).read().strip()
    print("  警告：未找到 GITEE_TOKEN，跳过 Gitee 发布")
    print("  可设置环境变量 GITEE_TOKEN 或在脚本目录创建 .gitee_token 文件")
    return ""


def gitee_create_release(tag: str, title: str, notes: str, token: str) -> int:
    url = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases"
    payload = json.dumps({
        "access_token": token,
        "tag_name": tag,
        "name": title,
        "body": notes,
        "prerelease": False,
        "target_commitish": "main",
    }).encode("utf-8")
    try:
        result = api_request(url, data=payload, headers={
            "Content-Type": "application/json;charset=utf-8",
            "User-Agent": "CodeFlow-Releaser",
        })
        return result["id"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code in (400, 422):
            print("  Gitee Release 已存在，查询 ID ...")
            r = api_request(
                f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/tags/{tag}?access_token={token}",
                headers={"User-Agent": "CodeFlow-Releaser"},
            )
            return r["id"]
        raise


def gitee_upload_asset(release_id: int, exe_path: str, token: str) -> str:
    url = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/{release_id}/attach_files"
    boundary = "----CFBoundary20260413"
    sep = f"--{boundary}\r\n".encode()
    end = f"--{boundary}--\r\n".encode()

    with open(exe_path, "rb") as f:
        exe_data = f.read()

    body = b""
    body += sep
    body += b'Content-Disposition: form-data; name="access_token"\r\n\r\n'
    body += token.encode() + b"\r\n"
    body += sep
    body += f'Content-Disposition: form-data; name="file"; filename="{ASSET_NAME}"\r\n'.encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += exe_data + b"\r\n"
    body += end

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "CodeFlow-Releaser",
    })
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
    return result.get("browser_download_url", "")


# ── 主流程 ────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("用法：py -3.10 release.py <版本号> <EXE路径>")
        print("示例：py -3.10 release.py 2.9.30 dist/CodeFlow-Desktop.exe")
        sys.exit(1)

    version  = sys.argv[1].lstrip("v")
    exe_path = sys.argv[2]
    tag      = f"v{version}"

    if not os.path.isfile(exe_path):
        print(f"错误：EXE 文件不存在: {exe_path}")
        sys.exit(1)

    size_mb = round(os.path.getsize(exe_path) / 1024 / 1024, 1)
    notes   = read_changelog(version)
    title   = f"v{version}"

    print(f"\n{'='*50}")
    print(f"  CodeFlow Desktop 发版：{tag}  ({size_mb} MB)")
    print(f"{'='*50}\n")
    print("【发版说明预览】")
    print(notes[:300] + ("..." if len(notes) > 300 else ""))
    print()

    # ── GitHub ──────────────────────────────────────────────────────
    print("[GitHub] 正在发布 ...")
    github_token = get_github_token()
    try:
        rel_id = github_create_release(tag, title, notes, github_token)
        print(f"  Release 已创建，ID={rel_id}")
        print(f"  上传 {size_mb}MB EXE ...")
        gh_url = github_upload_asset(rel_id, exe_path, github_token)
        print(f"  上传完成：{gh_url}")
    except Exception as e:
        print(f"  GitHub 发布失败：{e}")

    # ── Gitee ───────────────────────────────────────────────────────
    print("\n[Gitee] 正在发布 ...")
    gitee_token = gitee_get_token()
    if gitee_token:
        try:
            rel_id = gitee_create_release(tag, title, notes, gitee_token)
            print(f"  Release 已创建，ID={rel_id}")
            print(f"  上传 {size_mb}MB EXE ...")
            gt_url = gitee_upload_asset(rel_id, exe_path, gitee_token)
            print(f"  上传完成：{gt_url}")
        except Exception as e:
            print(f"  Gitee 发布失败：{e}")

    print(f"\n{'='*50}")
    print(f"  发版完成！")
    print(f"  GitHub: https://github.com/{GITHUB_REPO}/releases/tag/{tag}")
    print(f"  Gitee:  https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/releases/tag/{tag}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
