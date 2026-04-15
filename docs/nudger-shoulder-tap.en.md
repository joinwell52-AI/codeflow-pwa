# Patrol Engine "Shoulder Tap" — Technical Approach and Precision Guide

> Role: Unified explanation for architecture / product / implementation  
> Goal: Without a **cross-session Cursor API**, use desktop automation to **reliably notify** each Agent window that **there is a new task file — please process it**.

---

## I. Is There a "Fundamental" Problem with the Current Technical Approach?

### 1.1 What the approach is

```
Task file written to disk → (optional) filesystem events or polling detect changes
    → Focus Cursor window → hotkey to switch to target Agent tab
    → Open/confirm chat input area → paste fixed short phrase → Enter
    → (optional) OCR to verify current role and input box
```

This is the typical **OS + application UI automation** solution; it is **not a design flaw**: when the vendor does not provide an API to **deliver messages to a specific Agent session**, there is no more "canonical" alternative path.

### 1.2 Where the real risk lies (not "whether patrol is appropriate," but **boundaries**)

| Category | Description |
|----------|-------------|
| **UI contract instability** | Cursor upgrades, themes, layout, Pinned/Agents window changes → hotkeys may still work, but OCR regions and input-box recognition may drift. |
| **OCR is inherently non-deterministic** | Font size, anti-aliasing, mixed CJK/Latin layout cause the same screen to yield fluctuating recognition → **do not treat OCR as the sole source of truth**; use it only as auxiliary verification or fallback clicking. |
| **Focus and timing** | Race conditions between window switch, Ctrl+L, and paste; under high load, insufficient `sleep` causes occasional failures. |
| **"Busy" detection** | Relies on heuristics such as keywords / Stop button → false positives (should nudge but does not) and false negatives (should not nudge but does). |
| **Multi-monitor / scaling** | DPI and occluded windows affect screenshots and coordinates. |

Conclusion: the **direction of the solution is correct**; issues cluster around **engineering resilience and operational constraints**, requiring **layered degradation + configurability + observability**, not a full rewrite.

---

## II. How to Achieve "Precision and Effectiveness"

### 2.1 Product layer: define "effective" first

- **Single source of truth**: collaboration content is authoritative in **TASK files** under `docs/agents/`; **Shoulder Tap** only **wakes** agents — it does not repeat long body text in chat.  
- **Success criteria**: business success is **the file being read by the target role and driving follow-up actions**; desktop automation aims at **best-effort delivery of a short prompt**, with **one manual click** allowed as backup.  
- **Fixed phrasing**: short lines (e.g. patrol-style "receive file") reduce ambiguity when paste fails and reduce model misreading of long text.

### 2.2 Architecture layer: hotkeys primary, OCR secondary

1. **Primary path**: `Ctrl+Alt+1..4` (or keys configured in `codeflow.json` (alias `CodeFlow.json`) / `codeflow-nudger.json` (alias `codeflow-desktop.json`)) to switch tabs → **success should mean "hotkey + short delay"**, not "full-screen OCR to read text".  
2. **Narrow OCR usage**:  
   - Prefer **verifying whether the current tab is the target role** (small ROI beats full screen).  
   - On failure, **click the role name as fallback** (existing logic direction is correct).  
   - If still wrong, the Patrol Engine simulates **Ctrl+Shift+P**, pastes a label consistent with Pinned (e.g. `2-DEV`) in the command palette and presses Enter, then OCR-verifies again; combine with the first two steps in **multi-round retries** to reduce false failures from lost focus or unfinished animations.  
3. **Avoid driving the main path with OCR**: full-screen text scanning is only for debug or fallback; otherwise latency and misjudgments increase.

### 2.3 Implementation layer: already done + recommended next steps

**Directions already reflected in code (examples)**

- When a new task is not delivered due to **cooldown / Agent busy / send failure**, it enters a **pending retry queue**, avoiding "watcher remembered the file but never nudges" (closed loop).  
- Templates such as `first_hello` use **safe formatting** to avoid `.format` crashes when there are no placeholders.  
- Task-side `DEV` and UI-side `DEV` are aligned via **normalized role keys**, reducing "switched but still judged failed".  
- Agent switching: `Ctrl+Alt+1..4` → click tab name → **Ctrl+Shift+P + `1-PM`/`2-DEV`…** three-level degradation, default up to **3** full-round retries, OCR after each step.

**Suggested iterations (by cost/benefit)**

| Priority | Item | Effect |
|----------|------|--------|
| P0 | **Preflight panel** one-click check: project path, `docs/agents`, whether hotkeys are written to `keybindings.json`, Relay connectivity | Reduces ineffective Shoulder Taps from "never configured properly". |
| P0 | **Fixed Cursor usage habits**: single window, Agents bar visible, avoid multiple Cursor instances fighting for focus | Ops constraints often improve success more than code changes. |
| P1 | **File watching**: use `watchdog` (or Windows `ReadDirectoryChangesW`) instead of pure polling to shorten disk-write → first Shoulder Tap attempt latency and reduce idle spinning | Watch for multiple editor saves — apply **debouncing**. |
| P1 | **Configurable delays**: `post_hotkey_delay_ms`, `after_ctrl_l_delay_ms`, etc. in `codeflow-nudger.json` (legacy name `codeflow-desktop.json`) for slow machines | Precision often means tunability. |
| P2 | **ROI OCR**: screenshot only the tab strip or near the input box to reduce noise | Higher accuracy, lower latency. |
| P2 | **Structured logs + panel trace**: `patrol_trace` stage keys + `/api/patrol_trace` + panel "Patrol trace" table, same source as `[Patrol]` logs | Know exactly what the Patrol Engine did. |

### 2.4 Metrics: how to know it "got more accurate"

Recommend tracking long-term in desktop logs or the panel:

- **Shoulder Tap success rate** = successful sends / attempts (break down "window not found," "switch failed," "paste failed").  
- **Retry hit rate** = share of first failure then success on attempt N.  
- **Latency distribution from file write to first attempt** (should drop after introducing watchdog).

Without metrics, iteration is guesswork.

---

## III. Relationship to MCP and the Main Agent Window (clear boundaries)

- **MCP**: convenient for **read/write of task files within the current session** with tools; it **cannot** replace "switch to another Agent window and Shoulder Tap."  
- **Cursor main Agent / Subagents**: suited to **single-user, single-product task splitting**; **CodeFlow**'s **multi-role personas, file audit trail, mobile ADMIN, relay** remain distinct value.  
- **Shoulder Tap** is **complementary** to the above: the file protocol is **what to say**; patrol is **who should listen** — until Cursor exposes a cross-session API, this layer remains necessary.

---

## IV. Summary

1. **Technical approach**: **reasonable** under current constraints; issues are mainly **UI drift, OCR non-determinism, timing and focus**, addressed by **layered strategy + retries + configuration + preflight**, not by rejecting **Shoulder Tap** itself.  
2. **Precision and effectiveness**: product-side **files as sole source of truth + short wake-up lines**; engineering-side **hotkeys primary, OCR verification and fallback secondary, pending retry queue to avoid drops, observability and tunable delays** to continuously tighten the error band.

---

*This document can be extended as implementation evolves: e.g. `watchdog` rollout notes, JSON config field table, alignment with PWA events.*
