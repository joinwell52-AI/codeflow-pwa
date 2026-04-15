# Product Hunt Launch Draft

## Product Name
CodeFlow (码流)

## Tagline (60 chars max)
Command your AI dev team from your phone. Open source.

## Alternative Taglines
- CDP-powered AI agent patrol — 10ms response, 100% accuracy
- One person, one AI team, shipping real products
- Filename as Protocol — the simplest multi-agent orchestration

## Description (260 chars)
CodeFlow orchestrates multi-role AI teams (PM/DEV/QA/OPS) in Cursor IDE. CDP patrol reads DOM in 10ms — 60x faster than OCR. Send tasks from phone, agents execute on PC, everything is markdown. 4 team templates, full EN/ZH i18n, self-healing. v2.10.1.

## Topics
- Developer Tools
- Artificial Intelligence
- Open Source
- Productivity
- Remote Work

## Gallery Images (5 recommended)
1. `product-1.png` — Brand poster: "Commands Flow, Intelligence Follows"
2. `hero-banner.png` — Brand poster with Chinese tagline
3. `codeflow-0.png` — Desktop panel: preflight & agent guide
4. `pwa-0.jpg` + `pwa-1.jpg` — Phone PWA: workspace + send task
5. `cursor-0.png` — Cursor IDE with Desktop panel side by side

## First Comment (Maker Comment)

Hi Product Hunt! I'm the maker of CodeFlow.

I started by writing a tutorial on how to run a 4-role AI team in Cursor IDE. The result was surprising: 87 person-days of work completed in 17 days, 91 production deployments, zero incidents.

But the setup was manual and fragile. OCR-based agent monitoring was slow (300-800ms) and only ~90% accurate. So I rebuilt the entire patrol engine on **Chrome DevTools Protocol (CDP)**.

### What CDP changed:

| | OCR (before) | CDP (now) |
|---|---|---|
| Accuracy | ~90% | **100%** |
| Latency | 300-800ms | **10-15ms** |
| Agent detection | Screenshot guessing | DOM query exact match |
| Click method | Screen coordinates | Native browser events |

CDP reads Cursor's DOM directly — `div[role="tab"]` for agent tabs, `aria-selected` for active state, Stop button visibility for busy detection. Every CDP step auto-degrades to OCR if anything fails. Zero stuck states.

### The full stack:

- **Desktop EXE** (v2.10.1): CDP patrol engine monitors all agents, auto-nudges stuck tasks, self-heals frozen Cursor windows, full EN/ZH bilingual (130+ i18n keys)
- **Phone PWA**: Send "do a security audit" from your couch, come back to find the report
- **MCP Plugin**: Init teams, dispatch tasks, read reports — all from Cursor chat
- **Protocol**: Every task is `TASK-20260414-003-PM-to-DEV.md`. The filename IS the routing. No databases, no message queues.

4 team templates (dev/media/mvp/qa), full EN+ZH bilingual, MIT licensed. GitHub community health: 100%.

Try the PWA right now on your phone:
https://joinwell52-ai.github.io/codeflow-pwa/

CDP technical deep-dive:
https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md

Would love your feedback!

## Links
- Website: https://joinwell52-ai.github.io/codeflow-pwa/promotion/
- GitHub: https://github.com/joinwell52-AI/codeflow-pwa
- CDP Tech Doc: https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md
- Desktop Download: https://github.com/joinwell52-AI/codeflow-pwa/releases
