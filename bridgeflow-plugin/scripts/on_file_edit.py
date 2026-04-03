"""
Hook script: triggered by afterFileEdit on docs/agents/**/*.md

Reads the edited file info from stdin and could push notifications
to the relay server (Phase 2).

For now, just logs the event.
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        data = {}

    filepath = data.get("path", "unknown")
    timestamp = datetime.now().isoformat()

    log_dir = Path(
        __file__
    ).resolve().parent.parent.parent / "docs" / "agents" / ".bridgeflow"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "hook_events.log"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] file_edit: {filepath}\n")


if __name__ == "__main__":
    main()
