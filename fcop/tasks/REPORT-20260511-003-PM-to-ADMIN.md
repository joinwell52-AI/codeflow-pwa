---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260511-003
sender: PM
recipient: ADMIN
priority: P0
thread_key: codeflow-p4-day-4-and-layout-migration-double-landing
references:
  - REPORT-20260511-002-PM-to-ADMIN
  - REPORT-20260511-014-OPS-to-PM
  - REPORT-20260511-015-OPS-to-PM
  - REPORT-20260511-007-DEV-to-PM
  - TASK-20260511-013-PM-to-DEV
  - TASK-20260511-014-PM-to-OPS
  - TASK-20260511-015-PM-to-OPS
layer: governance
---

# REPORT: P4 Day 4 + Layout Migration 双落地 + PM 第 16/17 次错误自披露 + v0.3.0-alpha 出厂条件评估

## §0 TL;DR（30 秒）

| 维度 | 数据 |
|---|---|
| **P4 sprint 进度** | Day 4/6 完工 + **layout migration 提前落地**（5/11 15:41 commit `c650c39`） |
| **Day 4 节奏** | DEV-013 ~14min vs SLA 1d = **34x 加速** |
| **Migration 节奏** | OPS-015 ~11min vs SLA 1.5-3.5h = **8-19x 加速** |
| **运行测试** | `141/141 pass / 0 fail`（runtime workspace），3 workspace `tsc --noEmit` 全 exit 0 |
| **fcop bridge** | TaskParser + ReviewWriter + NeedsHumanGate + InboxWatcher 四件套已全部 wire 完成 |
| **协作路径** | CodeFlow 协作 workspace 已对齐 fcop@1.1.0 默认布局 `fcop/`，**0 deprecation warning**（走 v1 默认）|
| **PM 错误自披露累计** | 17 次（本次 +2：#16 不存在的 `fcop migrate` CLI / #17 状态心智滞后 58min）|
| **v0.3.0-alpha 出厂可能** | **5/12 EOD 高可能性**（vs 原 5/17-5/18 EOD 提前 5-6 天），PM **不承诺** |
| **本次新增 ADMIN 决策点** | 无新 D，仅请示后续 OPS-016 commit / DEV-016 Day 5 派单时机 |

---

## §1 Day 4 完工事实

### 1.1 DEV-013 实际交付

**SLA 对比**：

```
PM SLA      : 1 工作日（8h）
实际完工    : ~14min（DEV-013 派单 14:57 → 代码落地 ~15:11）
加速倍率    : 34x（P4 sprint 至今最高）
```

**核心交付物**（commit `9506a91 feat(p4-day4)`）：

1. `InboxWatcher` 接入 `fcopClient.inspectTask()` schema 校验（带 `onValidationFail` 策略：reject / needs_human_review / dispatch_anyway 三选一）
2. `FcopClientError` fallback 路径（fcop 降级时 InboxWatcher 不阻塞，回退到 Day-1 pass-through）
3. `Runtime` 注入扩展到 `InboxWatcher`（继 Day 2 TaskParser、Day 3 ReviewWriter+NeedsHumanGate 之后第 4 件）
4. `docs/releases/v0.3.0-alpha.md` release notes baseline 首版（DEV 自决「§三 C 路径」抢跑）
5. 测试 +5：runtime 136 → **141 pass**（新增 InboxWatcher.test.ts 5 tests：TS-IW-D4-1/2/3/3b/4）

### 1.2 PM 第 15 次错误自披露的正面回报

5/11 15:00 PM 派 TASK-013 前用「第 9 条自约束 path 版三件套」拦截发现 `fcop.Project.list_agents` 不存在 → **主动撤回 Day 4.1 AgentRegistry 改造**，把 Day 4 范围收窄到 InboxWatcher。

**效果**：
- 节省 DEV 一个工作日（不为 PM 架构错买单）
- 派单文档自带 PM 透明认错段，DEV 信任度 ↑
- 自约束 9 从「事后认错」首次演化到「事前拦截」— **优秀样本入 emergence-log §3**

---

## §2 Layout Migration 落地事实

### 2.1 ADMIN 战略 pivot 时间线

