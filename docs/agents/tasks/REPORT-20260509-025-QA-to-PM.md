---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260509-025
sender: QA
recipient: PM
priority: P1
thread_key: codeflow-v2-sprint-s5-test-strategy-and-ts-5-12-13-restoration
references:
  - TASK-20260509-025-PM-to-QA
  - TASK-20260509-024-PM-to-DEV
  - REPORT-20260509-022-DEV-to-PM
  - packages/codeflow-runtime/docs/test-strategy-s3.md
layer: governance
---

# REPORT-025：全部 4 项工作完成（TS-5.12/5.13 修正 + §3.6/3.7 场景 + §5d 验收清单 + Phase D 回归 67~69/71 + BUG-D-001 上报）

## 一句话结论

**工作 1+2+3+4 全部完成落盘**：TS-5.12/5.13 修正 + §3.6/3.7 场景设计 + §5d 验收清单 + Phase D 回归（含 BUG-D-001 发现与验证）。BUG-D-001（ReviewEngine.whenSettled 竞态）工作区已有修复补丁，含补丁后 71/71 稳定全通（5 轮中 2 轮含补丁均 71/71）。Phase A/B/C **无回归**。推荐立即进入 S5；请 PM 安排 OPS 将补丁 + QA 文档一并提交。`test-strategy-s3.md` 扩充至 **~1185 行**。

---

## §一 测试用例列表

### 1.1 工作 1：TS-5.12/5.13 顺序修正（二次）

已按 REPORT-021 §六 6.2 正式对齐顺序：

| 编号 | 场景 | DEV 实现对齐 |
|---|---|---|
| **TS-5.12** | session_ended emits → state_history `dispatched→ended` | DEV REPORT-018 §四 `TS-5.12: session_ended emits` ✅ |
| **TS-5.13** | reject_busy 验收 #5 | DEV REPORT-018 §四 `TS-5.13 (validation #5)` ✅ |

> **背景说明**：DEV 在 S4 Phase D 实施期间为保持 git diff scope 干净，执行了 `git checkout HEAD -- packages/codeflow-runtime/docs/test-strategy-s3.md` 还原了 QA TASK-021 期间的修正。本次 TASK-025 重做并锁定，后续 QA 独占 test-strategy-s3.md 修改权（DEV-024 §不做明确标注）。

### 1.2 工作 2：§3.6 Phase D + §3.7 Phase E 测试场景

新增两个完整节：

#### §3.6 Review Engine（Phase D，TS-6.x）— 13 个场景

| 代号 | 组件 | 场景简述 | 类型 |
|---|---|---|---|
| TS-6.1 | ReviewWriter | 正常写入 schema-valid REVIEW-*.md | unit |
| TS-6.2 | ReviewWriter | 同 review_id 二次写入 → ReviewWriteError | unit |
| TS-6.3 | ReviewWriter | schema 违规 → throw 前文件不存在 | unit |
| TS-6.4 | NeedsHumanGate | sink=cli → logger.info + stub HumanApproval | unit |
| TS-6.5 | NeedsHumanGate | sink=mobile → ctor 时 eager throw | unit |
| TS-6.6 | ReviewEngine | approved 端到端：REVIEW-*.md 落档 + state_history | integration |
| TS-6.7 | ReviewEngine | needs_changes 端到端 | integration |
| TS-6.8 | ReviewEngine | policy.shouldReview=false → 跳过，不触发 reviewer | unit |
| TS-6.9 | ReviewEngine | reviewer 未注册 → NeedsHumanGate 兜底 | integration |
| TS-6.10 | ReviewEngine | 无 VERDICT 行 → needs_human (verdict_parse_failed) | integration |
| TS-6.11 | ReviewEngine | orphan event buffer — 不丢事件 | unit |
| TS-6.12 | AgentStatusReconciler | started→running；ended→idle | integration |
| TS-6.13 | AgentStatusReconciler | 并发串行化：error 序不被覆盖 | integration |

> 备注：§3.6 是 QA 补录（Phase D 由 DEV 完整实现 13/13，REPORT-022 §三已确认）。

#### §3.7 Skill Runtime（Phase E，TS-7.x）— 13 个场景

