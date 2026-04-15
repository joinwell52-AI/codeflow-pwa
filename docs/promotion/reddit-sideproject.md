# Reddit r/SideProject Post

**Subreddit:** r/SideProject
**Title:** I'm a solo dev running a full AI team from my phone — now with CDP patrol that reads Cursor DOM in 10ms

---

I wanted to see if one person could manage a complete AI development team — not by chatting with one bot, but by orchestrating PM, DEV, QA, and OPS roles that collaborate autonomously.

After 17 days on a real production project (87 person-days of output, 91 deployments, zero incidents), I turned it into an open-source product: **CodeFlow (v2.10.1)**.

**The big v2.10 upgrade: CDP Patrol Engine**

The desktop app used to monitor agents via OCR (slow, ~90% accurate). Now it uses Chrome DevTools Protocol — reads Cursor's DOM directly in 10ms, 100% accurate. Detects busy agents via Stop button visibility. Auto-degrades to OCR if CDP fails.

**The setup:**
1. Download a 35MB Windows EXE
2. Double-click — it launches Cursor IDE + a control panel
3. Scan a QR code from your phone
4. Send tasks from the couch, review results over coffee

**What makes it different:**
- **CDP patrol**: 10ms DOM scan, 3-layer busy detection, native mouse events
- No databases, no APIs — tasks are markdown files with structured filenames
- Auto-degrades: CDP -> OCR -> retry queue. Zero stuck states.
- 4 team templates: dev-team, media-team, mvp-team, qa-team

**Stack:** Python (Desktop), CDP + OCR (patrol), vanilla HTML/JS (PWA), WebSocket relay

- GitHub: https://github.com/joinwell52-AI/codeflow-pwa
- Try the PWA: https://joinwell52-ai.github.io/codeflow-pwa/
- Product page: https://joinwell52-ai.github.io/codeflow-pwa/promotion/
- CDP Tech Doc: https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md

v2.10.1 just shipped: full EN/ZH bilingual UI (130+ translation keys), community health score 100%.

MIT license. Star us if you find it useful!
