# CodeFlow Agent File Structure (码流)

**CodeFlow**'s first phase is not about building a "mobile chat app" — it's about building the file system backbone for "humans entering the team protocol."

Therefore, `docs/agents/` is the core collaboration directory of this project.

## Directory Structure

```text
docs/agents/
├── README.md                  # This file: agent file structure overview
├── ADMIN-01.md                # Human role ADMIN01 responsibilities
├── PM-01.md                   # PM01 role definition
├── DEV-01.md                  # DEV01 role definition
├── OPS-01.md                  # OPS01 role definition
├── QA-01.md                   # QA01 role definition
├── tasks/                     # Task files
├── reports/                   # Reply/report files
├── log/                       # Notification and archive summaries
└── issues/                    # Issue records
```

## File Protocol

### Task Files

Naming format:

```text
TASK-YYYYMMDD-sequence-sender-to-recipient.md
```

Examples:

- `TASK-20260401-001-ADMIN01-to-PM01.md`
- `TASK-20260401-002-PM01-to-ADMIN01.md`
- `TASK-20260401-003-PM01-to-DEV01.md`

### Rules

- One message = one file
- Text sent from phone to PM must become `TASK-*-ADMIN01-to-PM01.md`
- PM's reply to ADMIN must become `TASK-*-PM01-to-ADMIN01.md`
- DEV/OPS/QA replying directly to humans must use `XX01-to-ADMIN01`
- No secondary "chat-only, no-file" protocol is allowed

### Standard Write Method

To avoid field omissions from manual Markdown writing, use the CLI to generate standard files:

```powershell
CodeFlow write-admin-task --text "Please have PM arrange the next steps"
CodeFlow write-reply --sender PM01 --text "Accepted, starting task decomposition" --thread-key "demo-thread-001"
```

Where:

- `write-admin-task` writes to `tasks/` by default
- `write-reply` writes to `reports/` by default
- Both automatically include the `agent_bridge` metadata header

### Protocol Metadata

Starting from the current version, `TASK` Markdown files carry a lightweight metadata header:

```text
---
protocol: agent_bridge
version: 1
kind: task
sender: ADMIN01
recipient: PM01
priority: P1
source: ADMIN01-mobile
thread_key: 20260401-123000-ADMIN01-to-PM01
created_at: 2026-04-01 12:30:00
attachments_count: 0
---
```

This metadata serves to:

- Enable the desktop bridge to reliably parse `sender`, `recipient`, `thread_key`
- Enable phone-side to aggregate threads by `thread_key`
- Support future role adapter integrations without relying on plain-text regex guessing

## Phase 1 Role Positioning

### ADMIN01

- Represents the real human user
- Used by default on the phone PWA
- Responsible for sending requirements, following up on progress, receiving replies

### PM01

- Receives tasks from `ADMIN01`
- Decomposes requirements for DEV / OPS / QA
- Reports results back to `ADMIN01`

### DEV01 / OPS01 / QA01

- Internal execution roles within the team
- Phase 1 does not require phone-side direct communication with these three roles

## Why This Design

If the phone only "views messages" without writing files, two parallel systems emerge:

1. Internal team: `TASK-*.md`
2. Phone side: Independent chat records

This would break project archiving, accountability, and thread tracking.

Therefore, CodeFlow Phase 1 insists:

**All text communication must go through the file protocol.**

## Protocol Naming

This project internally names this file collaboration approach `agent_bridge`:

- Application-level name: **CodeFlow** (Chinese: 码流)
- Underlying collaboration protocol: `agent_bridge`
- Protocol core: `TASK-YYYYMMDD-sequence-sender-to-recipient.md`
