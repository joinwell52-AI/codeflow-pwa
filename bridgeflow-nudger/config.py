"""
BridgeFlow Nudger 配置模块
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NudgerConfig:
    project_dir: Path = field(default_factory=lambda: Path.cwd())
    relay_url: str = "wss://ai.chedian.cc/bridgeflow/ws/"
    room_key: str = ""
    device_id: str = "bridgeflow-nudger"
    poll_interval: float = 5.0
    nudge_cooldown: float = 15.0
    lang: str = "zh"

    hotkeys: dict[str, tuple] = field(default_factory=lambda: {
        "PM":  ("ctrl", "alt", "1"),
        "DEV": ("ctrl", "alt", "2"),
        "QA":  ("ctrl", "alt", "3"),
        "OPS": ("ctrl", "alt", "4"),
    })

    input_offset: tuple[float, float] = (0.80, 55)

    @property
    def agents_dir(self) -> Path:
        return self.project_dir / "docs" / "agents"

    @property
    def tasks_dir(self) -> Path:
        return self.agents_dir / "tasks"

    @property
    def reports_dir(self) -> Path:
        return self.agents_dir / "reports"

    @property
    def issues_dir(self) -> Path:
        return self.agents_dir / "issues"

    @property
    def log_dir(self) -> Path:
        return self.agents_dir / "log"
