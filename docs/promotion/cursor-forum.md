# Cursor Forum — Updated Post

**Category:** Showcase / Built for Cursor
**Title:** CodeFlow v2.10: CDP patrol engine reads Cursor DOM in 10ms — phone-first multi-agent orchestration

**Update to existing thread:** https://forum.cursor.com/t/cursor-ai-automated-team-4-role-autonomous-ai-dev-team-with-mdc-rules-patrol-bot-87-person-days-in-17-days/156224

---

**UPDATE v2.10.1: CDP Patrol Engine + 4 team templates + Full Bilingual UI**

Big update since the last post. We replaced the OCR-based patrol with **Chrome DevTools Protocol (CDP)** — the desktop app now reads Cursor's DOM directly.

## What CDP changed

| | OCR (v2.9) | CDP (v2.10) |
|---|---|---|
| Accuracy | ~90% | **100%** (DOM attributes) |
| Latency | 300-800ms | **10-15ms** |
| Agent detection | Screenshot + image recognition | `div[role="tab"]` + `aria-selected` |
| Busy detection | Pixel guessing spinners | Stop button visibility + status text |
| Click method | `pyautogui.click(x,y)` | `Input.dispatchMouseEvent` (native) |

**Design**: CDP primary, OCR purely as graceful fallback. Every CDP step auto-degrades — port down, connection dropped, verify failed — all silently fall back to OCR. Zero stuck states.

## How CDP identifies agents

Cursor's agents appear as tabs. CDP scans two DOM layers:
1. **Tab bar** — `div[role="tab"]` with `aria-selected` for active state
2. **Agent sidebar** — `span.agent-sidebar-cell-text` for overflow roles

3-layer busy detection: Stop/Cancel button → Spinner animation in Composer → Status text matching (generating, thinking, planning, running terminal).

## The full workflow (unchanged)

1. Open PWA on phone → type a task
2. Task arrives on PC as `TASK-*.md` file
3. PM-01 decomposes → dispatches to DEV/QA/OPS
4. Desktop EXE **CDP-patrols** all agents — auto-nudges stuck tasks, self-heals freezes
5. Reports flow back to phone in real-time
6. You review from anywhere

## Architecture

```
Phone (PWA)  <->  WebSocket Relay  <->  Desktop EXE  <->  Cursor IDE
   phone               relay              CDP patrol       4 AI agents
 send tasks        event bridge        10ms DOM scan      PM/DEV/QA/OPS
 view status       room-based          self-healing       .mdc rules
 QR binding        < 8KB msgs          auto-nudge         file protocol
```

## What's in the box

### Desktop App (v2.10.1)
- Windows EXE (~35MB), double-click to run
- **Full i18n**: 130+ translation keys, EN/ZH switch with one setting
- **CDP patrol engine**: reads DOM in 10ms, 100% accurate agent detection
- 3-layer busy detection (Stop button + Spinner + Status text)
- Auto-nudge for stuck/idle agents
- OCR as graceful fallback when CDP unavailable
- Real-time relay bridge to phone

### Mobile PWA (v2.3.1)
- Send tasks to your AI team from your phone
- Real-time status, markdown viewer, role filtering
- QR code binding — scan and connect in 5 seconds
- Full bilingual support (EN/Chinese)
- Works offline, add to home screen

### MCP Plugin
- `init_project` — set up team with one command
- `send_task` — dispatch tasks from Cursor chat
- `list_tasks` / `get_team_status` — read reports without leaving the IDE

### 4 Team Templates
- **dev-team**: PM / DEV / QA / OPS
- **media-team**: WRITER / EDITOR / PUBLISHER / COLLECTOR
- **mvp-team**: MARKETER / RESEARCHER / DESIGNER / BUILDER
- **qa-team**: PM / AUTO-TESTER / PERF-TESTER / SECURITY-TESTER

## How it compares

| | CursorRemote | CodeFlow |
|---|---|---|
| Phone role | Remote control (approve/reject) | **Command center (send tasks)** |
| Agent model | Single agent, multi-window | **Multi-role team (4+ agents)** |
| Patrol tech | — | **CDP (10ms DOM scan) + OCR fallback** |
| Offline | — | **PWA with Service Worker** |
| Protocol | CDP DOM polling | **File-based (every msg = .md file)** |
| Price | $7.99 | **Free & open source (MIT)** |
| Team templates | — | **4 templates (dev/media/mvp/qa)** |

## Links
- **Try PWA on phone**: https://joinwell52-ai.github.io/codeflow-pwa/
- **Download Desktop EXE**: https://github.com/joinwell52-AI/codeflow-pwa/releases
- **Product page**: https://joinwell52-ai.github.io/codeflow-pwa/promotion/
- **GitHub**: https://github.com/joinwell52-AI/codeflow-pwa
- **CDP Technical Doc**: https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md
- **Methodology**: https://joinwell52-ai.github.io/joinwell52/

MIT licensed. Battle-tested: 91 production deployments. Feedback welcome!
