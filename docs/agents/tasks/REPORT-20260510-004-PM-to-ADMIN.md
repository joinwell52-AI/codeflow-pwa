---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-004
sender: PM
recipient: ADMIN
priority: P0
thread_key: codeflow-v0.2-day1-night-s0-incident-and-p2-completion
references:
  - REPORT-20260510-003-PM-to-ADMIN
  - REPORT-20260510-005-OPS-to-PM
  - REPORT-20260510-006-QA-to-PM
  - REPORT-20260510-007-DEV-to-PM
  - TASK-20260510-008-PM-to-OPS
  - TASK-20260510-009-PM-to-QA
layer: governance
---

# REPORT-20260510-004：S0 安全事件 + DEV P2 抢跑完工 + 路线再次提前

## §一 一句话结论

**🚨 S0 安全事件**：ADMIN 之前曾把真 Cursor API key 误填到 `.env.example`（commit-tracked 模板），DEV 在 P2 自测时发现 + 立即 `git checkout --` revert，**真 key 0% 进入 git 历史 / 0% push 到任何 remote**。
**🚀 重大进展**：OPS-005 + DEV P2 双双抢跑完工 — `v0.2.0-alpha` 已 commit/tag，DEV 已交 P2（MT-2 + EXE spike + runtime 99/99）。
**📅 路线再次提前**：原 5/14 v0.2.0-rc.1 → 现可能 5/12 EOD 出（提前 2 天）；5/27 v1.0 公开发布锁定。

---

## §二 🚨 S0 安全事件 — 完整时间线 + 实际风险评估

### §2.1 时间线

| 时间 | 事件 | 行为者 |
|---|---|---|
| 5/10 ~01:30 | DEV P1 完工 — `.env.example` 模板 placeholder = `ck_xxxxxxxx`（DEV 写错前缀，真 Cursor key 是 `crsr_*`）| DEV-01 |
| 5/10 ~01:50 | ADMIN 首次试用真 SDK 路径，**误把真 key 直接编辑到 `.env.example` line 23**（而非 cp 一份到 `.env`）| ADMIN |
| 5/10 ~02:00 | ADMIN 改回头放到 `codeflow-shell/.env`（正确位置）；但 `.env.example` working tree 仍含真 key | ADMIN |
| 5/10 ~02:05 | DEV 启动 P2 自测，跑 `git status` 发现 `M codeflow-shell/.env.example` | DEV-01 |
| 5/10 ~02:10 | DEV 立即 `git checkout -- codeflow-shell/.env.example` revert 工作目录 | DEV-01 |
| 5/10 ~02:17 | ADMIN 通知 PM「`.env.example` 已经有 key」（PM 先以为是 ADMIN 在问占位符）| ADMIN |
| 5/10 ~02:20 | PM 验证 `.env.example` working tree 已干净（DEV revert 成功）| PM-01 |
| 5/10 ~02:22 | PM 验证 `codeflow-shell/.env` 真 key 格式正确（69 字符 / `crsr_*` / git 排除）| PM-01 |
| 5/10 ~02:30 | PM 改 `.env.example` 加 DO NOT EDIT 顶部强警告 + `ck_` → `crsr_REPLACE_WITH_YOUR_REAL_KEY` 占位符；DEV-007 报告披露 S0 全貌 | PM + DEV |
| 5/10 ~02:35 | PM 派 OPS-008 commit DEV P2 + .env.example 防御 + tag v0.2.0-beta | PM-01 |

### §2.2 实际泄露风险评估

| 风险层 | 是否发生 | 证据 |
|---|---|---|
| L1 真 key 进 PUBLIC origin (`codeflow-pwa`) git 历史 | ❌ **未发生** | `git log --all -p --full-history -- codeflow-shell/.env.example \| grep crsr_` 输出空 |
| L2 真 key 进 PRIVATE backup (`codehouse`) git 历史 | ❌ **未发生** | 同上扫描全 commit history 0 命中 |
| L3 真 key 进过 working tree 短暂存在 | ✅ 发生（约 20-30 分钟） | DEV 在 commit 前 revert |
| L4 真 key 在 ADMIN 本地磁盘留存 | ✅ 仍在使用中 | `codeflow-shell/.env`（gitignored）|

**实际泄露概率 = 0**（key 仅在 ADMIN 本地 working tree 短暂存在，0 push 0 commit）。

### §2.3 PM 推荐处置（按风险厌恶度二选一）

