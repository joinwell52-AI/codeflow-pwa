# BridgeFlow User Manual

**Version:** v1.9.0 | **Updated:** 2026-04-03

---

## 1. System Requirements

| Item | Requirement | Notes |
|------|-------------|-------|
| OS | Windows 10 or later | macOS / Linux not yet supported |
| Cursor | v3.0 or later (installed) | Download: https://cursor.com |
| Display | 1920×1080 or higher | Need space for multiple Agent Tabs |
| Network | Internet access required | WebSocket connection for relay |

> **Python is NOT required** — just run the packaged EXE.

---

## 2. Prerequisites

### 2.1 Install Cursor

If Cursor is not installed yet:

1. Go to https://cursor.com
2. Download the Windows installer
3. Install and open Cursor, sign in

### 2.2 Prepare a Project Folder

Choose a local folder as your team workspace, e.g.:

```
D:\my-ai-team\
```

This folder will contain:
- `docs/agents/` — tasks, reports, issues
- `.cursor/rules/` — Agent collaboration rules
- `.cursor/skills/` — Agent skill files

> **Any drive letter, any path** — just remember where it is.

### 2.3 Get BridgeFlow Desktop

Get `BridgeFlow-Desktop.exe` (~50MB), place it anywhere.

---

## 3. First-Time Setup (~3 Minutes)

### Step 1: Run the EXE

Double-click `BridgeFlow-Desktop.exe`. The browser opens the control panel:

```
http://127.0.0.1:18765
```

### Step 2: Select Project Folder

The panel shows a setup wizard. Click **Browse** to select your project folder.

### Step 3: Choose a Team Template

Pick one of 3 preset teams:

| Template | Roles | Best For |
|----------|-------|----------|
| Software Dev Team | PM + DEV + QA + OPS | Software projects |
| Media Team | PUBLISHER + COLLECTOR + WRITER + EDITOR | Content creation |
| Startup MVP Team | MARKETER + RESEARCHER + DESIGNER + BUILDER | Product validation |

Click **Save**. The system auto-generates:

```
Your project folder/
├── .cursor/
│   ├── rules/bridgeflow-core.mdc
│   ├── rules/bridgeflow-patrol.mdc
│   └── skills/file-protocol/SKILL.md
├── docs/agents/
│   ├── bridgeflow.json
│   ├── PM.md / PM.en.md              ← Role docs (bilingual)
│   ├── DEV.md / DEV.en.md
│   ├── QA.md / QA.en.md
│   ├── OPS.md / OPS.en.md
│   ├── tasks/ reports/ issues/ log/
```

### Step 4: Environment Preflight

The panel runs 6 checks automatically:

| Check | What it does | If it fails |
|-------|-------------|-------------|
| Project Directory | Folder exists | Re-select folder |
| Directory Structure | tasks / reports / issues / log exist | Click "Fix" |
| Team Config | bridgeflow.json generated | Re-select team |
| Role Files | rules + skills + role docs ready | Click "Copy" |
| Cursor Window | Cursor is running | Open Cursor first |
| Hotkeys | Ctrl+Alt+1~4 configured | Auto-written |

**All 6 green = ready to go.**

### Step 5: Open Project Folder in Cursor

1. Open Cursor
2. File → Open Folder → select your project folder
3. Create 4 Agent Tabs in the Chat panel

**For Software Dev Team, names must match exactly:**

| # | Tab Name | Role |
|---|----------|------|
| 1 | `1-PM` | Project Manager |
| 2 | `2-DEV` | Developer |
| 3 | `3-QA` | QA Engineer |
| 4 | `4-OPS` | DevOps Engineer |

> How to: Click **"+"** in Chat panel to create, then click the name to rename.

### Step 6: Start Patrol

Go back to the control panel (`http://127.0.0.1:18765`), click **Start**.

Once started:
- Button turns cyan (lit state)
- Nudger monitors `docs/agents/tasks/` and `reports/`
- When new task files appear, it auto-switches to the right Agent Tab

**First-time setup complete!**

---

## 4. Phone Binding (Optional)

### 4.1 Open PWA

On your phone browser, go to:

```
https://joinwell52-ai.github.io/bridgeflow-pwa/
```

Add to home screen:
- **iOS Safari:** Share button → "Add to Home Screen"
- **Android Chrome:** Top-right menu → "Add to Home Screen"

### 4.2 Scan to Bind

1. PC control panel → Phone Connection area → QR code displayed
2. Phone PWA → tap **"My"** → tap **"Scan to Bind PC"**
3. Point at QR code
4. Binding complete — phone can now control the PC

### 4.3 What Phone Can Do

- Remote start / stop patrol
- View task list and reports
- Send tasks to specific roles
- Remote desktop actions (focus Cursor / check status / start work)

---

## 5. Daily Usage

Each time, just:

1. **Double-click `BridgeFlow-Desktop.exe`**
2. **Open Cursor** (make sure 4 Agent Tabs are there)
3. **Click "Start"**

> If you've already set up the project folder and team, no re-configuration needed.

---

## 6. Control Panel Overview

| Area | Features |
|------|----------|
| Patrol Control | Start / Stop / Preflight / Reset |
| Task Overview | Pending tasks / Reports / Issues / Nudge count |
| Task Pipeline | Real-time status (running / possibly stuck / timeout / done) |
| File Browser | Tasks / Reports / Issues / Archives — click to preview Markdown |
| Phone Connection | QR code + bound devices list + unbind |
| Live Logs | INFO / WARNING / ERROR color-coded |
| Settings | Relay URL / poll interval / language switch (zh/en) |

---

## 7. Troubleshooting

### Cursor Window Not Detected

- Make sure Cursor is open and visible (not minimized to tray)
- Window title must contain "Cursor"

### Hotkeys Not Working

- Check that `keybindings.json` has `Ctrl+Alt+1~4` entries
- Preflight auto-writes them; manual check: `%APPDATA%\Cursor\User\keybindings.json`

### Phone Scan Not Working

1. Confirm camera permission is granted
2. Confirm PWA connection indicator is green (connect first, then scan)
3. Refresh the panel page to regenerate QR code

### Panel Won't Open

- Make sure the EXE is still running (console window not closed)
- Check browser URL is `http://127.0.0.1:18765`
- If port is occupied, close whatever is using port 18765

### Switch Project / Change Team

Click the **Reset** button at bottom-right of the panel (requires confirmation), then re-run the wizard.

---

## 8. File Reference

| File | Description |
|------|-------------|
| `BridgeFlow-Desktop.exe` | Main program, double-click to run, ~50MB |
| `docs/agents/bridgeflow.json` | Team config (roles, room key, relay URL) |
| `docs/agents/tasks/*.md` | Task files |
| `docs/agents/reports/*.md` | Completion reports |
| `docs/agents/issues/*.md` | Issue records |
| `docs/agents/log/*.md` | Historical archives |
| `.cursor/rules/*.mdc` | Cursor Agent rule files |
| `.cursor/skills/*/SKILL.md` | Cursor Agent skill files |