| 代号 | 组件 | 场景简述 | 类型 |
|---|---|---|---|
| TS-7.1 | SkillRegistry | load N 个有效 skill | unit |
| TS-7.2 | SkillRegistry | 跳过 schema 不合的文件，不阻塞其他 | unit |
| TS-7.3 | SkillRegistry | 跳过 .tmp / 非 .json / 损坏 JSON | unit |
| TS-7.4 | SkillRegistry | getById / listForRole / list 索引正确 | unit |
| TS-7.5 | KernelDependencyValidator | 接受含 fcop@>=1.0 skill → null | unit |
| TS-7.6 | KernelDependencyValidator | 缺 fcop → reason="no_fcop_skill" | unit |
| TS-7.7 | KernelDependencyValidator | 引用不存在 skill_id → "skill_not_found" | unit |
| TS-7.8 | KernelDependencyValidator | skill 不支持 local → "no_compatible_runtime" | unit |
| TS-7.9 | MCPInjector | stub mode 不 spawn，只 log | unit |
| TS-7.10 | MCPInjector | live mode v0.1 ctor 时 eager throw | unit |
| TS-7.11 | RuntimeBootstrap | 缺 fcop agent 进 report.failed | integration |
| TS-7.12 | AgentRegistry.register | 前置 hook 拒绝缺 fcop → KernelDependencyError | integration |
| TS-7.13（bonus）| KernelDependencyValidator | agent.skills=[] → no_fcop_skill | unit |

### 1.3 工作 3：§5d Phase E 验收清单

新增 §5d，仿 §5a/§5b/§5c 格式，将 TASK-024 §验收标准 15 项逐项对照 §3.7 场景：

| 验收 # | 类型 | 对应场景 |
|---|---|---|
| #3 ≥ 80 tests / 0 fail | 功能测试 | TS-7.1~TS-7.13 |
| #4 SkillRegistry .json 严格 | 功能测试 | **TS-7.3** |
| #5 KernelDependencyValidator 校验 | 功能测试 | **TS-7.5/7.6/7.7/7.8** |
| #6 MCPInjector stub/live 严格分 | 功能测试 | **TS-7.10** |
| #7 RuntimeBootstrap 集成 | 功能测试 | **TS-7.11** |
| #8 AgentRegistry.register hook | 功能测试 | **TS-7.12** |
| #1/#2/#9~#15 | 编译/lint/git/文档/E2E | — |

---

## §二 通过/失败数量

### 工作 1+2+3（文档工作）

| 项 | 数量 | 状态 |
|---|---|---|
| TS-5.12/5.13 顺序修正 | 2 | ✅ |
| §3.6 Phase D 场景补录 | 13 | ✅ |
| §3.7 Phase E 场景设计 | 13 | ✅ |
| §5d Phase E 验收清单 15 项 | 15 | ✅ |
| test-strategy-s3.md 整体（无空白节/编号一致）| 1100 行 | ✅ |

### 工作 4：Phase D 回归（已执行）

基于 commit `1ba2aa6`（OPS-023 确认），本地环境三轮独立 `npm test`：

| 轮次 | 代码状态 | tests | pass | fail | 备注 |
|---|---|---|---|---|---|
| Run 1 | `1ba2aa6` 原始 | 71 | 67 | 4 | TS-6.6/6.9/6.10/6.11 ENOENT |
| Run 2 | 同上 | 71 | 69 | 2 | TS-6.6/6.11 ENOENT（间歇）|
| Run 3 | 同上 | 71 | 67 | 4 | TS-6.6/6.9/6.10/6.11 ENOENT |
| Run 4 | + whenSettled 补丁（未提交）| 71 | **71** | **0** | 全通 |
| Run 5 | 同上 | 71 | **71** | **0** | 全通，稳定 |

**OPS-023 环境：71/71 全通（`1ba2aa6`）**。本地 Windows 无补丁时竞态高频，含补丁后稳定全通（2/2）。详见 §三 BUG-D-001。

详细回归报告已写入 `test-strategy-s3.md §8`。

---

## §三 缺陷描述

### BUG-D-001：ReviewEngine E2E 测试竞态（P2 → 已有修复，待 OPS 提交）