**选项 A（保守 — PM 推荐）**：吊销那条 `crsr_*` key，重新生成新 key
- 理由：成本极低（< 1 分钟）；彻底消除 L4 残留风险；defense-in-depth 原则
- 操作：[https://cursor.com/settings](https://cursor.com/settings) → Account → API keys → Revoke 那条 → Create new → 写到 `codeflow-shell/.env`（正确位置）

**选项 B（务实）**：保留那条 key 继续使用
- 理由：实际泄露概率 0；ADMIN 本地磁盘是受信环境
- 操作：什么都不做，直接进 v0.2.0-beta + A-07~10 真 SDK 验收

**ADMIN 选 A 或 B**（不回答 = 默认 A 保守路径，PM 等 ADMIN 重新生成 key + 通知 PM 后再触发 QA-009 真 SDK 验收）。

### §2.4 防御加固（PM 已落地）

- ✅ `.env.example` 顶部加 12 行 DO NOT EDIT 强警告块（含「origin = github.com/joinwell52-AI/codeflow-pwa is PUBLIC」明示）
- ✅ 占位符 `ck_xxxxxxxx` → `crsr_REPLACE_WITH_YOUR_REAL_KEY_DO_NOT_EDIT_THIS_FILE`（更醒目）
- ✅ TASK-008 §A.2 给 OPS 加了 commit 前 `git diff` 安全核查
- 🚧 DEV REPORT-007 §五 §S0 建议加 pre-commit hook 检测 — PM 推**到 v0.2.0-rc.1 期间**做（不阻塞当前节奏）

---

## §三 🚀 DEV P2 + OPS-005 双线抢跑完工

### §3.1 OPS-005（已落地，未在 §一 §二 通报中）

| 维度 | 值 |
|---|---|
| Commit A（DEV P1 主体）| `9f24841 feat(s6-v0.2-sprint0-p1): real CursorSdkAdapter wiring + ConfigLoader` |
| Commit B（5/10 加速 docs）| `6a8ad8d docs(s6-v0.2-acceleration): kickoff reports, fixtures, and relay spike` |
| 本地 tag | `v0.2.0-alpha`（指向 `9f24841`，**未**推 origin/backup）|
| 三仓 HEAD | origin / backup 同步至 `6a8ad8d`；gitee 仍 `62532a7`（HANDOFF G3）|

### §3.2 DEV-007 P2（5 大成果 + 0 P0 风险）

| 成果 | 关键数据 |
|---|---|
| **MT-2 atomic-write retry-on-EPERM** | 5 测试 TS-AW-1~5 / runtime 94 → **99 全过** / 0 flake |
| **EXE 打包 spike doc** | `docs/design/spike-exe-packaging.md` 15 KB / 7 方案逐项实测 / 4 根因 / 4 v1.0 重审 gates |
| **EXE 实测结论** | **7 方案在当前 sprint 内全不可行**（ESM/CJS + native sqlite3 + monorepo hoist 三向冲突）→ pack.cmd 改为 spike-only stub，默认 forwards to npm start |
| **`@codeflow/runtime` + codeflow-shell** | 双包 0.2.0-beta / typecheck 0 错 / 真 governance loop 端到端 0 EPERM |
| **0 安全事件遗漏** | DEV 主动揭示 S0；MT-2 修对了 race；spike doc 4 个 v1.0 gates 给上游 fcop@1.0 重启入口 |

### §3.3 4 个 v1.0 EXE 重审 gates（DEV-007 §二 §2.2）

| Gate | 触发条件 | 解锁 EXE 路径 |
|---|---|---|
| R-1 | `@cursor/sdk` 1.x → 2.x 修 dist/esm packaging + 双产物 | esbuild ESM bundle 路径解 |
| **R-2** | **迁 `fcop@>=1.0` 后 cursor-sdk 替换为 fcop REST/WS adapter，不再依赖 sqlite3** | **同时解 EXE D + relay-bridge** |
| R-3 | bun 1.x → 2.x 引入 `--asset` 把 .node 嵌进 EXE | bun --compile 路径解 |
| R-4 | `@cursor/sdk` 加为 `codeflow-shell` 直接 dep（解 monorepo hoist）| ESM + externals 路径解 |

**PM 战略观察**：**R-2 是最划算路径** — 它**同时**解锁 EXE + relay-bridge + fcop 治理对齐三件大事。这印证了 PM 在加速路线 §四 D1「不等 fcop@1.0 final，用 RC.1 直开干」决策的合理性。

---

## §四 路线再次提前 — 新时间盘

```
原计划                                    现状（DEV 抢跑后）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5/10 EOD: 派单                            5/10 02:30 ✅ 全派完 + Day 1 完工
5/11 EOD: v0.2.0-alpha                    5/10 02:00 ✅ alpha 已 commit/tag (early -1d)
5/12 EOD: v0.2.0-beta                     5/10 02:30 ✅ DEV beta 已交付，等 OPS commit (early -2d)
5/14 EOD: v0.2.0-rc.1 (relay-bridge)      可能 5/12 EOD 完工 (early -2d)
5/22 EOD: v1.0-rc.1                       5/20 EOD (early -2d，假设 fcop@1.0 5/16 落 PyPI)
5/27 EOD: ★★★ v1.0 公开发布              5/25 EOD (early -2d)
```

**结论**：v1.0 公开发布有望从 5/27 提前到 **5/25**（比原 6/10 提前 16 天）。

但 PM 不擅自压缩缓冲 — 5/27 仍作为正式承诺，提前 2 天作为缓冲（应对 fcop@1.0 final 延期、QA 发现真 SDK bug、PWA 联调坎坷等）。

---

## §五 已派下一波 2 TASK + 1 ADMIN-facing REPORT（5/10 02:35）

| 文件 | 接收 | 内容 | SLA |
|---|---|---|---|
| [TASK-008](TASK-20260510-008-PM-to-OPS.md) | OPS | DEV P2 commit (10 文件 + .env.example 防御) + tag `v0.2.0-beta` (不推 origin) + 5/10 docs commit | ≤ 10 min |
| [TASK-009](TASK-20260510-009-PM-to-QA.md) | QA | v0.2.0-beta 全量 + A-07~10 真 SDK 验收（**HARD GATE**：严禁 cat `.env`）| ≤ 3h |
| 本 REPORT | ADMIN | S0 通报 + DEV/OPS 双抢跑通报 + 选 A/B 决策点 | 立刻 |

---

## §六 ADMIN 待办（按重要度）

| P | 项 | 状态 |
|---|---|---|
| **P0** | **§2.3 选 A（吊销 + 重新生成）or B（保留）**（不回答 = 默认 A）| 等 ADMIN |
| **P0** | 在 **OPS / QA cursor session 各打 1 次「巡检 开工」**启动 OPS-008 + QA-009 | 现在 |
| P1 | 试用 v0.1.0-rc.1（按 [REPORT-001 §三](REPORT-20260510-001-PM-to-ADMIN.md)）| 任意 |
| P2 | 拍板 [DRAFT-001 issue #2 reply](DRAFT-20260509-001-PM-to-ADMIN-issue-2-reply.md) | 任意（已就绪 5 天）|
| P2 | 回 D4：是否扩 DEV-02 cursor session（PM 推荐方案 A 不扩）| 任意（不回 = 默认 A）|

### 给 ADMIN 的「不要再做的事」清单（PM 关键提醒）

| ❌ 严禁 | ✅ 替代 |
|---|---|
| 编辑 `.env.example`（commit-tracked 模板！）| 仅编辑 `.env`（gitignored）|
| 把真 key 贴到 chat / TASK 文件 / commit message | 直接写到 `codeflow-shell/.env` 或 `~/.codeflow/v2/.env` |
| 在公开仓库（origin = `codeflow-pwa` PUBLIC）push 任何含 `crsr_*` 字串的 commit | OPS-008 §A.2 已加 commit 前 `git diff` 安全核查；ADMIN 偶尔可自查 `git log --all -p \| grep crsr_` 期望空输出 |

---

## §七 PM 自约束审计（本轮）

| 决策 | 性质 | 处置 |
|---|---|---|
| 接受 DEV-007 P2 全部 5 大成果 + 7 决策点 + 2 surprises (S0+S1) | 常规推荐 | ✅ 自决 |
| 接受 DEV `git checkout -- .env.example` revert 处置 | 常规推荐 | ✅ 自决 — DEV 处置正确 |
| PM 自改 `.env.example` 加 DO NOT EDIT 警告 + 占位符更正 | 文档防御 | ✅ 自决 — 不需 DEV/OPS 时间 |
| 派 OPS-008 双 commit + tag `v0.2.0-beta` 不推 origin | 常规推荐 | ✅ 自决（与 v0.1 + v0.2.0-alpha 同 internal RC 策略）|
| 派 QA-009 含 HARD GATE「严禁 cat .env」安全条款 | 常规推荐 | ✅ 自决 — defense-in-depth |
| **§2.3 选 A vs B**（key 是否吊销）| 资源/成本影响 | ❌ **上交 ADMIN**（默认 A 保守路径）|
| 5/27 公开发布日期不擅自提前到 5/25 | 重大变更 | ✅ 自决保守 — 提前 2 天作为缓冲，对外承诺仍 5/27 |
| **D4 是否扩 DEV-02** | 资源变更 | ❌ 仍上交（仍待 ADMIN）|

→ 6 项自决 + 2 项上交（§2.3 + D4）+ 0 项延后请示，**0 越权**。

---

## §八 一句话送 ADMIN

> 安全事件已闭环（0 泄露 + 防御加固落地）；DEV/OPS 双抢跑让 v0.2 节奏再提前 2 天。
>
> **你今晚唯一关键动作（任选其一）：**
> - **A** = 吊销那条 `crsr_*` key + 重新生成 + 写到 `codeflow-shell/.env`（PM 推荐 — 完全消除残留）
> - **B** = 保留继续用（实际 0 泄露所以可行）
>
> 加上在 OPS / QA cursor session 各打 1 次「巡检 开工」启动 OPS-008 + QA-009。
>
> 路线锁定 5/27 v1.0 公开发布（实际可能 5/25 出，作为 2 天缓冲）。

PM-01
2026-05-10 02:35 (UTC+8)