| 时间 | 事件 |
|---|---|
| 5/11 11:09 | DEV-005 spike §S8 证 `workspace_dir="docs/agents"` 参数 PASS → PM 推荐「迁移可推迟到 P5+」 |
| 5/11 15:08 | ADMIN「fcop 不是把 docs 改成 fcop 了？怎么平移？」战略 pivot 信号 |
| 5/11 15:12 | ADMIN「如果是新的项目，就不会是 docs 了；如果现在手工把 docs 改成 fcop 呢？」一致性原则压过 0 成本短期收益 |
| 5/11 15:19 | ADMIN「你先巡检，然后决定什么时候迁移！」**授权 PM 自决** |
| 5/11 15:30 | PM 派 TASK-014 + TASK-015（OPS 自决今晚 vs 明早，截止 5/12 EOD）|
| **5/11 15:41** | **OPS-015 落 commit `c650c39`**（11 分钟完工，全过 10 项 Safety HARD GATE）|
| 5/11 16:43 | ADMIN 戳破 PM 状态心智滞后 → PM 实测 + REPORT-003 |

### 2.2 OPS-015 commit `c650c39` 验证矩阵

| # | 验证项 | 结果 |
|---|---|---|
| 1 | git mv `docs/agents` → `fcop/` | 258 files / 6273+ insertions / 229 deletions |
| 2 | Cursor key `crsr_[0-9a-f]{16,}` 扫描 | 0 match |
| 3 | ck_ / sk- / GitHub / AWS key 扫描 | 0 match |
| 4 | 物理校验 `Test-Path fcop/tasks` / `docs/agents` | True / False |
| 5 | `git ls-files fcop` / `docs/agents` 计数 | 197 / 0 |
| 6 | Runtime tests | **141 pass / 0 fail** |
| 7 | TypeScript 3 workspaces `tsc --noEmit` | all exit 0 |
| 8 | Smoke A（yaml fallback / `CODEFLOW_SKIP_FCOP_PROBE=1`）| ✅ pass |
| 9 | Smoke B（real fcop / `PYTHON_BIN`）| ✅ pass |
| 10 | origin / backup hash 对账 | both MATCH at `c650c39a4...` |
| 11 | gitee 隔离（仍 G3 `62532a7...`，未污染） | ✅ |
| 12 | 未打 / 未推 `v0.3*` tag | ✅（按 PM 指令） |

### 2.3 代码侧关键改动

`codeflow-shell/src/main.ts:281` 现在的 fcop 客户端构造调用：

```281:285:codeflow-shell/src/main.ts
fcopClient = await FcopProjectClient.create({
  projectRoot: process.cwd(),
  ensureInitialized: false,
});
```

**没有 `workspaceDir` 参数** → fcop `_resolve_workspace_root` 走「v1 默认分支」→ 0 deprecation warning。

这就是 ADMIN 实测「**运行也没有收到警告啊**」的源码级解释：

```python
# fcop@1.1.0 _resolve_workspace_root 源码片段
if v1_exists:                              # ← <root>/fcop/ 存在 → 当前命中
    return v1_root, "v1"                   #    返回，不发警告
if legacy_exists:                          # ← 只有 docs/agents/ 存在才走这条
    warnings.warn(... DeprecationWarning)  #    才发警告
```

**结论**：迁移已落地 → CodeFlow 现在走「合法 v1 默认路径」→ 0 警告是设计正确，不是 bug。

---

## §3 PM 错误自披露 #16 + #17

### 3.1 第 16 次错误：不存在的 `fcop migrate-workspace` CLI

**事实**：
- PM 内部 TODO `wait-admin-d6-workspace-migration` 多次提及「fcop migrate-workspace CLI 使用时点」
- 5/11 15:08 ADMIN 战略 pivot 后，PM 用 path 版三件套 ripgrep + `inspect.signature(fcop.Project)` 核验 → **fcop@1.1.0 无此 CLI / API**
- 仅有 `workspace_dir` 构造参数

**拦截结果**：
- 派 TASK-015 时采用 `git mv` 物理迁移方案（OPS 执行），未派任何依赖不存在 CLI 的子任务
- **派单前三件套首次拦截连续 2 个 sprint 错误**（#15 list_agents + #16 migrate CLI）

### 3.2 第 17 次错误：状态心智滞后 58 分钟

**事实链**：

