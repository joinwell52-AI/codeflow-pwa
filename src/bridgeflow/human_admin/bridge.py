from __future__ import annotations

from bridgeflow.config import PatrolConfig
from bridgeflow.task_writer import write_admin_task, WrittenTask


def admin_text_to_task(config: PatrolConfig, text: str, priority: str = "") -> WrittenTask:
    return write_admin_task(config, text, priority=priority or config.default_priority)
