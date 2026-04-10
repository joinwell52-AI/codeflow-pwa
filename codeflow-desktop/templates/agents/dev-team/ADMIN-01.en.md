type: role
id: ADMIN-01
role: Human Administrator / Mobile Entry Point
project: CodeFlow
version: 0.1
updated: 2026-04-02
---

# ADMIN-01 Human Administrator

**Role:** Human Administrator, ID `ADMIN-01`
**Project:** `CodeFlow` (Chinese product name: 码流)

`ADMIN-01` is not an AI, nor a remote controller — it is the human member entry point in the project team.

This role participates in team collaboration through the `agent_bridge` protocol.

## Core Responsibilities

1. Send requirements to `PM-01` via phone or web
2. Follow up on task progress
3. Receive reports from `PM-01` or the team
4. Open OSS / Markdown links to view detailed results

## Core Rules

### 1. One Message = One Task File

Every text sent by `ADMIN-01` must be saved as:

```text
TASK-YYYYMMDD-sequence-ADMIN01-to-PM01.md
```

Messages must not only exist in the chat window.

### 2. No Direct Cross-Role Dispatching

In Phase 1, `ADMIN-01` sends text only to `PM-01` by default.

That means:

- Allowed: `ADMIN01 -> PM01`
- Not supported by default: `ADMIN01 -> DEV01`
- Not supported by default: `ADMIN01 -> OPS01`
- Not supported by default: `ADMIN01 -> QA01`

### 3. Replies Must Also Be Filed

Text from `PM-01` or other roles replying to `ADMIN-01` must also be saved as:

```text
TASK-YYYYMMDD-sequence-PM01-to-ADMIN01.md
```

Or:

```text
TASK-YYYYMMDD-sequence-DEV01-to-ADMIN01.md
```

### 4. Phone Does Not Perform GUI Operations

`ADMIN-01`'s responsibility is "text collaboration", not "controlling Cursor windows."

Therefore:

- Does not click tabs
- Does not perform OCR recognition
- Does not send keyboard input to desktop windows
- Does not directly participate in PC patrol actions

## Standard Workflow

### Sending Tasks

1. `ADMIN-01` enters text on the phone
2. Text reaches the desktop bridge via relay
3. Desktop bridge writes `TASK-*-ADMIN01-to-PM01.md`
4. `PM-01` receives and processes

### Viewing Replies

1. `PM-01` writes `TASK-*-PM01-to-ADMIN01.md`
2. Desktop bridge detects the file
3. Sends summary to phone via relay
4. `ADMIN-01` opens details or links on phone

## Requirements for PM-01

When `PM-01` processes tasks from `ADMIN-01`, it must:

1. Clearly reply whether the task is accepted
2. If decomposition is needed, continue writing `PM01-to-DEV01 / OPS01 / QA01`
3. Promptly send `PM01-to-ADMIN01` when interim results are available
4. Never keep results circulating internally without reporting back to `ADMIN-01`

## Applicable Scenarios

- Join collaboration via phone when away from the computer
- Quickly dispatch requirements to PM
- Check project progress at any time
- Receive delivery links and interim reports

## Phase 1 Limitations

- No full conversation thread UI yet
- No multi-admin concurrent conflict handling yet
- No phone-side viewing of all internal team details yet
- No remote desktop control yet
