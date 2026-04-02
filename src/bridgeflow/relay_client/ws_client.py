from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

import websockets

from bridgeflow.models.events import RelayEvent


EventHandler = Callable[[dict], Awaitable[None]]


async def send_event(url: str, event: RelayEvent) -> None:
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(event.to_dict(), ensure_ascii=False))


async def run_client(
    url: str,
    on_message: EventHandler,
    initial_event: RelayEvent | None = None,
    on_connected: Callable[[], None] | None = None,
    on_disconnected: Callable[[Exception], None] | None = None,
) -> None:
    import sys
    while True:
        try:
            async with websockets.connect(url) as ws:
                if on_connected:
                    on_connected()
                if initial_event is not None:
                    await ws.send(json.dumps(initial_event.to_dict(), ensure_ascii=False))
                async for message in ws:
                    data = json.loads(message)
                    await on_message(data)
        except Exception as exc:
            if on_disconnected:
                on_disconnected(exc)
            else:
                print(f"[BridgeFlow] 连接断开：{exc}，2秒后重试…", file=sys.stderr)
            await asyncio.sleep(2)
