# CodeFlow Agent File Structure

**CodeFlow**'s first phase is not about building a "mobile chat app" — it's about building the file system backbone for "humans entering the team protocol."

Therefore, `docs/agents/` is the core collaboration directory of this project.

---

## Core Principle (the north star)

> **AI roles must not communicate only in their heads — every exchange must be written to a file.**

This is the overarching clause for the whole agent protocol. Every rule below (naming
conventions, file protocol, YAML metadata header, "one message = one file", etc.) is just
**this principle specialized for a specific context**.

This principle was not designed top-down by a human. It emerged from a human-AI
co-evolution: on 2026-04-20, a Cursor agent, while executing a completely unrelated video
generation task, spontaneously sublimated seven scattered technical rules in this project's
`.cursor/rules/` into a single sentence — and we then absorbed its synthesis back into the
protocol as the overarching clause. Full event log and evidence archive:
[FCoP repo · fcop-natural-protocol.en.md](https://github.com/joinwell52-AI/FCoP/blob/main/essays/fcop-natural-protocol.en.md).

---

## Directory Structure

```text
docs/agents/
├── README.md                  # This file: agent file structure overview
├── ADMIN-01.md                # Human role ADMIN responsibilities
├── PM-01.md                   # PM role definition
├── DEV-01.md                  # DEV role definition
├── OPS-01.md                  # OPS role definition
├── QA-01.md                   # QA role definition
├── tasks/                     # Task files
├── reports/                   # Reply/report files
├── log/                       # Notification and archive summaries
└── issues/                    # Issue records
```

---

## Role Naming Convention

The same role has different representations across different contexts. **All four team templates follow these unified rules.**

### Naming Rules

| Context | Format | Example | Description |
|---------|--------|---------|-------------|
| **File name sender/recipient** | `ROLE_NAME` (no hyphen, no number) | `PM`, `QA`, `COLLECTOR` | Used in `TASK-*-PM-to-QA.md` |
| **Cursor Tab display name** | `number-ROLE_NAME` | `01-PM`, `03-QA`, `01-COLLECTOR` | Set when pinning in Cursor Agents panel |
| **Role definition doc** | `ROLE_NAME-number.md` | `PM-01.md`, `COLLECTOR.md` | In `docs/agents/` or `templates/agents/` |
| **Patrol engine internal** | Pure role name (auto-normalized) | `PM`, `QA`, `COLLECTOR` | Code uses `_role_key_for_task()` |

### dev-team Roles (Software Development)

| # | Cursor Tab | File Protocol | Definition Doc | Responsibility |
|---|-----------|--------------|----------------|----------------|
| 01 | `01-PM` | `PM` | `PM-01.md` | Project Manager / Task Dispatcher |
| 02 | `02-DEV` | `DEV` | `DEV-01.md` | Full-Stack Developer |
| 03 | `03-QA` | `QA` | `QA-01.md` | QA Engineer |
| 04 | `04-OPS` | `OPS` | `OPS-01.md` | Operations & Deployment |
| — | — | `ADMIN` | `ADMIN-01.md` | Human Admin (not in Cursor) |

### media-team Roles (Content & Media)

| # | Cursor Tab | File Protocol | Definition Doc | Responsibility |
|---|-----------|--------------|----------------|----------------|
| 01 | `01-COLLECTOR` | `COLLECTOR` | `COLLECTOR.md` | Content Collection |
| 02 | `02-WRITER` | `WRITER` | `WRITER.md` | Content Writing |
| 03 | `03-EDITOR` | `EDITOR` | `EDITOR.md` | Editing & Review |
| 04 | `04-PUBLISHER` | `PUBLISHER` | `PUBLISHER.md` | Publishing & Operations |

### mvp-team Roles (Rapid MVP Validation)

| # | Cursor Tab | File Protocol | Definition Doc | Responsibility |
|---|-----------|--------------|----------------|----------------|
| 01 | `01-BUILDER` | `BUILDER` | `BUILDER.md` | Product Building |
| 02 | `02-DESIGNER` | `DESIGNER` | `DESIGNER.md` | UI/UX Design |
| 03 | `03-MARKETER` | `MARKETER` | `MARKETER.md` | Marketing & Promotion |
| 04 | `04-RESEARCHER` | `RESEARCHER` | `RESEARCHER.md` | User Research |

### qa-team Roles (Dedicated QA)

| # | Cursor Tab | File Protocol | Definition Doc | Responsibility |
|---|-----------|--------------|----------------|----------------|
| 01 | `01-LEAD-QA` | `LEAD-QA` | `LEAD-QA.md` | QA Lead |
| 02 | `02-TESTER` | `TESTER` | `TESTER.md` | Functional Testing |
| 03 | `03-AUTO-TESTER` | `AUTO-TESTER` | `AUTO-TESTER.md` | Automation Testing |
| 04 | `04-PERF-TESTER` | `PERF-TESTER` | `PERF-TESTER.md` | Performance Testing |

### Normalization Rules

The patrol engine uses `_role_key_for_task()` to extract the **pure role name** for matching. All formats are correctly recognized:

```
PM           → PM            strip trailing digits
01-PM          → PM            strip leading number + hyphen
PM-01          → PM            strip hyphen + trailing digits
03-QA          → QA
QA           → QA
COLLECTOR      → COLLECTOR     already pure role name
01-COLLECTOR   → COLLECTOR
AUTO-TESTER    → AUTO-TESTER   preserves inner hyphen
03-AUTO-TESTER → AUTO-TESTER
```

### Historical Compatibility

Legacy file protocol used `PM`, `QA` as sender/recipient. The patrol engine normalizes them correctly.
New task files **should use pure role names** (`PM`, `QA`), but legacy format is also supported.

---

## File Protocol

### Task Files

Naming format:

```text
TASK-YYYYMMDD-sequence-sender-to-recipient.md
```

Examples:

- `TASK-20260401-001-ADMIN-to-PM.md`
- `TASK-20260401-002-PM-to-ADMIN.md`
- `TASK-20260401-003-PM-to-DEV.md`
- `TASK-20260401-004-PM-to-COLLECTOR.md` (media-team scenario)

Legacy format also supported: `TASK-20260401-001-ADMIN-to-PM.md`

### Rules

- One message = one file
- Text sent from phone to PM must become `TASK-*-ADMIN-to-PM.md`
- PM's reply to ADMIN must become `TASK-*-PM-to-ADMIN.md`
- DEV/OPS/QA replying directly to humans must use `XX-to-ADMIN`
- No secondary "chat-only, no-file" protocol is allowed

### Standard Write Method

To avoid field omissions from manual Markdown writing, use the CLI to generate standard files:

```powershell
CodeFlow write-admin-task --text "Please have PM arrange the next steps"
CodeFlow write-reply --sender PM --text "Accepted, starting task decomposition" --thread-key "demo-thread-001"
```

Where:

- `write-admin-task` writes to `tasks/` by default
- `write-reply` writes to `reports/` by default
- Both automatically prepend the FCoP metadata header

### Protocol Metadata

Starting from the current version, `TASK` Markdown files carry a lightweight metadata header:

```text
---
protocol: fcop
version: 1
kind: task
sender: ADMIN
recipient: PM
priority: P1
source: ADMIN-mobile
thread_key: 20260401-123000-ADMIN-to-PM
created_at: 2026-04-01 12:30:00
attachments_count: 0
---
```

This metadata serves to:

- Enable the desktop bridge to reliably parse `sender`, `recipient`, `thread_key`
- Enable phone-side to aggregate threads by `thread_key`
- Support future role adapter integrations without relying on plain-text regex guessing

#### About `protocol:` and `version:`

- **`protocol: fcop`** — portable identifier that tells any reader (agent, tool,
  human) "this Markdown file is an FCoP coordination document, not a stray note."
  The canonical value is lowercase `fcop`, following the machine-identifier
  convention used by `http` / `grpc` / etc. The brand name **FCoP** is reserved
  for prose, titles and external writing. Historical aliases (`agent_bridge` —
  the pre-2026-04-20 internal codename — as well as `agent-bridge` /
  `file-coordination`) are normalised to `fcop` by `_parse_frontmatter`, so
  existing files do **not** need to be migrated.
- **`version: 1`** — protocol version. Integer, no quotes, no decimal point.
  Only bumped when the protocol itself introduces a breaking change (field
  semantics flip, required fields added/removed); do **not** use this field to
  track per-document revisions. Existing files written as `1.0` / `"1.0"` are
  also normalised to `"1"`, no forced upgrade.

## Team Templates

`codeflow-desktop/templates/agents/` contains multiple pre-built team templates:

| Team Directory | Use Case | Core Roles |
|----------------|----------|------------|
| `dev-team/` | Software Development | PM, DEV, OPS, QA, ADMIN |
| `media-team/` | Content & Media | COLLECTOR, WRITER, EDITOR, PUBLISHER |
| `mvp-team/` | Rapid MVP Validation | BUILDER, DESIGNER, MARKETER, RESEARCHER |
| `qa-team/` | Dedicated QA | LEAD-QA, TESTER, AUTO-TESTER, PERF-TESTER |

When initializing CodeFlow Desktop, users select a team template. The system automatically:
1. Copies role definition files to `docs/agents/`
2. Creates corresponding Agent Tabs in Cursor (named by number + role name)
3. The patrol engine auto-detects all roles and starts patrolling

---

## Phase 1 Role Positioning

### ADMIN

- Represents the real human user
- Used by default on the phone PWA
- Responsible for sending requirements, following up on progress, receiving replies

### PM

- Receives tasks from `ADMIN`
- Decomposes requirements for DEV / OPS / QA
- Reports results back to `ADMIN`

### DEV / OPS / QA

- Internal execution roles within the team
- Phase 1 does not require phone-side direct communication with these roles

## Why This Design

If the phone only "views messages" without writing files, two parallel systems emerge:

1. Internal team: `TASK-*.md`
2. Phone side: Independent chat records

This would break project archiving, accountability, and thread tracking.

Therefore, CodeFlow Phase 1 insists:

**All text communication must go through the file protocol.**

## Protocol Naming

This project internally names this file collaboration approach `agent_bridge`:

- Application-level name: **CodeFlow**
- Underlying collaboration protocol: `agent_bridge`
- Protocol core: `TASK-YYYYMMDD-sequence-sender-to-recipient.md`
