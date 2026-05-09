---
protocol: fcop
version: 1
kind: draft
draft_id: DRAFT-20260509-001
sender: PM
recipient: ADMIN
priority: P1
thread_key: codeflow-v2-fcop-issue-2-reply-draft
references:
  - https://github.com/joinwell52-AI/FCoP/issues/2#issuecomment-4412811192
  - REPORT-20260509-023-PM-to-ADMIN
  - docs/design/codeflow-v2-on-fcop-sdk.md
layer: governance
---

# DRAFT: issue #2 第三条 comment 草稿（CodeFlow PM 团队回应 FCoP v1.0 RC.1 reply）

> **状态**：PM 草拟。等 ADMIN 审改后，由 ADMIN 用 `@joinwell52-AI` 身份 post 到
> https://github.com/joinwell52-AI/FCoP/issues/2
>
> **回应 upstream 5/9 14:59 reply 的 3 个问题**：
> 1. Boundary 是否覆盖 worker/governance/admin + 10-token can/cannot？
> 2. 接受 `>=1.0,<2.0` pin 推荐？
> 3. 愿意为 Fields 3+4 v1.2 提供 field evidence？

---

## ✏️ 草稿正文（建议直接 post 内容）

```markdown
## CodeFlow v2 / Sprint S5 update + accepting v1.0 alignment

Thanks for the detailed reply — exactly the kind of clarity that lets us
plan downstream. Posting back as `@joinwell52-AI` (CodeFlow project lead)
with the cross-project alignment decisions made on the CodeFlow side
this evening (2026-05-09 23:14 UTC+8).

### TL;DR

- **All 5 fields' v1.0 dispositions accepted** — Field 1 (Boundary
  generalisation) is welcomed; Fields 2-5 deferred to v1.1+/v1.2+ are
  acknowledged.
- **CodeFlow v0.1 will ship as `v0.1.0-rc.1` internal preview** (not
  publishing to npm) and **v0.2 sprint 0 will fully align to fcop@1.0
  charter** (7 abstractions, Boundary, the works).
- **Direct answers to your three questions: yes / yes / yes.** Details below.

### Where CodeFlow stands today (Sprint S5 just landed)

CodeFlow v2 backend kernel is ~95% to v0.1 finish line:

- **94/94 tests pass + 30× 0 flaky.** 14 runtime subsystems composed
  (AgentRegistry, PersistentStore, RuntimeBootstrap, SessionManager,
  TaskDispatcher, ReviewEngine, ReviewWriter, NeedsHumanGate,
  AgentStatusReconciler, SkillRegistry, KernelDependencyValidator,
  MCPInjector, …)
- **fcop kernel-dependency gate is closed in two paths**:
  `AgentRegistry.register` rejects pre-SDK if a spec lacks `^fcop@.+`,
  and `RuntimeBootstrap.run()` rejects on rehydrate. Tested via 17
  TS-7.x scenarios.
- Sprint **S6 (codeflow-shell EXE bundle + Hello World demo)** is the
  last v0.1 milestone, expected ~3 hours of work (2-3 hours actual,
  given Sprint S5's 47-minute pace).

The CodeFlow side accepts that this v0.1 ships against the **5-schema
shape** (agent / task / review / session / skill) and **`needs_human` +
`human_approval` review semantics** — exactly the layout this Issue
proposed. We're now treating that as **v0.1-only internal preview**;
CodeFlow v0.2 sprint 0 will mirror your 7-schema shape verbatim from
`spec/schemas/`.

### Direct answers

> **Q1. Does the Field 1 → Boundary generalisation match your CodeFlow
> runtime design?**

**Yes** — and it's actually a deeper fit than our original `agent.layer`
3-value enum proposal.

CodeFlow's design philosophy (recorded as our project's third charter
clause from human ADMIN, 2026-05-09 13:51) is:

> "Define `constraints + capabilities + state + permissions` and let
> agents do their own planning / collaboration / decomposition /
> implementation. We're not 'controlling agents' — we're 'providing
> a non-crashing collaborative universe for agents'."

Your Boundary abstraction (layer + 10-token `can`/`cannot` capability
bundle + `assert_boundary` + `BOUNDARY_VIOLATED` event) is the **exact
schematic embodiment** of that — `layer` covers permissions, the
capability bundle covers capabilities, `assert_boundary` covers
constraints, the event covers state. Our 3-value layer was a coarse
approximation; Boundary is the precise expression.

The 10 tokens look sufficient for our worker/governance/admin
distinctions; we'll exercise them in v0.2 sprint 0 and report back any
gaps as field evidence (per Q3 below).

> **Q2. Are you OK with the `>=1.0,<2.0` pin recommendation?**

**Yes**, with one timing nuance:

- CodeFlow v0.1.0-rc.1 (this week, internal preview only) — currently
  pinned conceptually to `pending-fcop-review` placeholder; we won't add
  a real `peerDependencies` until v0.2.
- CodeFlow v0.2.0-alpha.1 (~3-4 weeks out) — will set:
  ```jsonc
  "peerDependencies": { "fcop": ">=1.0.0,<2.0.0" }
  ```
- We'll target alignment with `fcop@1.0.0` final (your 5/16-5/20 window),
  not the RC.

This means CodeFlow v0.2 alpha probably lands ~6-8 weeks from now,
which gives `fcop@1.0.0` final ~2 weeks of mature use before we depend
on it as a peer.

> **Q3. Would you contribute additional field evidence for Fields 3+4
> deferred to v1.2?**

**Yes** — and the v0.2 sprint 0 work is the natural place to gather it.

Specifically:

- We'll port CodeFlow's current `NeedsHumanGate` (sprint S4 / decision K
  / decision O — currently emits `decision: needs_human` on session
  end) **to a Boundary capability check first**. If it works (i.e. all
  use cases collapse cleanly into `cannot.<token>` denials), we'll
  formally retract our Field 3+4 proposal and report "Boundary covers
  it."
- If it doesn't work — i.e. we hit a use case that *genuinely* needs the
  reviewer to say "approve in principle but with human oversight,"
  rather than "you're forbidden from doing this" — we'll write up the
  failure case with the exact agent / task / boundary tokens involved
  and append it here as fresh evidence. That's the field evidence
  v1.2 needs.

Honest leading hypothesis from our side: **most use cases will
collapse into Boundary**, and Field 3+4 may end up genuinely retired
rather than deferred. The remaining uncertain cases are around
"semantic intent ambiguity" (e.g. a SQL query that *could* be missing a
`tenant_id` clause but might also be deliberately cross-tenant) — these
are interpretive, not capability-bounded, and are where the
`needs_human` shape still feels like the correct answer. We'll let the
v0.2 work sort it out empirically.

### Acknowledgements re: your refinements

Your three landing-time refinements (5/9 5:32 reply) are accepted:

a. `auth_method: password` → `password_with_2fa` — agree, will pass
   through cleanly when we eventually reach v1.2.
b. `channel: 'manual_file_edit'` requires `device_id` or
   `channel_attestation` — agree, that's the audit-trail-no-bypass
   instinct.
c. `risk_level: 'irreversible'` reserves `requires_rollback_plan` field
   name today — agree, easy to honor in our v0.2 mirror.

### Closing

The bigger reframing — that v1.0 ships **7 abstractions** (Agent /
Encoding / IPC / Event / Failure / Boundary / Audit) instead of just
adding 5 fields to a pre-existing 5-schema shape — is in our view the
**right** call. It does mean our `packages/codeflow-protocol/` will
need a structural rewrite in v0.2 sprint 0, but that's a healthier
alignment than bolting v1.1 on top of a v0.7-shaped consumer.

Will reply here again when v0.2 sprint 0 starts (estimated ~1 week
after v0.1 internal preview, so likely ~2-3 weeks from today) with
either the field evidence requested in Q3, or the retraction of Fields
3-4 if Boundary subsumes them.

Thanks again — this is exactly the kind of upstream-downstream
synchronization rhythm we hoped FCoP would enable.

— @joinwell52-AI (CodeFlow PM team)
```

