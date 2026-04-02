from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re

from bridgeflow.binding import public_bind_state
from bridgeflow.config import PatrolConfig
from bridgeflow.desktop.cursor_probe import snapshot_cursor_state


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_name(value: str) -> str:
    clean = SAFE_NAME_RE.sub("_", value.strip())
    return clean or "unknown"


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _infer_status(config: PatrolConfig, cursor: dict, latest_entry: dict | None) -> tuple[str, int | None]:
    latest_dt = _parse_dt(latest_entry.get("created_at", "")) if latest_entry else None
    age_seconds = None
    if latest_dt is not None:
        age_seconds = int((datetime.now() - latest_dt).total_seconds())
    if not cursor.get("cursor_running"):
        return "未启动", age_seconds
    if age_seconds is not None and age_seconds <= config.idle_seconds:
        if cursor.get("cursor_foreground"):
            return "执行中", age_seconds
        return "忙碌中", age_seconds
    if latest_entry and latest_entry.get("progress") in {"待处理", "处理中"}:
        return "等待中", age_seconds
    if cursor.get("cursor_foreground"):
        return "待命中", age_seconds
    return "空闲", age_seconds


def _build_messages(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in sorted(entries, key=lambda row: row.get("created_at", "")):
        rows.append(
            {
                "filename": item.get("filename", ""),
                "sender": item.get("sender", ""),
                "recipient": item.get("recipient", ""),
                "time": item.get("created_at", ""),
                "type": item.get("type", ""),
                "summary": item.get("summary", ""),
                "body": item.get("body", ""),
                "markdown": item.get("markdown", ""),
            }
        )
    return rows


def _build_detail(entry: dict[str, str], all_entries: list[dict[str, str]]) -> dict:
    thread_key = entry.get("thread_key", "")
    thread_entries = [item for item in all_entries if item.get("thread_key", "") == thread_key] if thread_key else [entry]
    return {
        "task_id": entry.get("task_id", ""),
        "filename": entry.get("filename", ""),
        "type": entry.get("type", ""),
        "time": entry.get("created_at", ""),
        "progress": entry.get("progress", ""),
        "sender": entry.get("sender", ""),
        "recipient": entry.get("recipient", ""),
        "thread_key": thread_key,
        "summary": entry.get("summary", ""),
        "body": entry.get("body", ""),
        "priority": entry.get("priority", ""),
        "task_type": entry.get("task_type", ""),
        "path": entry.get("path", ""),
        "markdown": entry.get("markdown", ""),
        "messages": _build_messages(thread_entries),
    }


def sync_runtime_state(config: PatrolConfig, entries: list[dict[str, str]]) -> dict:
    config.ensure_runtime_dirs()
    cursor = snapshot_cursor_state().to_dict()
    latest_entry = entries[0] if entries else None
    status_text, age_seconds = _infer_status(config, cursor, latest_entry)

    bind_state = public_bind_state(config)
    device_status = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "device": {
            "device_id": config.device_id,
            "device_name": config.device_name,
            "owner_role": config.owner_role,
            "machine_code": config.machine_code,
        },
        "bind": bind_state,
        "ai_team": {
            "fixed_roles": config.fixed_roles,
            "cursor_only": config.cursor_only,
        },
        "cursor": cursor,
        "status": status_text,
        "latest_activity_age_seconds": age_seconds,
        "latest_task_id": latest_entry.get("task_id", "") if latest_entry else "",
        "latest_thread_key": latest_entry.get("thread_key", "") if latest_entry else "",
    }

    task_index = {
        "generated_at": device_status["generated_at"],
        "count": len(entries),
        "items": [
            {
                "task_id": item.get("task_id", ""),
                "filename": item.get("filename", ""),
                "type": item.get("type", ""),
                "time": item.get("created_at", ""),
                "progress": item.get("progress", ""),
                "sender": item.get("sender", ""),
                "recipient": item.get("recipient", ""),
                "thread_key": item.get("thread_key", ""),
                "priority": item.get("priority", ""),
                "task_type": item.get("task_type", ""),
                "summary": item.get("summary", ""),
            }
            for item in entries[:200]
        ],
    }

    last_activity = {
        "generated_at": device_status["generated_at"],
        "status": status_text,
        "latest": latest_entry or {},
        "cursor": cursor,
        "bind": bind_state,
    }

    heartbeat = {
        "generated_at": device_status["generated_at"],
        "device_id": config.device_id,
        "machine_code": config.machine_code,
        "status": status_text,
        "bind_status": bind_state.get("status", "unbound"),
    }

    _write_json(config.device_status_file, device_status)
    _write_json(config.task_index_file, task_index)
    _write_json(config.last_activity_file, last_activity)
    _write_json(config.heartbeat_file, heartbeat)

    current_files: set[str] = set()
    for entry in entries:
        detail = _build_detail(entry, entries)
        filename = f"{_safe_name(entry.get('task_id', entry.get('filename', 'unknown')))}.json"
        current_files.add(filename)
        _write_json(config.task_details_dir / filename, detail)

    for stale_file in config.task_details_dir.glob("*.json"):
        if stale_file.name not in current_files:
            stale_file.unlink(missing_ok=True)

    return {
        "device_status": device_status,
        "task_index": task_index,
        "last_activity": last_activity,
    }
