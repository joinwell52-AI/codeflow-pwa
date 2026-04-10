"""
可选：通过 JSON-RPC 请求 Cursor 侧「在编辑器内打开 Simple Browser + 布局」类能力（实验性）。

说明：
- 公开文档与各版本行为可能不一致；方法名、参数、监听地址需在你使用的 Cursor 3.x+ 中自行核对。
- 未配置 ``cursor_acp_endpoint``（且未设环境变量 ``CODEFLOW_ACP_ENDPOINT``）时，本模块不执行任何操作。
- 成功时由 ``main`` 跳过系统 ``webbrowser.open`` 与 ``win_snap``，避免重复打开/抢布局。
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("codeflow.acp")


def try_open_simple_browser(
    url: str,
    endpoint: str | None = None,
    *,
    layout: str = "split-right",
    width_ratio: float = 0.35,
    timeout_s: float = 8.0,
) -> tuple[bool, str]:
    """
    发送 JSON-RPC 2.0 请求（HTTP POST + application/json），示例与社区所述 ACP 一致：

    - method: ``workspace/openSimpleBrowser``
    - params: ``url``, ``layout``, ``widthRatio``

    若你的 Cursor 使用其它 method/transport，请改源码或等官方稳定后再接。
    """
    ep = (endpoint or os.environ.get("CODEFLOW_ACP_ENDPOINT") or "").strip()
    if not ep:
        return False, "未配置 cursor_acp_endpoint / CODEFLOW_ACP_ENDPOINT"

    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "workspace/openSimpleBrowser",
        "params": {
            "url": url,
            "layout": layout,
            "widthRatio": float(width_ratio),
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ep,
        data=raw,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, f"HTTP {e.code}: {msg[:200]}"
    except urllib.error.URLError as e:
        return False, f"连接失败: {e.reason}"
    except Exception as e:
        return False, str(e)[:220]

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False, f"非 JSON 响应: {body[:160]}"

    err = data.get("error")
    if err is not None:
        return False, str(err)[:220]

    logger.info("ACP openSimpleBrowser 已返回成功: %s", str(data.get("result"))[:120])
    return True, "ok"

