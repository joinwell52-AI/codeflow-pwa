# CodeFlow — Commands Flow, Intelligence Follows

> The tool that turns [the Cursor AI team methodology](https://joinwell52-ai.github.io/joinwell52/) into a real product.
> Just download, run, and command your AI team from your phone.

---

## What is CodeFlow?

CodeFlow is a **remote control for your AI coding team**. It connects your phone to your PC running Cursor IDE, so you can:

- Send tasks to AI agents from your phone
- Watch them work in real-time
- Get reports back when they're done

No servers to set up. No accounts to create. Just two things:

| You need | What it does |
|----------|-------------|
| **CodeFlow Desktop** (EXE) | Runs on your PC, bridges your phone to Cursor IDE |
| **CodeFlow PWA** (web app) | Opens on your phone, sends tasks and views status |

---

## Get Started in 3 Minutes

### Step 1: Download Desktop EXE

- **China (fast)**: https://gitee.com/joinwell52/cursor-ai/releases
- **GitHub**: https://github.com/joinwell52-AI/codeflow-pwa/releases

Double-click `CodeFlow-Desktop.exe` (~35MB). On first launch, pick your project folder.

### Step 2: Open PWA on Phone

Open this link in your phone browser:

**https://joinwell52-ai.github.io/codeflow-pwa/**

Tap "Add to Home Screen" to install it as an app.

### Step 3: Scan to Bind

1. The Desktop shows a QR code on its panel
2. In PWA, tap **My** → **Scan to Bind PC**
3. Scan the QR code — done! Green light means connected

Now you can send tasks from your phone and watch your AI team work.

---

## How It Works

```
Phone (PWA)  ──→  Relay (WebSocket)  ──→  PC Desktop  ──→  Cursor IDE
   send task        forward event          write file       AI agents work
   view status  ←──  push updates     ←──  read reports  ←──  write reports
```

Every task becomes a markdown file: `TASK-20260413-001-ADMIN01-to-PM01.md`

The filename tells the system who sent it, who should receive it, and when. No database, no message queue — just files.

---

## What You Can Do from Your Phone

| Feature | Description |
|---------|------------|
| **Send tasks** | Write a task, pick a role (PM/DEV/QA/OPS), send |
| **View task list** | Categories: Tasks / Reports / Issues / Archive |
| **Read task details** | Full markdown source, flow path, status |
| **Monitor patrol** | Watch the Nudger patrol your Cursor agents |
| **Start/stop patrol** | Remote control the patrol from phone |
| **Team status** | See which roles are busy, idle, or waiting |
| **Language switch** | Full English and Chinese UI |

---

## Your AI Team

CodeFlow comes with 3 ready-made team templates. Pick one when you initialize a project:

| Template | Roles | Best for |
|----------|-------|----------|
| **dev-team** | PM + DEV + QA + OPS | Software projects |
| **media-team** | PUBLISHER + COLLECTOR + WRITER + EDITOR | Content creation |
| **mvp-team** | MARKETER + RESEARCHER + DESIGNER + BUILDER | Startup MVPs |

Each role is a Cursor Agent with its own rules and responsibilities. The Desktop's **Nudger** automatically switches between agents, delivers tasks, and nudges them when they get stuck.

---

## Self-Healing

The Desktop monitors Cursor IDE and fixes common problems automatically:

| Problem | What CodeFlow does |
|---------|--------------------|
| Cursor Connection Error | Auto Reload Window |
| Extension Host frozen | Auto Reload Window |
| Agent stuck or timed out | Reload + nudge message |
| Agent waiting for confirmation | Auto-send "continue" |
| WebSocket disconnected | Auto-reconnect |

You don't need to babysit the agents. Go grab that coffee.

---

## Desktop Panel Features

The Desktop runs a local web panel at `http://127.0.0.1:18765` with:

- Environment preflight check (project dir, team config, Cursor window, OCR)
- Agent mapping & one-click switching between roles
- Task pipeline with file browser (tasks / reports / issues / log)
- Patrol trace log with real-time updates
- Skills marketplace (download community skills for agents)
- QR code for phone binding
- Auto-update from GitHub + Gitee (dual mirror, picks the fastest)

---

## FAQ

**Q: Do I need to install Python?**
No. The EXE is self-contained. Just download and double-click.

**Q: Does it work without internet?**
The Desktop and Cursor work locally. The phone connection needs a relay server (included by default at `wss://ai.chedian.cc/codeflow/ws/`). You can also run your own relay.

**Q: Can I customize the team roles?**
Yes. Edit `docs/agents/codeflow.json` in your project folder. The PWA picks up changes automatically.

**Q: Is my data sent to any server?**
Only task status events (JSON text, no file content) pass through the relay. All actual files stay on your PC. The relay has a 256KB message limit.

---

## Links

- **Methodology**: [How to Build an Automated AI Development Team in Cursor](https://joinwell52-ai.github.io/joinwell52/)
- **Product site**: [github.com/joinwell52-AI/codeflow-pwa](https://github.com/joinwell52-AI/codeflow-pwa)
- **PWA**: [joinwell52-ai.github.io/codeflow-pwa](https://joinwell52-ai.github.io/codeflow-pwa/)
- **Download (China)**: [gitee.com/joinwell52/cursor-ai/releases](https://gitee.com/joinwell52/cursor-ai/releases)
- **Download (GitHub)**: [github.com/joinwell52-AI/codeflow-pwa/releases](https://github.com/joinwell52-AI/codeflow-pwa/releases)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

MIT License. © 2026 joinwell52-AI
