"""One-shot rename: `protocol: agent_bridge` -> `protocol: fcop` in role docs.

Runs idempotently. Intentionally SKIPS:
  - docs/agents/tasks/**  (historical task files, including 20260420 evidence)
  - docs/agents/reports/**
  - docs/agents/log/**
  - README files (handled separately with custom surrounding prose)

Only touches role-definition files whose embedded task templates need to reflect
the new canonical `protocol: fcop` value.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    "docs/agents/QA-01.md",
    "docs/agents/QA-01.en.md",
    "codeflow-desktop/templates/agents/dev-team/QA-01.md",
    "codeflow-desktop/templates/agents/dev-team/QA-01.en.md",
    "codeflow-desktop/templates/agents/qa-team/LEAD-QA.md",
    "codeflow-desktop/templates/agents/qa-team/LEAD-QA.en.md",
    "codeflow-desktop/templates/agents/qa-team/PERF-TESTER.md",
    "codeflow-desktop/templates/agents/qa-team/PERF-TESTER.en.md",
    "codeflow-desktop/templates/agents/qa-team/AUTO-TESTER.md",
    "codeflow-desktop/templates/agents/qa-team/AUTO-TESTER.en.md",
    "codeflow-desktop/templates/agents/qa-team/TESTER.md",
    "codeflow-desktop/templates/agents/qa-team/TESTER.en.md",
]

PATTERN = re.compile(r"protocol:\s*agent_bridge")


def main() -> int:
    changed = 0
    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            print(f"[SKIP missing] {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        new = PATTERN.sub("protocol: fcop", text)
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            print(f"[OK]   {rel}")
            changed += 1
        else:
            print(f"[noop] {rel}")
    print(f"\nChanged {changed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
