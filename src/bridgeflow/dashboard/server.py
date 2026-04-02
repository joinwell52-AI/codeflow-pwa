"""
BridgeFlow 本地仪表盘 HTTP 服务器
地址：http://localhost:18765
提供环境检测、连接状态、机器码等接口
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bridgeflow.config import PatrolConfig

DASHBOARD_PORT = int(os.environ.get("BRIDGEFLOW_DASHBOARD_PORT", "18765"))

# 全局状态（由主循环写入，dashboard 读取）
_status: dict = {
    "relay_connected": False,
    "relay_url": "",
    "room_key": "",
    "device_id": "",
    "device_name": "",
    "machine_code": "",
    "bind_status": "unbound",
    "env": {},
    "task_count": 0,
    "reply_count": 0,
}
_lock = threading.Lock()


def update_status(**kwargs) -> None:
    with _lock:
        _status.update(kwargs)


def get_status() -> dict:
    with _lock:
        return dict(_status)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 关闭访问日志

    def _send_json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_png(self, data: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json(get_status())
        elif self.path.startswith("/api/qr"):
            # 生成机器码二维码 PNG
            try:
                import io
                import urllib.parse
                import segno
                status = get_status()
                mc = status.get("machine_code") or "BF-UNKNOWN"
                relay = status.get("relay_url", "")
                room = status.get("room_key", "")
                device_id = status.get("device_id", "")
                # 二维码内容：包含完整连接信息，手机扫一次全配置好
                params = urllib.parse.urlencode({
                    "machine_code": mc,
                    "relay": relay,
                    "room": room,
                    "device_id": device_id,
                })
                qr_content = f"bridgeflow://bind?{params}"
                qr = segno.make_qr(qr_content, error="M")
                buf = io.BytesIO()
                qr.save(buf, kind="png", scale=4, border=2)
                self._send_png(buf.getvalue())
            except Exception as exc:
                self.send_response(500)
                self.end_headers()
        elif self.path in ("/", "/index.html"):
            html_path = Path(__file__).parent / "index.html"
            self._send_html(html_path.read_text(encoding="utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(config: "PatrolConfig") -> None:
    """在后台线程启动仪表盘 HTTP 服务器"""
    from bridgeflow.env_check import check_env

    env = check_env()
    update_status(
        relay_url=config.relay_url,
        room_key=config.room_key,
        device_id=config.device_id,
        device_name=config.device_name,
        machine_code=config.machine_code,
        bind_status=config.bind_status,
        env=env.to_dict(),
    )

    server = HTTPServer(("127.0.0.1", DASHBOARD_PORT), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