---

## §一 review checklist for ADMIN（建议改的地方）

| # | 段落 | 当前措辞 | ADMIN 可考虑改 |
|---|---|---|---|
| 1 | 标题 | "CodeFlow v2 / Sprint S5 update + accepting v1.0 alignment" | 是否换成更简短的"v0.2 alignment plan"？ |
| 2 | TL;DR 第 3 项 | "Direct answers to your three questions: yes / yes / yes" | 是否过于直白？是否需要更含蓄？ |
| 3 | 第 3 段第 1 句 | "given Sprint S5's 47-minute pace" | 是否暴露内部节奏？是否换成 "given recent sprint velocity"？ |
| 4 | Q1 答案引用了"third charter clause from human ADMIN, 2026-05-09 13:51" | 这是 §0.0 第 3 句宪法 | 是否暴露内部 charter？是否改成更通用措辞？ |
| 5 | Q3 答案 leading hypothesis | "most use cases will collapse into Boundary, and Field 3+4 may end up genuinely retired" | 是否说得太绝对？要不要 hedge？ |
| 6 | 全篇语气 | First-person plural ("we", "our") | 是否换 "the CodeFlow team" / 单数等？ |

## §二 替代方案（如 ADMIN 不喜欢上面这版）

可选更简短版（4 段）：

```markdown
## v1.0 alignment accepted — v0.2 sprint 0 will mirror 7-schema shape

Acknowledged. Three direct answers:

1. **Q1 (Boundary generalisation)**: yes — exact match for our internal
   "constraints + capabilities + state + permissions" model.
2. **Q2 (`>=1.0,<2.0` pin)**: yes, will activate at CodeFlow v0.2
   (post 1.0.0 final tag, ~5/20).
3. **Q3 (field evidence for v1.2)**: yes — porting current NeedsHumanGate
   to a Boundary capability check is the v0.2 sprint 0 mainline; will
   report whether Boundary subsumes Fields 3+4 entirely (current leading
   hypothesis: yes for most cases) or whether genuine "semantic intent
   ambiguity" cases survive.

CodeFlow v0.1 ships this week as `v0.1.0-rc.1` internal preview against
the 5-schema layout (deprecation noted in README); v0.2 sprint 0 will
do the structural rewrite to mirror your 7 schemas verbatim from
`spec/schemas/`.

Will reply here when v0.2 starts (~2-3 weeks).

— @joinwell52-AI
```

## §三 ADMIN 决策

| 选项 | |
|---|---|
| **a** | 用主版（长版，含 charter 引用 + 详细 hypothesis）|
| **b** | 用 §二 短版（4 段）|
| **c** | 在 a/b 中混合，PM 起草 v2 |
| **d** | ADMIN 自己重写 |

**PM 推荐 b**（短版）：理由 — upstream 反馈清晰、CodeFlow 还没真正进入 v0.2 实施，过早承诺 hypothesis 反而增加 v1.2 deferred field 翻案的难度。短版保留承诺空间。

---

PM-01 草拟。等 ADMIN 在 a / b / c / d 拍板。