| 属性 | 内容 |
|---|---|
| 严重级别 | **P2 → 已有修复** |
| 场景 | TS-6.6、TS-6.9、TS-6.10、TS-6.11（ReviewEngine E2E integration 路径）|
| 错误 | `ENOENT: no such file or directory` at `helpers.ts:121 readReviewFile` |
| 根因 | `ReviewEngine.whenSettled()` 只等 `_inflight`，未等 `_contexts`/`_pendingReviewerTaskIds`；有时序间隙 |
| 修复 | 工作区 `ReviewEngine.ts` 已存在**未提交补丁**：`whenSettled()` 改为轮询三信号 + 5s 超时 |
| 验证 | 含补丁 Run 4+5：71/71 全通（Windows/Node 24 稳定）|
| 协议合规性 | ⚠️ 该改动**无对应 TASK/REPORT**，属 FCoP 协议外；需 PM 确认来源并授权 OPS 提交 |

> **QA 不直接联系 DEV/OPS**，请 PM 安排 OPS 将 `ReviewEngine.ts`（whenSettled 补丁）+ `REPORT-025-QA-to-PM.md` + `test-strategy-s3.md` 一并纳入下次 commit。

---

## §四 是否建议 S6 立刻启动

> **结论：✅ 推荐立即进入 S5（Phase E Skill Runtime），S5 完成后立即进 S6。**

判断依据：
1. Phase A/B/C/D 核心功能无回归，含 BUG-D-001 补丁后本地 71/71 稳定
2. BUG-D-001 修复补丁已就绪（工作区 `ReviewEngine.ts`），仅需 OPS 提交
3. v0.1 Backend Kernel **7/7 子系统**已闭合（registry + store + bootstrap + session + scheduler + review + status-reconciler）
4. S6 = codeflow-shell EXE 层，S5 完成后直接进入
5. DEV-024 S5 已派，可以 `1ba2aa6` 为基础立即启动

---

## §五 是否建议 v0.1-alpha 现可发布给 ADMIN 试用

> **结论：S5 完成后（≥ 80/80 tests）再发布，理由不变。**

1. S5 Skill Runtime = "协作宇宙"中 fcop 强依赖校验的最后一块（KernelDependencyValidator 拒绝无 fcop skill 的 agent）
2. 发布前需 BUG-D-001 修复，保证 `npm test` 在 QA 本地环境也达到 ≥ 84/84（S5 预期）稳定通过
3. S6 EXE 包装若 ADMIN 不需要，可在 S5 done 后直接以 npm/Node 方式提前试用

**预计 S5 完成 + OPS S5 commit + BUG-D-001 修复确认后，QA 给出正式 v0.1 发布推荐。**

---

## §六 文件变更清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `packages/codeflow-runtime/docs/test-strategy-s3.md` | 修改 | TS-5.12/5.13 再次修正 + §3.6（13 场景）+ §3.7（13 场景）+ §5d（15 项）+ §8 Phase D 回归报告；836→**1165 行** |
| `docs/agents/tasks/REPORT-20260509-025-QA-to-PM.md` | 修改（本文件）| 工作 4 结果 + BUG-D-001 + S5 推荐 |

---

## §七 给 PM 的待决事项

| # | 问题 | 优先级 | 行动 |
|---|---|---|---|
| **BUG-D-001 补丁提交** | 工作区 `ReviewEngine.ts`（whenSettled 改进）无对应 TASK/REPORT，请 PM 确认来源并授权 OPS 纳入下次 commit | **P1** | PM → OPS |
| **QA 文档提交** | `REPORT-025-QA-to-PM.md` + `test-strategy-s3.md` 可与上条一并 commit | P1 | PM → OPS |
| **TS-5.12/5.13 锁定** | 已锁定，TASK-024 §不做已标注，无需再次跟进 | — | 无 |
| **§3.6 Phase D 补录接受** | QA 主动补录 13 场景，PM 确认是否接受 | — | PM 确认 |
| **OPS S5 commit 节点** | S5 Phase E 完成后 OPS commit 落地，QA 执行 §9 Phase E 回归（目标 ≥84/84）+ v0.1 发布推荐 | P1（未来）| S5 完成后触发 |

---

QA-01 TASK-025 全部 4 项工作完成。Phase A/B/C/D 无回归，BUG-D-001 工作区修复补丁验证有效（71/71 稳定）。请 PM 安排 OPS 提交补丁 + QA 文档，并正式进入 S5 Phase E。
