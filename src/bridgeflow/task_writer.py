from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from .config import PatrolConfig
from .file_protocol import (
    build_task_filename,
    build_task_markdown,
    next_task_sequence,
    summarize_title,
)


@dataclass
class WrittenTask:
    path: Path
    filename: str
    thread_key: str


def new_thread_key(sender: str, recipient: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{sender}-to-{recipient}"


def _write_message_file(
    *,
    target_dir: Path,
    sender: str,
    recipient: str,
    text: str,
    priority: str,
    task_type: str,
    source: str,
    attachments: list[str] | None = None,
    thread_key: str | None = None,
    client_message_id: str = "",
) -> WrittenTask:
    target_dir.mkdir(parents=True, exist_ok=True)
    seq = next_task_sequence(target_dir)
    filename = build_task_filename(sender, recipient, seq)
    task_path = target_dir / filename
    actual_thread_key = thread_key or new_thread_key(sender, recipient)
    md = build_task_markdown(
        sender=sender,
        recipient=recipient,
        title=summarize_title(text),
        body=text,
        task_type=task_type,
        priority=priority,
        source=source,
        thread_key=actual_thread_key,
        attachments=attachments or [],
        client_message_id=client_message_id,
    )
    task_path.write_text(md, encoding="utf-8")
    return WrittenTask(path=task_path, filename=filename, thread_key=actual_thread_key)


def write_admin_task(
    config: PatrolConfig,
    text: str,
    *,
    recipient: str | None = None,
    priority: str | None = None,
    attachments: list[str] | None = None,
    thread_key: str | None = None,
    client_message_id: str = "",
) -> WrittenTask:
    actual_recipient = (recipient or config.admin_target).strip()
    return _write_message_file(
        target_dir=config.tasks_dir,
        sender=config.admin_sender,
        recipient=actual_recipient,
        task_type="ADMIN请求",
        priority=priority or config.default_priority,
        source="ADMIN01-mobile",
        text=text,
        attachments=attachments or [],
        thread_key=thread_key,
        client_message_id=client_message_id,
    )


def write_role_reply(
    config: PatrolConfig,
    text: str,
    *,
    sender: str,
    recipient: str = "ADMIN01",
    priority: str | None = None,
    attachments: list[str] | None = None,
    thread_key: str | None = None,
    client_message_id: str = "",
) -> WrittenTask:
    return _write_message_file(
        target_dir=config.reports_dir,
        sender=sender,
        recipient=recipient,
        task_type="团队回执",
        priority=priority or config.default_priority,
        source=f"{sender}-bridgeflow",
        text=text,
        attachments=attachments or [],
        thread_key=thread_key,
        client_message_id=client_message_id,
    )
