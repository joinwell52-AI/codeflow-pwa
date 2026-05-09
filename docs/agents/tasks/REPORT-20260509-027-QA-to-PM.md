---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260509-027
sender: QA
recipient: PM
priority: P0
thread_key: codeflow-v2-sprint-s5-phase-e-regression-and-release-recommendation
references:
  - TASK-20260509-027-PM-to-QA
  - REPORT-20260509-024-DEV-to-PM
  - TASK-20260509-026-PM-to-OPS
  - REPORT-20260509-025-QA-to-PM
  - packages/codeflow-runtime/docs/test-strategy-s3.md
layer: governance
---

# REPORT-027：S5 Phase E 回归全通 + v0.1-alpha 发布推荐 + S6 进入推荐

## 一句话结论

**94/94 全通，30x 0 flaky，v0.1 6 项硬约束全满足。QA 正式推荐 v0.1-alpha 发布（npm/Node 方式）+ 立即进入 S6。BUG-D-001 已随 S5 commit 修复关闭。**

---

## §一 测试执行结果

### 1.1 单次 94/94

| 项 | 值 |
|---|---|
| 版本 | `@codeflow/runtime@0.1.0-alpha.5` |
| 基准 | `1ba2aa6`（S4 done）+ S5 Phase E staged（OPS-026）|
| 结果 | **tests 94 / pass 94 / fail 0** |
| 耗时 | ~6058ms |

### 1.2 30x 稳定性验证

```
=== 30x: pass=30 / fail=0 ===
（所有 30 轮 ℹ fail 0，零 flaky）
```

**本地 Windows/Node 24 稳定，与 DEV REPORT-024 "30x 0 flaky" 结果一致。**

### 1.3 分层统计

| 阶段 | 测试数 | 结论 |
|---|---|---|
| Phase A（AgentRegistry / PersistentStore / Bootstrap）| 18 | ✅ 无回归 |
| Phase B（SessionManager / SessionStore / TranscriptWriter）| 22 | ✅ 无回归 |
| Phase C（InboxWatcher / TaskParser / StateHistoryWriter / TaskDispatcher）| 14 | ✅ 无回归 |
| Phase D（ReviewEngine / ReviewWriter / NeedsHumanGate / AgentStatusReconciler）| 13 | ✅ **BUG-D-001 已修复，全稳定** |
| Phase E（SkillRegistry / KernelDependencyValidator / MCPInjector + hooks）| **17** | ✅ 全通（13 指定 + 4 bonus）|
| cross-phase sanity | 10 | ✅ 全通 |
| **合计** | **94** | **✅ 94/94** |

---

## §二 Phase E TS-7.x 逐项确认

| 代号 | 场景 | 状态 |
|---|---|---|
| TS-7.1 | SkillRegistry load N valid skills | ✅ |
| TS-7.2 | schema-invalid skill → skipped，其他正常 | ✅ |
| TS-7.3 | tolerant-read：.tmp / 非.json / 损坏 JSON 跳过 | ✅ |
| TS-7.4 | getById / listForRole / list 索引一致 | ✅ |
| TS-7.5 | 含 fcop@>=1.0 skill → null（无错）| ✅ |
| TS-7.6 | 缺 fcop → `no_fcop_skill` | ✅ |
| TS-7.7 | 引用不存在 skill_id → `skill_not_found` | ✅ |
| TS-7.8 | skill 不支持 local → `no_compatible_runtime` | ✅ |
| TS-7.9 | MCPInjector stub mode → 只 log，不 spawn | ✅ |
| TS-7.10 | live mode v0.1 ctor → eager throw | ✅ |
| TS-7.11 | RuntimeBootstrap 缺 fcop agent → `report.kernel_failures[]` | ✅ |
| TS-7.12 | AgentRegistry.register pre-hook → `KernelDependencyError` + SDK/store 未写 | ✅ |
| TS-7.13（bonus）| agent.skills=[] → `no_fcop_skill` fast path | ✅ |
| bonus-1 | SkillRegistry re-load 幂等 | ✅ |
| bonus-2 | SkillRegistry missing dir → 返回空 | ✅ |
| bonus-3 | MCPInjector mount：skill_id 不在 registry → warn + skip | ✅ |
| bonus-4 | KernelValidator validateAll 聚合多失败 | ✅ |

**17/17 全通（含 4 bonus，远超 PM 要求的 ≥13）。**

---

## §三 缺陷状态

| 缺陷 | 状态 | 详情 |
|---|---|---|
| BUG-D-001（ReviewEngine.whenSettled 竞态）| ✅ **已修复关闭** | `whenSettled()` loop-poll 修复随 S5 Phase E commit（OPS-026）纳入；Phase D 13 项本轮 30x 全稳定通过 |

