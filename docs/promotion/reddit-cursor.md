# Reddit r/cursor Post

**Subreddit:** r/cursor
**Title:** CodeFlow v2.10.1: CDP patrol reads Cursor DOM in 10ms — manage 4 AI agents from your phone (open source, bilingual)

---

Hey r/cursor!

You know the pain: your Cursor agent gets stuck, and you don't notice for 20 minutes. OCR-based monitoring was our first solution — but it was slow (~300ms) and only ~90% accurate.

So in v2.10 we rebuilt the patrol engine on **Chrome DevTools Protocol (CDP)**.

**What CDP does:**
- Reads `div[role="tab"]` + `aria-selected` to identify which agent is active — **10ms, 100% accurate**
- Detects busy states via Stop button visibility, Spinner animation, status text — **3-layer detection**
- Switches agents with `Input.dispatchMouseEvent` (native browser events, not `pyautogui`)
- Auto-degrades to OCR if CDP is unavailable — **zero stuck states**

**The workflow:**
1. Open PWA on phone -> type a task
2. Task arrives on PC as `TASK-*.md` file
3. PM-01 decomposes, dispatches to DEV/QA/OPS
4. Desktop EXE CDP-patrols all agents — auto-nudges stuck tasks
5. Reports flow back to your phone in real-time

**What's included:**
- **Desktop EXE** (v2.10.1, ~35MB) — CDP patrol + OCR fallback + full EN/ZH bilingual UI
- **Phone PWA** (v2.3.1) — command center, not just a dashboard
- **MCP Plugin** — init teams and dispatch from Cursor chat
- **4 team templates**: dev-team, media-team, mvp-team, qa-team

**v2.10.1 highlights:** Full i18n support (130+ translation keys), all API messages / patrol traces / panel UI switch between EN and ZH. Community health score: 100%.

**The protocol:** Every task is `TASK-20260414-003-PM-to-DEV.md`. Zero databases.

- **Try PWA now (phone):** https://joinwell52-ai.github.io/codeflow-pwa/
- **Download Desktop EXE:** https://github.com/joinwell52-AI/codeflow-pwa/releases
- **China mirror:** https://gitee.com/joinwell52/cursor-ai/releases
- **CDP Technical Doc:** https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md
- **Product page:** https://joinwell52-ai.github.io/codeflow-pwa/promotion/
- **GitHub:** https://github.com/joinwell52-AI/codeflow-pwa

MIT licensed. 91 production deployments, zero incidents. Star us if you find it useful!