| 时间 | 事件 | PM 心智 |
|---|---|---|
| 5/11 15:30 | PM 派 TASK-014 + TASK-015，口径「OPS 自决今晚 vs 明早」 | 已派 |
| 5/11 15:41 | OPS 落 commit `c650c39`（11min 完工，没主动通知 PM）| 仍认为「OPS 自决中」 |
| 5/11 15:41 ~ 16:43 | **58 分钟巡检空窗**，PM 未 `git log` 核对 | 心智仍停在「等」 |
| 5/11 16:43 | ADMIN「但是运行也没有收到警告啊」 | **被戳破** → 立即实测 |
| 5/11 16:50 | PM 实测确认 + 写 REPORT-003 | 状态修正 |

**根因**：PM 派完 TASK-015 后，把「巡检」职责隐式推给了「OPS 主动汇报」— 但 Charter 1「不能在脑子里说话」**反向也成立**：PM 不能假定 agent 会主动跟上文件落地节奏。

**沉淀（已入 emergence-log）**：
- **自约束 9.1（path 派单后版）诞生**：派 TASK 之后亦须周期性 `git log` + `git status` 双核对，commit 落地与 REPORT 落地缺一即「未完工」。
- **给下一任 PM §6 + §7 新增**：巡检责任不可外推；ADMIN 提问视为「巡检漏的报警器」，立即实测验证。

### 3.3 错误模式归纳更新

17 次错误中：

- **10 次「path/API/参数」类**（#6/8/9/10/11/12/13/14/15/16）— 第 9 条 path 版三件套覆盖
- **7 次「判断/流程/战略/巡检节奏」类**（#1/2/3/4/5/7/17）— Charter 5/6 + 自约束 5/7/9.1/10 覆盖

**优秀样本**：#15 / #16 是「派单前三件套」首次连续 2 次主动拦截。
**反面样本**：#17 是「派单后三件套」缺位代价，催生 9.1 扩展。

---

## §4 v0.3.0-alpha 出厂条件评估

### 4.1 出厂条件矩阵（截至 5/11 16:50）

| 条件 | 标准 | 当前状态 | 是否满足 |
|---|---|---|---|
| C1 P4 sprint Day 1-4 完工 | TaskParser + ReviewWriter + NeedsHumanGate + InboxWatcher 全部 wire 走 fcop | ✅ Day 4 commit `9506a91` 已落 | ✅ |
| C2 Layout 对齐 fcop 默认 | docs/agents → fcop/ | ✅ commit `c650c39` 已落 | ✅ |
| C3 测试矩阵全绿 | 141 tests / 3 workspace tsc 0 错 / 2 smoke | ✅ OPS-015 §五全过 | ✅ |
| C4 Safety HARD GATE | 10 项（精确正则）| ✅ OPS-014 + OPS-015 双重通过 | ✅ |
| C5 Schema 清理（Day 5）| 删除 v0.1 自有 task/review/agent 5 schemas | ❌ 未启动 | ❌ |
| C6 全量回归 smoke + release notes 完稿（Day 6）| baseline + 完整测试矩阵 | ⚠️ baseline 已 ship（DEV §三 C），Day 6 全量回归未跑 | ⚠️ 部分 |
| C7 OPS-015 REPORT commit | REPORT-015 文件落地（已写，仅 untracked）| ⚠️ 文件已就，待 OPS-016 commit | ⚠️ |
| C8 emergence-log §3 入档 17 次 | 含 #15/16/17 + 9.1 自约束 | ✅ 本会话刚完成 | ✅ |

**4/8 已满足，2/8 部分满足，2/8 未启动**。

### 4.2 距离 v0.3.0-alpha 出厂的最短路径

```
当前 ───────────────────────────────► v0.3.0-alpha ship
 │                                        │
 ├─ Step 1: OPS-016 commit                │
 │   含 REPORT-015 + emergence-log + REPORT-003
 │   预期 SLA: 5-10min
 │
 ├─ Step 2: DEV-016 Day 5 (schema 清理)    │
 │   删 v0.1 自有 schema 类型 + 重构 import
 │   预期 SLA: 1-3h（参考 Day 3/4 节奏 8-30x 加速）
 │
 ├─ Step 3: DEV-017 Day 6 (全量回归)      │
 │   smoke 3 模式 + release notes 完稿 + tag baseline
 │   预期 SLA: 1-3h
 │
 ├─ Step 4: OPS-017 final commit + tag     │
 │   commit + tag v0.3.0-alpha（不推 origin）
 │   预期 SLA: 10-15min
 │
 └─ Step 5: QA 验收（可选）                │
     2 模式 smoke + release notes 复核
     预期 SLA: 30-60min
```