**本次回归 0 新缺陷。**

---

## §四 v0.1-alpha 发布前置检查（6 项硬约束）

| # | 硬约束 | 状态 | 验证 |
|---|---|---|---|
| 1 | 无 UI（npm/Node lib 模式 + cli stdout）| ✅ | Runtime.create + E2E demo stdout |
| 2 | 状态全文件化（agents.json + sessions/*.json + reviews/*.md + transcripts/*.md + state_history append-only）| ✅ | Phase A/B/C/D 测试覆盖 |
| 3 | 崩溃自修复（RuntimeBootstrap reconcile loop）| ✅ | TS-2.1~2.8 |
| 4 | 每任务有 reviewer（ReviewEngine governance loop）| ✅ | TS-6.6~6.13 |
| 5 | 全本地（no cloud agent，MCPInjector live=eager throw）| ✅ | TS-7.10 |
| 6 | fcop-mcp 强绑定（KernelDependencyValidator + `required_kernel.contains: "^fcop@.+"`）| ✅ | TS-7.5~7.13 |

**6/6 全满足。**

---

## §五 双推荐

### 5.1 v0.1-alpha 发布推荐

> ✅ **QA 正式推荐发布 v0.1-alpha（npm/Node 方式）**

前提条件已全部满足：
- 94/94 测试通过，30x 0 flaky
- 6 项 v0.1 硬约束 6/6 满足
- BUG-D-001 已修复
- v0.1 Backend Kernel **14 子系统全部闭合**（Registry + Store + Bootstrap + Session + Scheduler + Review + StatusReconciler + SkillRuntime）

**发布方式**：npm/Node 直接使用（`import { Runtime } from '@codeflow/runtime'`），无需等待 S6 EXE 包装。若 ADMIN 只需 npm 方式试用，可立即进行。

**版本**：`@codeflow/runtime@0.1.0-alpha.5`

**待 ADMIN 确认的前置**：
- 仅需 Node ≥ 20（推荐 v24）
- `npm install @codeflow/runtime`（待 PyPI 等价）
- 参考 `examples/hello-world.ts`

> ⚠️ 注意：v0.1-alpha 仍为 alpha 阶段；`MCPInjector live` 模式和 `NeedsHumanGate mobile` sink 为 v0.2 预留（ctor eager throw）。ADMIN 试用时请使用 `mode="stub"`。

### 5.2 S6 codeflow-shell 进入推荐

> ✅ **QA 推荐立即进入 S6 codeflow-shell**

S6 = `Runtime.create` + `SIGTERM/SIGINT` 钩子 + Node SEA bundle，DEV-022 §九规划明确。`Runtime.ts` 已 self-contained，无接口改动需求。

**建议 S6 交付物**：
- `codeflow-shell` CLI：`codeflow start --persist-dir <path>`
- Node SEA 单文件可执行（Windows/macOS/Linux）
- ADMIN 无需 Node 环境即可运行

---

## §六 文件变更清单（本次 QA 产出）

| 文件 | 操作 | 说明 |
|---|---|---|
| `packages/codeflow-runtime/docs/test-strategy-s3.md` | 修改 | §8 BUG-D-001 状态更新为已关闭 + §8.6 更新 + **§9 Phase E 完整回归报告**（~100 行）|
| `docs/agents/tasks/REPORT-20260509-027-QA-to-PM.md` | 新建 | 本文件 |

**commit 路径（选项 A）**：QA 不自行 commit，以上两个文件由 PM → OPS 纳入下次 commit（建议与 OPS-026 同批，或单独 `docs(qa-s5): test-strategy §9 + REPORT-027` commit）。

---

## §七 给 PM 的行动项

| # | 行动 | 优先级 |
|---|---|---|
| **v0.1-alpha 发布决策** | QA 推荐发布，最终发布时间由 PM/ADMIN 决定（npm publish / GitHub Release）| P0 |
| **S6 任务派发** | 建议 TASK-20260509-028-PM-to-DEV（codeflow-shell + Node SEA bundle）| P1 |
| **QA 文档 commit** | `test-strategy-s3.md` + `REPORT-027` → PM → OPS 纳入 commit | P1 |
| **REPORT-025 BUG-D-001 回收** | REPORT-025 中的 BUG-D-001 已关闭，PM 知悉即可 | — |

---

QA-01 TASK-027 全部工作完成。94/94 + 30x 0 flaky + 6/6 硬约束，v0.1-alpha 正式推荐发布，S6 正式推荐启动。
