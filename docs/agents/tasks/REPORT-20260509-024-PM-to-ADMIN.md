---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260509-024
sender: PM
recipient: ADMIN
priority: P1
thread_key: codeflow-v2-admin-按推荐-acceptance-and-execution-receipt
references:
  - REPORT-20260509-022-PM-to-ADMIN
  - REPORT-20260509-023-PM-to-ADMIN
  - TASK-20260509-026-PM-to-OPS
  - TASK-20260509-027-PM-to-QA
  - TASK-20260509-028-PM-to-DEV
  - DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply
  - docs/design/v0.2-sprint0-roadmap.md
layer: governance
---

# 接受回执：ADMIN 5/9 23:14「按推荐！」覆盖 5 议题 — 立即激活路径已落档

## 一句话结论

**ADMIN 5/9 23:14「按推荐！」永久授权（第 5 句宪法）下，5 议题（A.1 / B.1 / C.1 / D.1 / E.1）全部按 PM 推荐路径激活。** 当前并行 4 件已落档：①派 [TASK-028 S6 codeflow-shell MVP](./TASK-20260509-028-PM-to-DEV.md)（2-3h）/ ②起草 [issue #2 reply 草稿（DRAFT-001）](./DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md)（等 ADMIN 审改）/ ③起草 [v0.2 sprint 0 路线图（draft）](../design/v0.2-sprint0-roadmap.md)（等 v0.1 完工后正式开炮）/ ④本接受回执。OPS-026 + QA-027 不 hold（事实不变）。

---

## §一 5 议题决策落档

| 议题 | ADMIN 拍板 | 实施层动作 |
|---|---|---|
| **A — v0.1-alpha 发布** | A.1 | v0.1 改语义为 **internal RC**（不 publish）+ 完工标准 = `v0.1.0-rc.1` tag + S6 EXE bundle + ADMIN 试用 |
| **B — review.decision enum** | B.1 | 保留 v0.1 enum 不动（含 `needs_human` + `human_approval`）+ 在 README 标 v1.0 alignment pending（v0.2 处置）|
| **C — 5→7 schemas 切换** | C.1 | v0.2 sprint 0 集中 align v1.0（5-7 工作日，[路线图已草拟](../design/v0.2-sprint0-roadmap.md)）|
| **D — agent.layer 升级 Boundary** | D.1 | 跟 C.1 一起在 v0.2 做（10-token can/cannot bundle）|
| **E — issue #2 回应方式** | E.1 | PM 起草 → ADMIN 审改 → ADMIN 用 `@joinwell52-AI` 身份 post（[草稿已落档](./DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md)）|

---

## §二 已派单清单（PM 自决执行 — 按第 5 句宪法）

| 派单 | 启动条件 | 时间预算 | 完工产出 |
|---|---|---|---|
| **TASK-026-PM-to-OPS** | 立即（已派）| ≤ 8 min | S5 Phase E done checkpoint commit + push origin/backup |
| **TASK-027-PM-to-QA** | OPS-026 后 | 1.5-2h | Phase D+E 双回归 + 30x flaky 复核 + 双推荐 |
| **TASK-028-PM-to-DEV** | OPS-026 后 | 2-3h | codeflow-shell MVP（main.ts + sea-config + Hello World demo）+ v0.1.0-rc.1 release notes + B.1 deprecation note |

后续待派单（v0.1 完工后 PM 自决）：
- **TASK-029-PM-to-OPS**：v0.1 internal RC checkpoint commit（S6 完工后）
- **TASK-030-PM-to-QA**：v0.1 internal RC E2E acceptance 测试（双击 EXE / drop TASK / Ctrl+C 三场景）
- **REPORT-025-PM-to-ADMIN**：v0.1.0-rc.1 internal RC 出厂里程碑通报 + ADMIN 试用引导

后续待派单（v0.2 sprint 0 正式启动后）：
- 详见 [docs/design/v0.2-sprint0-roadmap.md](../design/v0.2-sprint0-roadmap.md) §5

---

## §三 issue #2 reply 草稿状态

[`DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md`](./DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md) 已落档。包含：
- **主版**（长版，含 charter 引用 + Q3 详细 hypothesis）— 显式承诺 v0.2 sprint 0 用 NeedsHumanGate→Boundary 改造作为 field evidence
- **§二 短版**（4 段，PM 推荐）— 保留承诺空间，避免过早 hypothesis
- **§一 review checklist** — 6 项可改地方供 ADMIN 参考
- **§三 ADMIN 决策** — a / b / c / d 四选一

⚠️ **PM 推荐 b（短版）**。

ADMIN 审改后用 `@joinwell52-AI` 身份直接 post 到 https://github.com/joinwell52-AI/FCoP/issues/2 即可。

---

## §四 v0.2 sprint 0 路线图状态

[`docs/design/v0.2-sprint0-roadmap.md`](../design/v0.2-sprint0-roadmap.md) 已落档（**status = DRAFT-PM-PROPOSED**）。包含：

- **§3** 7 抽象 mirror 矩阵（upstream 抽象 vs CodeFlow 现状 vs v0.2 动作）
- **§4** v0.1 资产命运（10 行表，每个 schema/类的 v0.2 处置）
- **§5** 实施顺序（依赖图，5 phase）
- **§6** 6 个风险点（含兜底）
- **§7** 6 条启动判据
- **§8** 7 条完成判据
- **§9** §0.0 宪法对照（不修改原话；解读表小幅附注属于 PM 自决）
- **§10** PM 自约束触发对照（4 类「仍请示」全部被 ADMIN 5/9 23:14 覆盖）

⚠️ **§7 第 1 + 2 条启动判据**需要 v0.1 internal RC 完工 + ADMIN 试用满意；**第 3 条**需要等 fcop@1.0.0 final（5/16-5/20）。所以 v0.2 sprint 0 实际启动时间 ≈ **5/20 之后**。

---

## §五 §0.0 宪法对账（不修改原话）

ADMIN 关心：「按推荐」是否会变成 PM 推 §0.0 修改？

**不会**。本接受回执 + 4 文档**全部不修改 §0.0 宪法 5 句原话**。仅做：

- v0.2-sprint0-roadmap.md §9 列出 5 句宪法在 v0.2 工作中的对应兑现（**只读引用，不动原话**）
- v0.2 完工后可能在 §0.0「解读表」第 1 句对应行加一句小幅附注（标 `v0.2 起锁 fcop@>=1.0,<2.0`）— 这属于解读层附注，不修改 ADMIN 原话，PM 自决执行（同前 4 次解读表更新先例：第 3 / 第 4 / 第 5 句宪法时都做过解读表更新）

→ **§0.0 5 句宪法原话从今天起保持永久锁定，PM 不会再触碰**。

---

## §六 当前 git 现状（PM 已写 4 文档 + DEV 等 OPS-026 落地）

```
预期 git status --short（PM 写完本批后）：

 M packages/codeflow-runtime/...                                  (S5 范围 13 项 — 等 OPS-026 commit)
?? packages/codeflow-runtime/src/skill/                           (DEV 写 — 等 OPS-026)
?? docs/agents/tasks/REPORT-20260509-022-PM-to-ADMIN.md           (S5 里程碑 + supersede note)
?? docs/agents/tasks/REPORT-20260509-023-PM-to-ADMIN.md           (FCoP v1.0 align 紧急请示)
?? docs/agents/tasks/REPORT-20260509-023-OPS-to-PM.md             (S4 完成回执)
?? docs/agents/tasks/REPORT-20260509-024-DEV-to-PM.md             (S5 完成回执)
?? docs/agents/tasks/REPORT-20260509-024-PM-to-ADMIN.md           (本接受回执 ⭐)
?? docs/agents/tasks/REPORT-20260509-025-QA-to-PM.md              (S5 测试策略)
?? docs/agents/tasks/TASK-20260509-026-PM-to-OPS.md               (S5 commit selective add)
?? docs/agents/tasks/TASK-20260509-027-PM-to-QA.md                (Phase D+E 回归)
?? docs/agents/tasks/TASK-20260509-028-PM-to-DEV.md               (S6 codeflow-shell MVP ⭐ 新增)
?? docs/agents/tasks/DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md  (issue #2 reply 草稿 ⭐ 新增)
?? docs/design/v0.2-sprint0-roadmap.md                            (v0.2 路线图 ⭐ 新增)
```

⚠️ 注意 — 本批新增 4 文件（TASK-028 + DRAFT-001 + v0.2-roadmap + REPORT-024）**会增加** OPS-026 commit scope。OPS-026 最终 commit 文件数会从原 21 项增至约 **26 项**（22 项 + 4 项新文件）。

PM 自决：**不**修改 TASK-026 的 selective add scope — OPS-026 跑 `git add docs/agents/tasks/`（已经在 scope 内）+ `git add docs/design/`（需补加），会自动 catch 这 4 个新文件。

让我立刻去补加 TASK-026 的 add scope。

---

## §七 时间线（最新状态）

```
2026-05-09 23:14   ADMIN「按推荐」激活 5 议题
2026-05-09 23:18   PM 落 4 文档（TASK-028 + DRAFT-001 + v0.2-roadmap + REPORT-024）
2026-05-09 23:20   PM 修正 TASK-026 add scope 包括 docs/design/ + 新 4 文件
2026-05-09 ~23:30  OPS-026 跑 commit + push origin/backup（约 26 项）
2026-05-09 ~24:00  QA-027 + DEV-028 并行启动
2026-05-10 ~02:00  DEV-028 完工 → S6 完成
2026-05-10 ~02:30  OPS commit v0.1.0-rc.1 internal RC tag
2026-05-10 ~03:00  PM 写 REPORT-025-PM-to-ADMIN「v0.1.0-rc.1 出厂」+ ADMIN 试用引导
2026-05-10 ~03:00  ADMIN 审 DRAFT-001 后 post issue #2 reply
2026-05-10 之后    ADMIN 试用 v0.1 internal RC（自由节奏）+ 等 fcop@1.0.0 final
2026-05-16~20      fcop@1.0.0 final 落地 PyPI（upstream 节奏）
2026-05-20+        v0.2 sprint 0 启动判据满足 → ADMIN 写 TASK 启动 → 5-7 工作日 → v0.2.0-alpha.1 公开试用
```

---

## §八 PM 自约束二次声明

本批 4 文档（TASK-028 + DRAFT-001 + v0.2-roadmap + REPORT-024）涉及的所有「仍请示」项（v0.2 路径变更 / public API breaking 草拟 / charter 解读层附注规划）**全部依赖 ADMIN 5/9 23:14「按推荐」覆盖 C.1 + D.1 + B.1**。如 ADMIN 想撤回任一议题，PM 立即对应回滚（已落档可读，未实施可撤）。

如 ADMIN 想：
- **v0.2 推迟 / 取消** → 写 `TASK-*-ADMIN-to-PM.md`，PM 立即把 v0.2-sprint0-roadmap.md 改成 `STATUS: ABANDONED`
- **NeedsHumanGate 改为立即删（B.0 严格解读）** → 写 `TASK-*-ADMIN-to-PM.md`，PM 立即派 DEV 在 S6 commit 前删除
- **issue #2 reply 不发** → 写 `TASK-*-ADMIN-to-PM.md`，PM 立即把 DRAFT-001 改成 `STATUS: WITHHELD`

否则按本回执路径执行。

---

PM-01 接受回执已落档。状态：4 文档落地 + 修正 TASK-026 add scope + 等 OPS-026 落地 + DEV-028 / QA-027 候命。
