import asyncio
import json
import os
import time
from collections import defaultdict, deque

import websockets
from websockets.exceptions import ConnectionClosed


rooms: dict[str, set] = defaultdict(set)
connection_windows: dict[object, deque[float]] = defaultdict(deque)
room_devices: dict[str, dict[str, dict]] = defaultdict(dict)
connection_meta: dict[object, dict] = {}
ALLOWED_EVENTS = {
    "hello",
    "ping",
    "command_from_admin",
    "admin_command",
    "task_event",
    "reply_summary",
    "alert",
    "request_dashboard",
    "dashboard_state",
    "request_task_detail",
    "task_detail",
    "request_device_roster",
    "device_roster",
    # Phase 2 — MCP ↔ 手机端同步
    "file_list",
    "file_change",
    "agent_status",
    "message_history",
    "request_message_history",
    # PWA → PC 控制指令（定向投递）
    "start_patrol",
    "stop_patrol",
    "patrol_status",
    "patrol_state",
    "request_bind_state",
    "request_bind_code",
    "bind_state",
    "execute_desktop_action",
    "desktop_action_result",
}
MAX_MESSAGE_BYTES = 8 * 1024
TRANSPORT_MAX_BYTES = 16 * 1024
RATE_LIMIT_COUNT = 20
RATE_LIMIT_WINDOW_SEC = 10
MAX_ROOM_KEY_LENGTH = 64
RELAY_HOST = os.environ.get("BRIDGEFLOW_RELAY_HOST", "0.0.0.0")
RELAY_PORT = int(os.environ.get("BRIDGEFLOW_RELAY_PORT", "5252"))


async def send_alert(websocket, message: str, room_key: str = "") -> None:
    await websocket.send(
        json.dumps(
            {
                "room_key": room_key,
                "event_type": "alert",
                "payload": {"message": message},
            },
            ensure_ascii=False,
        )
    )


def allow_request(websocket) -> bool:
    now = time.monotonic()
    window = connection_windows[websocket]
    while window and now - window[0] > RATE_LIMIT_WINDOW_SEC:
        window.popleft()
    if len(window) >= RATE_LIMIT_COUNT:
        return False
    window.append(now)
    return True


async def cleanup_room(room_key: str, websocket) -> None:
    members = rooms.get(room_key)
    if not members:
        connection_windows.pop(websocket, None)
        connection_meta.pop(websocket, None)
        return
    roster_changed = False
    members.discard(websocket)
    if not members:
        rooms.pop(room_key, None)
    meta = connection_meta.pop(websocket, None) or {}
    device_id = str(meta.get("device_id", "")).strip()
    if device_id:
        devices = room_devices.get(room_key, {})
        if device_id in devices:
            devices.pop(device_id, None)
            roster_changed = True
        if not devices:
            room_devices.pop(room_key, None)
    connection_windows.pop(websocket, None)
    if roster_changed and room_key in rooms:
        await send_device_roster(room_key)


def device_roster_payload(room_key: str) -> dict:
    devices = sorted(
        room_devices.get(room_key, {}).values(),
        key=lambda item: (item.get("owner_role", ""), item.get("device_name", ""), item.get("device_id", "")),
    )
    return {"devices": devices}


async def send_device_roster(room_key: str) -> None:
    message = json.dumps(
        {
            "room_key": room_key,
            "event_type": "device_roster",
            "payload": device_roster_payload(room_key),
        },
        ensure_ascii=False,
    )
    stale = []
    for conn in list(rooms.get(room_key, set())):
        try:
            await conn.send(message)
        except ConnectionClosed:
            stale.append(conn)
    for conn in stale:
        await cleanup_room(room_key, conn)


async def broadcast(room_key: str, message: str, sender) -> None:
    stale = []
    for conn in list(rooms.get(room_key, set())):
        if conn == sender:
            continue
        try:
            await conn.send(message)
        except ConnectionClosed:
            stale.append(conn)
    for conn in stale:
        await cleanup_room(room_key, conn)


async def send_to_device(room_key: str, target_device_id: str, message: str) -> bool:
    stale = []
    delivered = False
    for conn in list(rooms.get(room_key, set())):
        meta = connection_meta.get(conn, {})
        if meta.get("device_id") != target_device_id:
            continue
        try:
            await conn.send(message)
            delivered = True
        except ConnectionClosed:
            stale.append(conn)
    for conn in stale:
        await cleanup_room(room_key, conn)
    return delivered


