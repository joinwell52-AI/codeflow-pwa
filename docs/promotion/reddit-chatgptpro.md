# Reddit r/ChatGPTPro Post

**Subreddit:** r/ChatGPTPro (or r/LocalLLaMA / r/artificial)
**Title:** Built an open-source system where 4 AI agents collaborate autonomously — now with CDP patrol (10ms DOM scanning)

---

Instead of chatting with one AI, I set up 4 specialized roles in Cursor IDE:

- **PM-01**: breaks down tasks, dispatches to team, collects reports
- **DEV-01**: codes, self-tests, submits deliverables
- **QA-01**: tests everything, files bugs through PM
- **OPS-01**: deploys, health checks, rollback plans

They communicate via markdown files — no databases, no APIs. The filename IS the protocol:

```
TASK-20260414-003-PM-to-DEV.md
```

**v2.10 upgrade: CDP Patrol Engine**

The desktop app now uses Chrome DevTools Protocol to monitor agents:
- **10ms DOM scan** (was 300-800ms OCR) — reads `div[role="tab"]` directly
- **100% accuracy** (was ~90%) — uses `aria-selected` not pixel guessing
- **3-layer busy detection**: Stop button + Spinner + Status text
- **Native mouse events**: `Input.dispatchMouseEvent` bypasses Electron event swallowing
- **Auto-degrades to OCR** if CDP unavailable — zero stuck states

Real results: 87 person-days of work in 17 days. 91 production deployments. Zero incidents.

- GitHub: https://github.com/joinwell52-AI/codeflow-pwa
- Try the PWA: https://joinwell52-ai.github.io/codeflow-pwa/
- CDP Tech Doc: https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md
- Product page: https://joinwell52-ai.github.io/codeflow-pwa/promotion/

v2.10.1: full EN/ZH bilingual UI (130+ i18n keys). Community health score: 100%.

Open source, MIT licensed. Star us if you find it useful!
