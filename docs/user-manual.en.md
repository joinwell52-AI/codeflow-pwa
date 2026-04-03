# BridgeFlow User Manual

**Version:** v0.2.1 | **Updated:** 2026-04-02

---

## First-Time Setup (About 5 Minutes)

### Prerequisite: Install Python

BridgeFlow requires Python 3.10+. If Python is already installed on your computer, skip this step.

**Installing Python on Windows:**

1. Go to https://www.python.org/downloads/
2. Download the latest version (3.10 or above)
3. Run the installer — **make sure to check "Add Python to PATH"**
4. Installation complete

> Not sure if Python is installed? Open Command Prompt (Win+R, type `cmd`), run `python --version`. If it shows a version number, you're good.

---

### Prerequisite: Create 4 Agents in Cursor

BridgeFlow requires the following 4 Agents in Cursor. **Names must match exactly:**

| # | Agent Name | Role |
|---|---|---|
| 1 | `1-PM` | Project Manager — receives tasks, dispatches work |
| 2 | `2-DEV` | Developer — handles coding and implementation |
| 3 | `3-QA` | QA Engineer — handles testing and verification |
| 4 | `4-OPS` | Operations Engineer — handles deployment and releases |

**Steps:**

1. Open Cursor
2. Click the **"+"** button at the top right of the Chat panel to create a new Agent
3. Click the Agent name to rename it to `1-PM`
4. Repeat the above steps to create `2-DEV`, `3-QA`, and `4-OPS`

> **Note:** The numbers and letter casing in the names must match exactly.
> BridgeFlow checks for these at startup — any missing agent will cause an error and exit.

---

### Step 1: Download the Launcher Script

Download `bfstart.bat` (Windows) from:

```
https://github.com/joinwell52-ai/BridgeFlow/raw/main/scripts/bfstart.bat
```

**Place this file in the project directory where you want task files to be stored**, e.g. `C:\my-ai-team\` or `D:\my-ai-team\` — any drive letter works.

---

### Step 2: Double-Click to Run

Double-click `bfstart.bat`. The script will automatically:

```
✓ Check Python version
✓ Install BridgeFlow (first time takes ~10-30 seconds)
✓ Auto-initialize configuration (generates a unique room key)
✓ Start BridgeFlow
✓ Open the browser dashboard
```

After startup, the browser opens `http://localhost:18765`:

```
┌─────────────────────────────────────┐
│  BridgeFlow Dashboard               │
│                                     │
│  Environment: ✓ Python  ✓ Cursor    │
│  Relay:  ● Connected                │
│  Room:   bf-my-pc-a3f2c8d1          │
│                                     │
│       ┌──────────────┐              │
│       │  [ QR Code ] │  ← Scan here with your phone
│       └──────────────┘              │
└─────────────────────────────────────┘
```

---

### Step 3: Scan QR Code with Your Phone

1. Open the PWA on your phone browser:

   ```
   https://joinwell52-ai.github.io/bridgeflow-pwa/
   ```

2. Add to home screen (use it like a native app):
   - iOS Safari: Tap the share button at the bottom → "Add to Home Screen"
   - Android Chrome: Top-right menu → "Add to Home Screen"

3. Open the PWA, tap **"My"** at the top right corner

4. Tap **"📷 Scan to Bind PC"**, point at the QR code on the dashboard

5. Once scanned successfully, the connection indicator at the top turns green ✅

**Binding complete!** Your phone and PC now recognize each other, and the room key is automatically synced.

---

### First-Time Setup Complete ✅

Your directory now contains:

```
📁 Your chosen directory\ (any drive letter)
  ├── bfstart.bat            ← Use this every time to start
  └── bridgeflow_config.json
```

---

## Daily Usage (Just 1 Step Each Time)

**Double-click `bfstart.bat`** — that's it.

The script automatically:
- Checks Python and Cursor environment
- Checks for updates and upgrades to the latest version
- Starts BridgeFlow
- Opens the browser dashboard
- Connects to relay and waits for phone commands

---

## Sending Tasks

In the PWA send area at the bottom:

```
1. Select recipient role: PM / DEV / OPS / QA
2. Enter task content
3. Select priority: P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low)
4. Tap "Send"
```

After sending, the AI role on the PC will receive the task and start processing.

---

## Viewing Replies

- On the PWA home page task list, tap any task card to expand and see the full conversation
- The "Today's Replies" counter at the top updates when new replies arrive
- Your phone receives AI reply summaries via push notifications

---

## Troubleshooting

### Dashboard Connection Indicator is Red

PC cannot connect to the relay server. Check:
1. Is your network connection working?
2. Is your firewall blocking `wss://ai.chedian.cc`?
3. Close and double-click `bfstart.bat` again

### Phone Scan Not Working

1. Confirm you've granted camera permission to the browser
2. Confirm the PWA connection indicator at the top is green (connect to relay first, then scan)
3. Refresh the dashboard page and try scanning again

### PWA Page Not Updated

Clear your phone browser cache:
- Safari: Settings → Safari → Clear History and Website Data
- Chrome: Settings → Privacy → Clear Browsing Data

### New Version Available

When double-clicking `bfstart.bat`, if a new version is detected:

```
  🚀 New version v0.2.1 available (current v0.2.0)
  Upgrade and restart now? [y/N]
```

Type `y` and press Enter to auto-upgrade and restart. No other action needed.

---

## Appendix

### Where is My Room Key?

When starting with `bfstart.bat`, the command prompt window shows:

```
  Room Key  : bf-my-pc-a3f2c8d1
```

The browser dashboard (`http://localhost:18765`) also displays it.

The phone "My" page also shows the current room key.

### Using Multiple PCs

Place a copy of `bfstart.bat` on each PC, double-click to run. Each one auto-generates its own config and unique room key. Scan and bind each PC separately from your phone.

### Where Are Task Files Stored?

```
Your project directory/
  docs/agents/tasks/      ← Task files (TASK-*.md)
  docs/agents/reports/    ← Reply/report files
```

Every task is saved as a standard Markdown file that can be opened with any text editor.