async def relay_handler(websocket) -> None:
    joined_room = None
    try:
        async for raw in websocket:
            if not isinstance(raw, str):
                await send_alert(websocket, "仅支持文本消息")
                continue
            if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await send_alert(websocket, f"消息过大，限制 {MAX_MESSAGE_BYTES} 字节")
                continue
            if not allow_request(websocket):
                await send_alert(websocket, "发送过于频繁，请稍后再试", joined_room or "")
                await websocket.close(code=4008, reason="rate limit")
                return

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_alert(websocket, "消息不是合法 JSON", joined_room or "")
                continue
            if not isinstance(data, dict):
                await send_alert(websocket, "消息格式必须是 JSON 对象", joined_room or "")
                continue

            room_key = str(data.get("room_key", "")).strip()
            event_type = str(data.get("event_type", "")).strip()
            if not room_key:
                await send_alert(websocket, "缺少 room_key")
                continue
            if len(room_key) > MAX_ROOM_KEY_LENGTH:
                await send_alert(websocket, f"room_key 过长，限制 {MAX_ROOM_KEY_LENGTH} 字符", room_key)
                continue
            if event_type not in ALLOWED_EVENTS:
                await send_alert(websocket, f"不支持的事件类型: {event_type}", room_key)
                continue
            if event_type != "ping" and not isinstance(data.get("payload", {}), dict):
                await send_alert(websocket, "payload 必须是 JSON 对象", room_key)
                continue

            if joined_room is None:
                joined_room = room_key
                rooms[room_key].add(websocket)

            if event_type == "ping":
                await websocket.send(json.dumps({"room_key": room_key, "event_type": "pong", "payload": {}}))
                continue

            payload = data.get("payload", {})
            if event_type == "hello":
                device_id = str(payload.get("device_id", "")).strip()
                device_name = str(payload.get("device_name", "")).strip()
                owner_role = str(payload.get("owner_role", "")).strip()
                if websocket in connection_meta:
                    old_meta = connection_meta.get(websocket, {})
                    old_device_id = str(old_meta.get("device_id", "")).strip()
                    if old_device_id and old_device_id != device_id:
                        room_devices.get(room_key, {}).pop(old_device_id, None)
                connection_meta[websocket] = {
                    "room_key": room_key,
                    "device_id": device_id,
                    "device_name": device_name,
                    "owner_role": owner_role,
                    "sender": str(data.get("sender", "")).strip(),
                    "client_type": str(data.get("client_type", "")).strip(),
                }
                if device_id:
                    room_devices[room_key][device_id] = {
                        "device_id": device_id,
                        "device_name": device_name or device_id,
                        "owner_role": owner_role,
                        "sender": str(data.get("sender", "")).strip(),
                        "client_type": str(data.get("client_type", "")).strip(),
                    }
                await send_device_roster(room_key)
                continue

            if event_type == "request_device_roster":
                await websocket.send(
                    json.dumps(
                        {"room_key": room_key, "event_type": "device_roster", "payload": device_roster_payload(room_key)},
                        ensure_ascii=False,
                    )
                )
                continue

            if event_type in {
                "command_from_admin",
                "admin_command",
                "request_dashboard",
                "request_task_detail",
                "request_message_history",
                "start_patrol",
                "stop_patrol",
                "patrol_status",
                "request_bind_state",
                "request_bind_code",
                "execute_desktop_action",
            }:
                target_device_id = str(payload.get("target_device_id", "")).strip()
                if not target_device_id:
                    await send_alert(websocket, "缺少 target_device_id，无法定向投递", room_key)
                    continue
                delivered = await send_to_device(room_key, target_device_id, raw)
                if not delivered:
                    await send_alert(websocket, f"目标设备不在线: {target_device_id}", room_key)
                continue

            await broadcast(room_key, raw, websocket)
    finally:
        if joined_room:
            await cleanup_room(joined_room, websocket)
        else:
            connection_windows.pop(websocket, None)


async def main() -> None:
    async with websockets.serve(
        relay_handler,
        RELAY_HOST,
        RELAY_PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=TRANSPORT_MAX_BYTES,
    ):
        print(f"BridgeFlow relay running on {RELAY_HOST}:{RELAY_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