**乐观估算**：Step 1-5 累计 ~3-6h 真实工时。若 Day 3-4 的 30x 加速节奏延续 → **5/12 EOD 出厂可能性 ≥ 70%**。

**保守估算**：若 Day 5 schema 清理触发大量 import 重写 / 测试调整 → 可能跨日，**5/13 EOD 出厂可能性 ≥ 90%**。

**PM 不承诺**（自约束 10）— 数据观察记录。

### 4.3 节奏过快的风险信号

emergence-log §9 已记录：DEV-011 (28x) / DEV-013 (34x) / OPS-015 (8-19x) 异常加速，**警示**「为了快放松了测试覆盖」需 Day 5/6 全量回归验证。

PM 建议 Day 6 全量回归 smoke 不再压缩 SLA，**至少留 30min 真实运行时间**而非加速。

---

## §5 投资矩阵 — P4 sprint 至今

| Phase | 计划 | 实际 | 加速 |
|---|---|---|---|
| DEV-005 spike | 4-6h | 30min | **8-12x** |
| DEV-007 Day 1 | 4-8h | 38min | **8-16x** |
| OPS-008 Day 1 commit | 10-15min | 3min | **3-5x** |
| DEV-009 Day 2 | 12-14h | 80min | **9-10x** |
| OPS-010 Day 2 commit | 5-10min | 4min | **1.25-2.5x** |
| DEV-011 Day 3 | 12-14h | 30min | **24-28x** |
| OPS-012 Day 3 commit | 5-10min | 3min | **1.7-3.3x** |
| DEV-013 Day 4 | 8h | 14min | **34x** |
| OPS-014 Day 4 commit | 5-10min | ~5min | **1-2x** |
| OPS-015 layout migration | 1.5-3.5h | 11min | **8-19x** |
| **P4 整 sprint 至今** | ~4 工作日（32h）| ~200min ≈ 3.3h | **~9-12x 整体** |

vs 原 PM SLA 6 工作日（48h） → **预测剩余 Day 5+6 仅需 2-6h 真实工时**。

---

## §6 待 ADMIN 决策点（本次新增 0 / 历史未结 3）

### 6.1 本次新增

**无**。OPS-015 layout migration 是 ADMIN 5/11 15:19 已授权 PM 自决执行，已落地。

### 6.2 历史未结（仅本期相关）

| # | 决策 | 截止 | 默认 |
|---|---|---|---|
| D8 | PWA Mobile 与 fcop 写关系（Charter 6 升级解读：PWA = FCoP 在 mobile 上的视图层）| P3 启动前（5/19 前）| 等 ADMIN |
| D9 | codeflow-pwa Dependabot 12 vulns（8 high / 3 moderate / 1 low）| 5/15 前 | 等 ADMIN，与战略转向后 PWA 重写决策合并评估 |
| **issue#2** | DRAFT-20260511-001-PM-to-ADMIN-issue-2-reply-v2.md 选项 a-f | 无强截止 | PM 推荐 a 主版（可选 c 意译战略指令） |

---

## §7 PM 当前推荐下一步

| # | 动作 | 谁 | SLA | 优先级 |
|---|---|---|---|---|
| 1 | OPS-016 commit（REPORT-015 + emergence-log 增量 + 本份 REPORT-003 + 其他文档增量）| OPS | 5-10min | **P0** |
| 2 | DEV-016 Day 5 派单（schema 清理）| DEV | 1-3h 实际 | **P0** |
| 3 | （可选）OPS-016 完工后 DEV-016 派单 — 串行避免 git 冲突 | — | — | — |

**推荐**：1+2 串行，OPS-016 先 commit 锁定状态 → 再派 DEV-016 启动 Day 5（避免 DEV 在 untracked 文件上工作时 OPS commit 误带）。

**需要 ADMIN**：
- **手动通知** OPS 跑动作 1（agent shells 仍需手动叮当门铃，Self-Constraint 10 仍生效）
- 一句「按推荐」即可启动整条链路（OPS-016 → DEV-016 → ... → v0.3.0-alpha ship）

---

## §8 一句话

P4 sprint Day 4 完工 + layout migration 落地 + PM 第 16/17 次错误自披露 + 自约束 9.1（path 派单后版）入档；v0.3.0-alpha 5/12 EOD 高可能性出厂（PM 不承诺）；ADMIN 一句问话戳破 PM 58min 巡检空窗，沉淀为 PM 与 ADMIN 协作的新「桥头守望」机制。

— **PM-01**, 5/11 16:54
