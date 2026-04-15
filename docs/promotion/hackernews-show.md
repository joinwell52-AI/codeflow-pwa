# Hacker News — Show HN

**Title:** Show HN: CodeFlow – CDP-powered patrol engine for multi-agent Cursor IDE teams (open source, bilingual)

**URL:** https://github.com/joinwell52-AI/codeflow-pwa

**Text (optional, for self-post):**

---

CodeFlow is an open-source tool for orchestrating multi-role AI teams in Cursor IDE.

Two core innovations:

**1. CDP Patrol Engine** — The desktop app uses Chrome DevTools Protocol to monitor Cursor agents. It reads the DOM in 10ms (vs 300-800ms OCR), detects busy states via Stop button visibility and aria attributes, and switches agents with `Input.dispatchMouseEvent`. Every CDP step auto-degrades to OCR if it fails. Zero stuck states.

| | OCR (before) | CDP (now) |
|---|---|---|
| Accuracy | ~90% | 100% |
| Latency | 300-800ms | 10-15ms |
| Detection | Screenshot guessing | DOM query exact match |

**2. Filename as Protocol** — Every task is a markdown file: `TASK-20260414-003-PM-to-DEV.md` — 7 routing fields in the filename. Zero databases, zero message queues.

The product: Desktop EXE (v2.10.1) patrols agents + Phone PWA (v2.3.1) sends tasks + MCP Plugin for Cursor chat. 4 team templates (dev/media/mvp/qa). Full EN/ZH bilingual — 130+ i18n keys, every message switches with one setting.

Born from a real production project: 87 person-days in 17 days, 91 deployments, zero incidents.

- Try the PWA: https://joinwell52-ai.github.io/codeflow-pwa/
- CDP Technical Doc: https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md
- Product page: https://joinwell52-ai.github.io/codeflow-pwa/promotion/

MIT licensed. Feedback on the CDP patrol approach welcome.
