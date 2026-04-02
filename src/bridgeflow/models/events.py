from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RelayEvent:
    room_key: str
    sender: str
    client_type: str
    event_type: str
    payload: dict
    ts: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["ts"] = self.ts or datetime.now().isoformat(timespec="seconds")
        return data
