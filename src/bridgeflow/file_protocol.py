from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


TASK_RE = re.compile(
    r"^TASK-(?P<date>\d{8})-(?P<seq>\d{3})-(?P<sender>[A-Z0-9]+)-to-(?P<recipient>[A-Z0-9]+)\.md$"
)
FIELD_PATTERNS = {
    "sender": re.compile(r"-\s*发送方：`([^`]+)`"),
    "recipient": re.compile(r"-\s*接收方：`([^`]+)`"),
    "task_type": re.compile(r"-\s*任务类型：`([^`]+)`"),
    "priority": re.compile(r"-\s*优先级：`([^`]+)`"),
    "source": re.compile(r"-\s*来源：`([^`]+)`"),
    "thread_key": re.compile(r"-\s*线程：`([^`]+)`"),
    "created_at": re.compile(r"-\s*时间：`([^`]+)`"),
}


def parse_task_filename(filename: str) -> dict | None:
    match = TASK_RE.match(filename)
    if not match:
        return None
    return match.groupdict()


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    metadata: dict[str, str] = {}
    closing_index = None
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            closing_index = idx
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    if closing_index is None:
        return {}, text

    body = "\n".join(lines[closing_index + 1 :]).lstrip()
    return metadata, body


def parse_task_markdown(text: str, *, filename: str = "") -> dict[str, str]:
    metadata, body = parse_front_matter(text)
    parsed = dict(metadata)

    if filename:
        name_meta = parse_task_filename(filename)
        if name_meta:
            parsed.setdefault("date", name_meta["date"])
            parsed.setdefault("seq", name_meta["seq"])
            parsed.setdefault("sender", name_meta["sender"])
            parsed.setdefault("recipient", name_meta["recipient"])

    title = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            break
    if title:
        parsed.setdefault("title", title)

    for key, pattern in FIELD_PATTERNS.items():
        if key in parsed and parsed[key]:
            continue
        match = pattern.search(body)
        if match:
            parsed[key] = match.group(1).strip()

    body_text = ""
    marker = "## 正文"
    if marker in body:
        tail = body.split(marker, 1)[1]
        body_lines = [line.rstrip() for line in tail.splitlines()]
        filtered = [line for line in body_lines if line.strip()]
        body_text = "\n".join(filtered)
    parsed["body"] = body_text.strip()

    return parsed


def next_task_sequence(tasks_dir: Path, date_str: str | None = None) -> int:
    current_date = date_str or datetime.now().strftime("%Y%m%d")
    max_seq = 0
    if tasks_dir.exists():
        for file in tasks_dir.glob(f"TASK-{current_date}-*.md"):
            parsed = parse_task_filename(file.name)
            if not parsed:
                continue
            max_seq = max(max_seq, int(parsed["seq"]))
    return max_seq + 1


def build_task_filename(sender: str, recipient: str, seq: int, date_str: str | None = None) -> str:
    current_date = date_str or datetime.now().strftime("%Y%m%d")
    return f"TASK-{current_date}-{seq:03d}-{sender}-to-{recipient}.md"


def build_task_markdown(
    *,
    sender: str,
    recipient: str,
    title: str,
    body: str,
    task_type: str,
    priority: str,
    source: str,
    thread_key: str,
    attachments: list[str] | None = None,
    client_message_id: str = "",
) -> str:
    attachments = attachments or []
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "---",
        "protocol: agent_bridge",
        "version: 1",
        "kind: task",
        f"sender: {sender}",
        f"recipient: {recipient}",
        f"priority: {priority}",
        f"source: {source}",
        f"thread_key: {thread_key}",
        f"created_at: {created_at}",
        f"attachments_count: {len(attachments)}",
        f"client_message_id: {client_message_id}",
        "---",
        "",
        f"# {title}",
        "",
        f"- 任务类型：`{task_type}`",
        f"- 发送方：`{sender}`",
        f"- 接收方：`{recipient}`",
        f"- 优先级：`{priority}`",
        f"- 来源：`{source}`",
        f"- 线程：`{thread_key}`",
        f"- 时间：`{created_at}`",
        "",
        "## 正文",
        "",
        body.strip(),
    ]
    if attachments:
        lines.extend(["", "## 附件", ""])
        lines.extend(f"- {item}" for item in attachments)
    lines.append("")
    return "\n".join(lines)


def summarize_title(text: str, limit: int = 32) -> str:
    clean = " ".join(text.strip().split())
    if len(clean) <= limit:
        return clean or "未命名任务"
    return clean[: limit - 3] + "..."
