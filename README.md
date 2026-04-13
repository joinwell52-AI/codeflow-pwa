# CodeFlow / 码流

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PWA](https://img.shields.io/badge/PWA-Live-green)](https://joinwell52-ai.github.io/codeflow-pwa/)
[![Desktop](https://img.shields.io/badge/Desktop-v2.9.44-orange)](https://github.com/joinwell52-AI/codeflow-pwa/releases)
[![PWA Version](https://img.shields.io/badge/PWA-v2.2.9-blue)](https://joinwell52-ai.github.io/codeflow-pwa/)

> **Commands Flow, Intelligence Follows.**
> 指令成流，智能随行。

**CodeFlow** is an AI-powered human-machine collaboration hub. Command your multi-agent team from a mobile phone; let the PC handle execution.

**码流（CodeFlow）** — AI 驱动的人机协作中枢。手机发指令，PC 写代码；每条消息都落成文件，文件名即通信协议。

<p align="center">
  <img src="docs/images/product-1.png" width="360" alt="CodeFlow Desktop Panel" />
  &nbsp;&nbsp;
  <img src="docs/images/product-2.png" width="360" alt="CodeFlow PWA Mobile" />
</p>

---

## How It Works / 工作原理

```mermaid
graph LR
    Phone["📱 PWA<br/>Mobile Command Center"]
    Relay["☁️ Relay<br/>WebSocket Forwarder"]
    Desktop["💻 CodeFlow Desktop<br/>PC Execution Engine"]
    Cursor["🤖 Cursor IDE<br/>AI Agents"]

    Phone -->|"send task / control"| Relay
    Relay -->|"forward JSON events"| Desktop
    Desktop -->|"write TASK-*.md"| Cursor
    Cursor -->|"reports / replies"| Desktop
    Desktop -->|"push dashboard"| Relay
    Relay -->|"display status"| Phone
```

| Layer | Role | Tech |
|-------|------|------|
| **Phone (PWA)** | Command center — send tasks, view status, scan to bind PC | HTML5 PWA, Service Worker |
| **Relay** | Lightweight text event forwarder | WebSocket (`wss://`) |
| **Desktop** | Execution engine — receive tasks, write files, patrol, bridge | Python, PyInstaller EXE |
| **Cursor IDE** | AI agents read/write TASK files, auto-dispatched by Nudger | Cursor + MCP Plugin |

---

## File-Driven Protocol / 文件驱动协议

> **Filename IS the protocol.** No second chat system.
> 文件名就是通信协议，不形成第二套聊天系统。

```
TASK-20260413-001-MARKETER-to-RESEARCHER.md
│    │         │   │          │
│    Date       │   Sender     Recipient
│              Seq#
TASK prefix
```

Every message — whether from human (ADMIN) or AI agent — is persisted as a markdown file with YAML front matter.

| Directory | Content |
|-----------|---------|
| `tasks/` | Task assignments |
| `reports/` | Completion reports |
| `issues/` | Bug / problem records |
| `log/` | Archive & notifications |

---

## Agent Naming & Team Templates / Agent 命名与团队模板

CodeFlow uses a **role-code naming convention**: uppercase English code + numeric suffix.

码流采用 **角色代码命名法**：大写英文代号 + 数字后缀。

### Naming Rules / 命名规则

| Rule | Example | Description |
|------|---------|-------------|
| Human operator | `ADMIN-01` | Always the human; never an AI |
| AI role code | `PM-01`, `DEV-01` | Uppercase, hyphen, 2-digit number |
| Team leader | First role in `codeflow.json` | Receives tasks from ADMIN |
| Task routing | `ADMIN01-to-PM01` | Embedded in filename |

### 4 Built-in Team Templates / 四套内置团队模板

Choose a template during project initialization. Each template generates bilingual role documents (Chinese + English).

```mermaid
graph TB
    subgraph devTeam ["dev-team / 软件开发团队"]
        PM01_d["PM-01<br/>项目经理"]
        DEV01_d["DEV-01<br/>全栈开发"]
        QA01_d["QA-01<br/>测试工程师"]
        OPS01_d["OPS-01<br/>运维部署"]
        PM01_d --> DEV01_d
        PM01_d --> QA01_d
        PM01_d --> OPS01_d
    end

    subgraph mediaTeam ["media-team / 自媒体团队"]
        PUB01["PUBLISHER-01<br/>发布主编"]
        COL01["COLLECTOR-01<br/>素材采集"]
        WRI01["WRITER-01<br/>内容写手"]
        EDI01["EDITOR-01<br/>编辑校对"]
        PUB01 --> COL01
        PUB01 --> WRI01
        PUB01 --> EDI01
    end

    subgraph mvpTeam ["mvp-team / 创业MVP团队"]
        MKT01["MARKETER-01<br/>营销策划"]
        RES01["RESEARCHER-01<br/>市场调研"]
        DES01["DESIGNER-01<br/>产品设计"]
        BLD01["BUILDER-01<br/>全栈开发"]
        MKT01 --> RES01
        MKT01 --> DES01
        MKT01 --> BLD01
    end

    subgraph qaTeam ["qa-team / 质量保障团队"]
        LQA01["LEAD-QA-01<br/>测试主管"]
        TST01["TESTER-01<br/>功能测试"]
        ATT01["AUTO-TESTER-01<br/>自动化测试"]
        PFT01["PERF-TESTER-01<br/>性能测试"]
        LQA01 --> TST01
        LQA01 --> ATT01
        LQA01 --> PFT01
    end
```

| Template | Roles | Use Case |
|----------|-------|----------|
| **dev-team** | PM + DEV + QA + OPS | Software development |
| **media-team** | PUBLISHER + COLLECTOR + WRITER + EDITOR | Content / media |
| **mvp-team** | MARKETER + RESEARCHER + DESIGNER + BUILDER | Startup MVP |
| **qa-team** | LEAD-QA + TESTER + AUTO-TESTER + PERF-TESTER | Quality assurance |

### Example: `codeflow.json` (mvp-team)

```json
{
  "team": "mvp-team",
  "team_name": "创业MVP团队",
  "roles": [
    {"code": "MARKETER",   "label": "营销策划"},
    {"code": "RESEARCHER", "label": "市场调研"},
    {"code": "DESIGNER",   "label": "产品设计"},
    {"code": "BUILDER",    "label": "全栈开发"}
  ],
  "leader": "MARKETER",
  "lang": "zh"
}
```

After initialization, your project directory looks like:

```
your-project/
├── .cursor/
│   ├── rules/          ← collaboration rules (.mdc)
│   └── skills/file-protocol/SKILL.md
├── docs/agents/
│   ├── codeflow.json   ← team config
│   ├── MARKETER-01.md / MARKETER-01.en.md
│   ├── RESEARCHER-01.md / RESEARCHER-01.en.md
│   ├── tasks/    reports/    issues/    log/
```

---

## Quick Start / 快速开始

### Desktop (PC)

```powershell
# Option 1: Run packaged EXE (recommended, ~35MB)
codeflow-desktop\dist\CodeFlow-Desktop.exe

# Option 2: Run from source (Python 3.10+)
cd codeflow-desktop
pip install -r requirements.txt
python main.py
```

**Download / 下载：**
- China (recommended): https://gitee.com/joinwell52/cursor-ai/releases
- GitHub: https://github.com/joinwell52-AI/codeflow-pwa/releases

On first launch, select your project folder. The Desktop opens a local panel at `http://127.0.0.1:18765` and auto-detects Cursor IDE.

### Mobile PWA

Open in mobile browser and add to home screen:

**https://joinwell52-ai.github.io/codeflow-pwa/**

Scan the QR code shown on the Desktop panel to bind your phone to the PC.

**PWA Capabilities:**
- Scan to bind/unbind PC
- Send tasks to any role
- Task list with categories (Tasks / Reports / Issues / Archive)
- View task markdown source
- Team roles synced from PC `codeflow.json`
- Real-time patrol trace display
- Remote desktop control (focus Cursor / start work)

---

## Self-Healing Nudger / 巡检器自愈

The Desktop Nudger continuously monitors Cursor IDE and auto-recovers from common failures:

| Scenario | Action |
|----------|--------|
| Cursor Connection Error | Auto Reload Window |
| Extension Host frozen | Auto Reload Window |
| Agent task stuck/timeout | Reload Window + nudge message |
| Agent waiting for confirmation | Auto-send "continue" |
| WebSocket disconnect | Auto-reconnect (exponential backoff) |
| Relay rate limit | Throttle + retry |

---

## Relay Service / 中继服务

| Environment | URL |
|-------------|-----|
| Local dev | `ws://127.0.0.1:5252` (`python server/relay/server.py`) |
| Production | Gateway proxies `/codeflow/ws/` to relay process |

The relay only forwards JSON text. Limits: `MAX_MESSAGE_BYTES` = 256KB, `TRANSPORT_MAX_BYTES` (WebSocket frame) = 512KB.

---

## Repository Structure / 仓库结构

```
BridgeFlow/
├── README.md
├── CHANGELOG.md
├── codeflow-desktop/          # Desktop source & packaging
│   ├── main.py                # Entry point (v2.9.44)
│   ├── nudger.py              # Patrol + relay client
│   ├── updater.py             # Auto-update (GitHub + Gitee)
│   ├── panel/index.html       # Desktop web panel
│   ├── templates/agents/      # 4 team templates
│   └── build.spec             # PyInstaller config
├── codeflow-plugin/           # Cursor MCP plugin
├── web/pwa/                   # PWA source (v2.2.9)
│   ├── index.html
│   ├── config.js
│   ├── sw.js
│   └── manifest.json
├── server/relay/server.py     # Local relay for dev
├── docs/
│   ├── agents/                # Agent role definitions
│   ├── images/                # Product screenshots
│   └── user-manual.md
└── scripts/                   # Utility scripts
```

---

## Core Principles / 核心原则

- **Filename IS the protocol** — `TASK-...-Sender-to-Recipient.md`
- **Phone sends text & commands only** — does not replace the desktop execution environment
- **PC handles execution** — bridging, patrolling, file I/O, Cursor wake-up
- **Relay forwards JSON only** — single message limit 256KB
- **One message = one file** — no chat-only channel allowed

---

## License

MIT License. See [LICENSE](LICENSE).

© 2026 joinwell52-AI · From real production experience.

- PWA repo: [github.com/joinwell52-AI/codeflow-pwa](https://github.com/joinwell52-AI/codeflow-pwa)
- Version history: [CHANGELOG.md](CHANGELOG.md)
- User manual: [docs/user-manual.md](docs/user-manual.md)
