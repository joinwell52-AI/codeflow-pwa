from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path
from textwrap import dedent

from scp import SCPClient


ROOT = Path(__file__).resolve().parents[2]
OPS_PATH = ROOT / "ops" / "ops.py"
LOCAL_RELAY = ROOT / "CodeFlow" / "server" / "relay" / "server.py"

REMOTE_BASE = "/opt/codeflow"
REMOTE_SERVER = f"{REMOTE_BASE}/server.py"
REMOTE_VENV = f"{REMOTE_BASE}/venv"
REMOTE_UNIT = "/etc/systemd/system/codeflow-relay.service"
REMOTE_NGINX_SITE = os.environ.get("BRIDGEFLOW_NGINX_SITE", "/etc/nginx/sites-enabled/codeflow-site")
PUBLIC_WSS = "wss://relay.example.com/codeflow/ws/"

BLOCK_BEGIN = "# === CodeFlow WS BEGIN ==="
BLOCK_END = "# === CodeFlow WS END ==="
NGINX_BLOCK = dedent(
    f"""
    {BLOCK_BEGIN}
        location /codeflow/ws/ {{
            proxy_pass http://127.0.0.1:5252/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 600s;
            proxy_send_timeout 600s;
            proxy_buffering off;
        }}
    {BLOCK_END}
    """
).strip("\n")

UNIT_TEXT = dedent(
    f"""
    [Unit]
    Description=CodeFlow Relay
    After=network.target

    [Service]
    Type=simple
    WorkingDirectory={REMOTE_BASE}
    Environment=CODEFLOW_RELAY_HOST=127.0.0.1
    Environment=CODEFLOW_RELAY_PORT=5252
    ExecStart={REMOTE_VENV}/bin/python {REMOTE_SERVER}
    Restart=always
    RestartSec=3
    User=root

    [Install]
    WantedBy=multi-user.target
    """
).strip() + "\n"


def load_ops():
    spec = importlib.util.spec_from_file_location("codeflow_ops", OPS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 ops.py: {OPS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_remote_dirs(ops) -> None:
    ops.run_remote(f"mkdir -p {REMOTE_BASE}", silent=True)


def upload_relay(ops) -> None:
    ssh = ops.get_ssh()
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(str(LOCAL_RELAY), REMOTE_SERVER)


def upload_text(ops, content: str, remote_path: str) -> None:
    ssh = ops.get_ssh()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(tmp_path, remote_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def ensure_remote_venv(ops) -> None:
    ops.run_remote(f"python3 -m venv {REMOTE_VENV}", silent=True)
    ops.run_remote(f"{REMOTE_VENV}/bin/pip install -U pip >/dev/null", timeout=120, silent=True)
    ops.run_remote(f"{REMOTE_VENV}/bin/pip install 'websockets>=12,<16' >/dev/null", timeout=120)


def write_systemd_unit(ops) -> None:
    tmp_remote = f"{REMOTE_BASE}/codeflow-relay.service"
    upload_text(ops, UNIT_TEXT, tmp_remote)
    ops.run_remote(f"cp {tmp_remote} {REMOTE_UNIT}", silent=True)


def patch_nginx_site(ops) -> None:
    site_text = ops.run_remote(f"cat {REMOTE_NGINX_SITE}", silent=True)
    if BLOCK_BEGIN in site_text:
        print("  [跳过] Nginx 已存在 CodeFlow WS 配置块")
        return

    anchor = "    listen 443 ssl;"
    if anchor not in site_text:
        raise RuntimeError("远端 Nginx 站点中未找到 SSL server 的 listen 443 锚点")

    updated = site_text.replace(anchor, f"{NGINX_BLOCK}\n\n{anchor}", 1)
    backup = f"{REMOTE_BASE}/codeflow-site.bak"
    tmp_remote = f"{REMOTE_BASE}/codeflow-site.nginx.tmp"
    upload_text(ops, updated, tmp_remote)
    ops.run_remote(f"cp {REMOTE_NGINX_SITE} {backup}", silent=True)
    ops.run_remote(f"cp {tmp_remote} {REMOTE_NGINX_SITE}", silent=True)


def restart_services(ops) -> None:
    ops.run_remote("systemctl daemon-reload")
    ops.run_remote("systemctl enable codeflow-relay")
    ops.run_remote("systemctl restart codeflow-relay")
    ops.run_remote("systemctl status codeflow-relay --no-pager | head -20")
    ops.run_remote("nginx -t")
    ops.run_remote("nginx -s reload")


def verify_remote(ops) -> None:
    print("\n[verify] 远端 relay 进程")
    print(ops.run_remote("systemctl is-active codeflow-relay", silent=True))
    print("\n[verify] 远端 5252 监听")
    print(ops.run_remote("ss -ltnp | grep 5252", silent=True))
    print("\n[verify] Nginx 路径")
    print(ops.run_remote(f"grep -n 'CodeFlow/ws' {REMOTE_NGINX_SITE}", silent=True))


def main() -> None:
    ops = load_ops()
    print("[1/6] 创建远端目录")
    ensure_remote_dirs(ops)
    print("[2/6] 上传 relay 服务端")
    upload_relay(ops)
    print("[3/6] 准备独立 venv")
    ensure_remote_venv(ops)
    print("[4/6] 写入 systemd 服务")
    write_systemd_unit(ops)
    print("[5/6] 注入 Nginx WebSocket 反代")
    patch_nginx_site(ops)
    print("[6/6] 重载服务并验证")
    restart_services(ops)
    verify_remote(ops)
    print(f"\n公网地址：{PUBLIC_WSS}")


if __name__ == "__main__":
    main()
