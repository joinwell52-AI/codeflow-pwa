from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from bridgeflow.binding import approve_bind, clear_binding, issue_bind_code, private_bind_state, public_bind_state
from bridgeflow.config import PatrolConfig
from bridgeflow.desktop.executor import execute_desktop_action
from bridgeflow.desktop.status_store import sync_runtime_state
from bridgeflow.file_protocol import parse_task_markdown
from bridgeflow.models.events import RelayEvent
from bridgeflow.relay_client.ws_client import run_client, send_event
from bridgeflow.task_writer import write_admin_task


DESKTOP_SENDER = "DESKTOP01"


def _load_markdown_info(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    info = parse_task_markdown(text, filename=path.name)
    info["summary"] = (info.get("title") or path.name).lstrip("\ufeff")
    info["markdown"] = text
    return info


def _is_reply_to_admin(path: Path, admin_sender: str) -> bool:
    info = _load_markdown_info(path)
    return info.get("recipient", "").strip().upper() == admin_sender.upper()


def _task_id_from_filename(filename: str) -> str:
    return filename[:-3] if filename.lower().endswith(".md") else filename


def _collect_entries(config: PatrolConfig) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for directory_name, directory in (("tasks", config.tasks_dir), ("reports", config.reports_dir)):
        directory.mkdir(parents=True, exist_ok=True)
        for file in sorted(directory.glob("TASK-*.md")):
            info = _load_markdown_info(file)
            entry_type = "回复" if info.get("recipient", "").strip().upper() == config.admin_sender.upper() else "任务"
            created_at = info.get("created_at", "")
            entries.append(
                {
                    "filename": file.name,
                    "task_id": _task_id_from_filename(file.name),
                    "directory": directory_name,
                    "type": entry_type,
                    "title": info.get("title", file.name),
                    "summary": info.get("summary", file.name),
                    "body": info.get("body", ""),
                    "markdown": info.get("markdown", ""),
                    "sender": info.get("sender", ""),
                    "recipient": info.get("recipient", ""),
                    "priority": info.get("priority", ""),
                    "task_type": info.get("task_type", ""),
                    "thread_key": info.get("thread_key", ""),
                    "client_message_id": info.get("client_message_id", ""),
                    "created_at": created_at,
                    "path": str(file),
                }
            )
    entries.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return entries


def _parse_created_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _find_duplicate_admin_task(
    config: PatrolConfig,
    *,
    text: str,
    recipient: str,
    thread_key: str,
    client_message_id: str,
) -> dict[str, str] | None:
    now = datetime.now()
    for entry in _collect_entries(config):
        if entry.get("type") != "任务":
            continue
        if entry.get("sender", "").strip().upper() != config.admin_sender.upper():
            continue
        if entry.get("recipient", "").strip() != recipient:
            continue
        if client_message_id and entry.get("client_message_id", "") == client_message_id:
            return entry
        if entry.get("thread_key", "") != thread_key:
            continue
        if entry.get("body", "").strip() != text:
            continue
        created_at = _parse_created_at(entry.get("created_at", ""))
        if created_at and now - created_at <= timedelta(seconds=90):
            return entry
    return None


def _apply_progress(entries: list[dict[str, str]], admin_sender: str) -> list[dict[str, str]]:
    by_thread: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        thread_key = entry.get("thread_key", "")
        by_thread.setdefault(thread_key, []).append(entry)

    for entry in entries:
        thread_entries = by_thread.get(entry.get("thread_key", ""), [])
        if any(item.get("recipient", "").upper() == admin_sender.upper() for item in thread_entries):
            progress = "已回复"
        elif any(item.get("sender", "").upper() != admin_sender.upper() for item in thread_entries):
            progress = "处理中"
        else:
            progress = "待处理"
        entry["progress"] = progress
    return entries


def _current_entries(config: PatrolConfig) -> list[dict[str, str]]:
    return _apply_progress(_collect_entries(config), config.admin_sender)


def _build_dashboard_payload(config: PatrolConfig, entries: list[dict[str, str]], snapshot: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    today_entries = [item for item in entries if item.get("created_at", "").startswith(today)]
    today_tasks = sum(1 for item in today_entries if item.get("type") == "任务")
    today_replies = sum(1 for item in today_entries if item.get("type") == "回复")
    thread_progress: dict[str, str] = {}
    for item in entries:
        thread_key = item.get("thread_key", "")
        if not thread_key:
            continue
        thread_progress[thread_key] = item.get("progress", "待处理")
    stats = {
        "today_tasks": today_tasks,
        "today_replies": today_replies,
        "in_progress_threads": sum(1 for value in thread_progress.values() if value == "处理中"),
        "replied_threads": sum(1 for value in thread_progress.values() if value == "已回复"),
        "pending_threads": sum(1 for value in thread_progress.values() if value == "待处理"),
    }
    list_items = [
        {
            "task_id": item["task_id"],
            "filename": item["filename"],
            "type": item["type"],
            "time": item["created_at"],
            "progress": item["progress"],
            "sender": item["sender"],
            "recipient": item["recipient"],
            "thread_key": item["thread_key"],
            "priority": item["priority"],
            "task_type": item["task_type"],
            "summary": item["summary"],
        }
        for item in entries[:100]
    ]
    bind_state = public_bind_state(config)
    return {
        "default_target": config.admin_target,
        "roles": config.sendable_roles,
        "device": {
            "device_id": config.device_id,
            "device_name": config.device_name,
            "owner_role": config.owner_role,
            "machine_code": config.machine_code,
            "bind_status": config.bind_status,
            "fixed_roles": config.fixed_roles,
            "cursor_only": config.cursor_only,
            "status": snapshot.get("device_status", {}).get("status", ""),
        },
        "bind": bind_state,
        "stats": stats,
        "items": list_items,
        "runtime": snapshot,
    }


def _build_task_detail(filename: str, entries: list[dict[str, str]]) -> dict:
    for entry in entries:
        if entry.get("filename") == filename:
            thread_key = entry.get("thread_key", "")
            thread_entries = [item for item in entries if item.get("thread_key", "") == thread_key] if thread_key else [entry]
            thread_entries.sort(key=lambda item: item.get("created_at") or "")
            messages = [
                {
                    "filename": item["filename"],
                    "sender": item["sender"],
                    "recipient": item["recipient"],
                    "time": item["created_at"],
                    "type": item["type"],
                    "summary": item["summary"],
                    "body": item["body"],
                    "markdown": item["markdown"],
                }
                for item in thread_entries
            ]
            return {
                "task_id": entry["task_id"],
                "filename": entry["filename"],
                "type": entry["type"],
                "time": entry["created_at"],
                "progress": entry["progress"],
                "sender": entry["sender"],
                "recipient": entry["recipient"],
                "thread_key": entry["thread_key"],
                "summary": entry["summary"],
                "body": entry["body"],
                "priority": entry["priority"],
                "task_type": entry["task_type"],
                "path": entry["path"],
                "flow_path": f"{entry['sender']} -> {entry['recipient']}",
                "markdown": entry["markdown"],
                "messages": messages,
            }
    return {}


async def start_desktop_bridge(
    config: PatrolConfig,
    on_connected=None,
    on_disconnected=None,
) -> None:
    config.validate_device()
    config.validate_roles()
    config.ensure_runtime_dirs()
    seen_reply_files: set[str] = set()

    async def emit_event(event_type: str, payload: dict) -> None:
        await send_event(
            config.relay_url,
            RelayEvent(
                room_key=config.room_key,
                sender=DESKTOP_SENDER,
                client_type="desktop",
                event_type=event_type,
                payload=payload,
            ),
        )

    async def on_message(data: dict) -> None:
        if data.get("room_key") != config.room_key:
            return

        event_type = str(data.get("event_type", "")).strip()
        payload = data.get("payload", {})
        target_device_id = str(payload.get("target_device_id", "")).strip()
        if target_device_id and target_device_id != config.device_id:
            return

        if event_type == "command_from_admin":
            text = str(payload.get("text", "")).strip()
            if not text:
                return
            recipient = str(payload.get("target_role", "")).strip() or config.admin_target
            thread_key = str(payload.get("thread_key", "")).strip()
            client_message_id = str(payload.get("message_id", "")).strip()
            duplicate = _find_duplicate_admin_task(
                config,
                text=text,
                recipient=recipient,
                thread_key=thread_key,
                client_message_id=client_message_id,
            )
            if duplicate:
                entries = _current_entries(config)
                sync_runtime_state(config, entries)
                await emit_event(
                    "task_event",
                    {
                        "filename": duplicate["filename"],
                        "thread_key": duplicate["thread_key"],
                        "path": duplicate["path"],
                        "message_id": client_message_id,
                        "duplicate": True,
                    },
                )
                return

            written = write_admin_task(
                config,
                text,
                recipient=recipient,
                priority=str(payload.get("priority", config.default_priority)),
                attachments=list(payload.get("attachments", [])),
                thread_key=thread_key or None,
                client_message_id=client_message_id,
            )
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            await emit_event(
                "task_event",
                {
                    "filename": written.filename,
                    "thread_key": written.thread_key,
                    "path": str(written.path),
                    "message_id": client_message_id,
                },
            )
            return

        if event_type == "request_dashboard":
            entries = _current_entries(config)
            snapshot = sync_runtime_state(config, entries)
            await emit_event("dashboard_state", _build_dashboard_payload(config, entries, snapshot))
            return

        if event_type == "request_task_detail":
            filename = str(payload.get("filename", "")).strip()
            if not filename:
                return
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            await emit_event("task_detail", _build_task_detail(filename, entries))
            return

        if event_type == "request_bind_state":
            await emit_event("bind_state", public_bind_state(config))
            return

        if event_type == "request_bind_code":
            state = issue_bind_code(
                config,
                mobile_device_id=str(payload.get("mobile_device_id", "")).strip(),
                mobile_device_name=str(payload.get("mobile_device_name", "")).strip(),
            )
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            await emit_event("bind_state", state)
            return

        if event_type == "approve_bind":
            try:
                state = approve_bind(
                    config,
                    bind_code=str(payload.get("bind_code", "")).strip(),
                    mobile_device_id=str(payload.get("mobile_device_id", "")).strip(),
                    mobile_device_name=str(payload.get("mobile_device_name", "")).strip(),
                )
                ok = True
                error = ""
            except ValueError as exc:
                state = private_bind_state(config)
                ok = False
                error = str(exc)
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            await emit_event("bind_state", {**state, "ok": ok, "error": error})
            return

        if event_type == "unbind_device":
            state = clear_binding(config)
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            await emit_event("bind_state", {**state, "ok": True, "error": ""})
            return

        if event_type == "execute_desktop_action":
            action = str(payload.get("action", "")).strip()
            dry_run = payload.get("dry_run", False) is True
            result = execute_desktop_action(config, action, dry_run=dry_run).to_dict()
            entries = _current_entries(config)
            snapshot = sync_runtime_state(config, entries)
            await emit_event("desktop_action_result", {**result, "runtime": snapshot})
            return

    async def watch_replies() -> None:
        while True:
            config.tasks_dir.mkdir(parents=True, exist_ok=True)
            config.reports_dir.mkdir(parents=True, exist_ok=True)
            entries = _current_entries(config)
            sync_runtime_state(config, entries)
            for directory in (config.tasks_dir, config.reports_dir):
                for file in sorted(directory.glob("*.md")):
                    file_key = str(file.resolve())
                    if file_key in seen_reply_files:
                        continue
                    if not _is_reply_to_admin(file, config.admin_sender):
                        continue
                    seen_reply_files.add(file_key)
                    info = _load_markdown_info(file)
                    await emit_event(
                        "reply_summary",
                        {
                            "filename": file.name,
                            "summary": info.get("summary", file.name),
                            "title": info.get("title", ""),
                            "thread_key": info.get("thread_key", ""),
                            "sender": info.get("sender", ""),
                            "path": str(file),
                        },
                    )
            await asyncio.sleep(2)

    hello_event = RelayEvent(
        room_key=config.room_key,
        sender=DESKTOP_SENDER,
        client_type="desktop",
        event_type="hello",
        payload={
            "role": "desktop_bridge",
            "device_id": config.device_id,
            "device_name": config.device_name,
            "owner_role": config.owner_role,
            "machine_code": config.machine_code,
            "bind_status": config.bind_status,
            "bind": public_bind_state(config),
            "fixed_roles": config.fixed_roles,
            "cursor_only": config.cursor_only,
            "actions": ["focus_cursor", "inspect", "start_work"],
        },
    )
    await asyncio.gather(
        run_client(
            config.relay_url,
            on_message,
            hello_event,
            on_connected=on_connected,
            on_disconnected=on_disconnected,
        ),
        watch_replies(),
    )
