from __future__ import annotations

from pathlib import Path

from bridgeflow.file_protocol import parse_task_filename


def scan_markdown_files(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    return {item.name for item in directory.glob("*.md")}


def parse_recipient(filename: str) -> str | None:
    parsed = parse_task_filename(filename)
    return parsed["recipient"] if parsed else None


def parse_sender(filename: str) -> str | None:
    parsed = parse_task_filename(filename)
    return parsed["sender"] if parsed else None


def decide_notify_targets(
    new_tasks: set[str],
    new_reports: set[str],
    role_to_chat: dict[str, str],
) -> set[str]:
    targets: set[str] = set()

    for filename in new_tasks:
        recipient = parse_recipient(filename)
        if recipient and recipient in role_to_chat:
            targets.add(role_to_chat[recipient])

    for filename in new_reports:
        recipient = parse_recipient(filename)
        if recipient and recipient in role_to_chat:
            targets.add(role_to_chat[recipient])

        sender = parse_sender(filename)
        if sender == "DEV01":
            targets.update(filter(None, [role_to_chat.get("QA01"), role_to_chat.get("PM01")]))
        elif sender == "QA01":
            targets.update(filter(None, [role_to_chat.get("PM01")]))

    return targets
