---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260509-023
sender: PM
recipient: ADMIN
priority: P0
thread_key: codeflow-v2-fcop-1.0-rc-1-upstream-alignment-decision
references:
  - https://github.com/joinwell52-AI/FCoP/issues/2#issuecomment-4412811192
  - https://github.com/joinwell52-AI/FCoP/blob/main/adr/ADR-0015-fcop-1.0-ai-os-protocol-charter.md
  - https://github.com/joinwell52-AI/FCoP/blob/main/adr/ADR-0020-agent-boundary-and-capability.md
  - REPORT-20260509-022-PM-to-ADMIN
  - docs/design/codeflow-v2-on-fcop-sdk.md
  - packages/codeflow-protocol/schemas/agent.schema.json
  - packages/codeflow-protocol/schemas/review.schema.json
layer: governance
---

# 紧急请示：FCoP v1.0 RC.1 已 land — CodeFlow v0.1 protocol 与上游 4 处不兼容，需 ADMIN 拍板 align 策略

> **触发**：ADMIN 5/9 23:01 让 PM 看 FCoP issue #2 第二条 comment（5/9 14:59 由 ADMIN 自己作为 `@joinwell52-AI` FCoP maintainer 发出的官方回复）。
>
> **PM 自约束触发**：本议题**同时触发 4 类「仍请示」**（修改宪法本身 + 架构层变更 + 公开 API breaking change + 跨 sprint 路线变更）→ 按兜底机制「默认按重大处理 → 写请示」。
>
> **§3.3.1 deal flow 已激活**：design doc `§3.3.1 line 1739-1743` 早已锁死「v0.1 实施前在 D:\FCoP 提对应 Issue（layer / risk_level / needs_human 等）→ 等反馈：接受 / 拒绝」的处理路径。**Issue #2 是这条路径的执行；upstream 5/9 14:59 reply 是反馈。** 但 upstream 给的不是「接受」也不是「拒绝」，而是 **deferred**（5 字段中 1 接受升级 + 4 deferred 到 v1.1/v1.2）— 这是 §3.3.1 没有预案的**第三种状态**，需 ADMIN 拍板新分支语义。

---

## §一 一句话结论

**FCoP v1.0 RC.1 已 land + 已 freeze 7 抽象**（agent / boundary / encoding / ipc-envelope / event / failure / review）。**CodeFlow 当前 5 schemas（agent/task/review/session/skill）+ `review.decision: needs_human` + `human_approval` 子结构与 v1.0 不兼容**。但 upstream 的 7 抽象**反而比我们当前 v0.1 更精确兑现 §0.0 第 3 句宪法**——「约束 + 能力 + 状态 + 权限 → 不会崩溃的协作宇宙」。**这不是被动让步，是哲学一致**。

需 ADMIN 拍 5 个议题（每个给 PM 推荐 + 备选），决定 v0.1 是否暂停发布、何时切换到 v1.0 charter、如何回应 upstream 三个问题。

---

## §二 upstream comment 5 个核心事实（5/9 14:59）

| # | 事实 | 影响 |
|---|---|---|
| 1 | **fcop@1.0.0-rc.1 已 land**（branch on main）| protocol surface 已冻结 |
| 2 | **Final 1.0.0 tag 在 5/16 ~ 5/20**（7-11 天后）| 发布窗口锁定 |
| 3 | **v1.0 ship 7 抽象，不是 5 schemas** | 我们 packages/codeflow-protocol/ 设计与 v1.0 不一致 |
| 4 | **5 字段命运**：layer ✅ ship 升级为 Boundary / risk_level + Skill.tools deferred 到 **v1.1+** / needs_human + human_approval deferred 到 **v1.2+** | 我们 v0.1 用了 needs_human + human_approval = **建在 deferred 字段上** |
| 5 | **upstream 推荐 peerDependencies: `fcop>=1.0,<2.0`** | 我们当前还没设 peerDependencies（待 v0.1 发布前定）|

### 2.1 v1.0 实际 ship 的 7 抽象

| # | 抽象 | ADR | Schema | 我们当前对应 |
|---|---|---|---|---|
| 1 | **Agent**（lifecycle + identity + Boundary）| ADR-0015 + 0020 | `agent.schema.json` + `boundary.schema.json` | ✅ agent.schema.json（但 layer 仍是 3 值，未升级 Boundary）|
| 2 | **Encoding**（filename + frontmatter + workspace）| ADR-0021 + 0022 | `encoding.schema.json` | ❌ 我们靠 fcop-mcp tool 隐式约束 |
| 3 | **IPC**（TASK / REPORT / ISSUE / **REVIEW** envelopes）| ADR-0017 | `ipc-envelope.schema.json` + `review.schema.json` | ⚠️ 我们 task.schema.json 形态不同（v1.0 是 envelope shape）|
| 4 | **Event Model**（12 event types + subscribe）| ADR-0018 | `event.schema.json` | ❌ 我们没顶级 event schema（在 RuntimeEvent 类型里）|
| 5 | **Failure & Recovery**（4 failure × 5 recovery）| ADR-0019 | `failure.schema.json` | ❌ 我们没顶级 failure schema（错误类散在各模块）|
| 6 | **Boundary**（capability bundle，⬅ 你 Field 1 generalized）| ADR-0020 | `boundary.schema.json` | ⚠️ 我们只有 `agent.layer` 3 值，缺 10-token can/cannot |
| 7 | **Audit**（REVIEW minimal v1.0 surface）| ADR-0017 | `review.schema.json` | ⚠️ enum 不匹配 + 含 deferred needs_human |

---

## §三 4 处明确不兼容（PM 已实测 grep 验证）

### 3.1 ❌ `review.decision` enum 不匹配

| | 我们当前 | upstream v1.0 |
|---|---|---|
| enum | `["approved", "rejected", "needs_changes", "abstained", "needs_human"]` | `["approved", "changes_requested", "blocked", "rejected"]` |
| `needs_human` 是否合法 | ✅ 是（v0.1 主路径之一）| ❌ 否（**deferred 到 v1.2+**）|
| `needs_changes` vs `changes_requested` | 命名不同 | 命名不同 |
| `blocked` 是否合法 | ❌ 否 | ✅ 是 |
| `abstained` 是否合法 | ✅ 是 | ❌ 否 |

证据：`packages/codeflow-protocol/schemas/review.schema.json:42, 53`。

### 3.2 ❌ `human_approval` 子结构整体 deferred 到 v1.2+

我们 `review.schema.json:58-70` 已 ship `human_approval` 子结构 + allOf 强制约束（`decision=needs_human` 时必填）。

upstream ADR-0013 状态：**Accepted but deferred to v1.2+**（"paused for evidence"）。
upstream 论证（critical）：
> 1. needs_human + human_approval 一起把 Review 变成 god-tier gatekeeper — 与 v1.0「7 平等抽象」哲学冲突
> 2. `human_approval.evidence` 子结构「invented 而非 discovered」— 违反 v1.0 「discovered, not invented」硬规则
> 3. 这些 use cases **可能本质是 Boundary capability check**（Field 1 已 ship 的 generalized form）— 待 v1.1 看证据

### 3.3 ❌ 5 schemas vs 7 schemas

我们：`agent / task / review / session / skill`。
upstream v1.0：`agent / boundary / encoding / ipc-envelope / event / failure / review`。

**没有 task / session / skill 顶级 schema** — 这些是 runtime-internal concepts：
- `task` 是 IPC envelope 的一种（`ipc-envelope.schema.json` 涵盖）
- `session` 是 runtime concept（不进 protocol 层）
- `skill` 在 v1.0 charter 中**不在 protocol 层**（deferred 到 v1.1+ 才进 protocol）

⚠️ 这意味着我们 S5 Phase E 刚 ship 的 SkillRegistry + KernelDependencyValidator + MCPInjector 实现是**正确的（runtime 层）**，但我们的 `skill.schema.json` 文件本身**不该作为 protocol-level schema 存在**——v1.0 不接受。

### 3.4 ⚠️ `agent.layer` 3 值 vs Boundary（10-token can/cannot）

我们：`agent.schema.json:26-30` enum `["worker", "governance", "admin"]`（3 值）。

upstream v1.0 ADR-0020：`layer` + `boundary.schema.json` 的 **10-token `can`/`cannot` capability bundle** + 4 normative rules + `Project.assert_boundary` API + `BOUNDARY_VIOLATED` event。

**这是 superset** — 我们当前 3 值 layer 是 v1.0 Boundary 的一个 dimension。升级路径 = additive。

---

## §四 哲学层关键发现 — upstream Boundary > 我们 needs_human + layer 组合

ADMIN 5/9 13:51 第 3 句宪法：

> 「**5 类 Schema 真正应该变成：**
> **Task Schema = 定义目标与约束 / Agent Schema = 定义能力边界 /**
> **Session Schema = 定义运行上下文 / Review Schema = 定义治理规则 /**
> **Skill Schema = 定义可调用能力。**
> **❌ 不要：定义固定动作。**
> **✅ 而要：定义"约束 + 能力 + 状态 + 权限"，然后让 Agent 自己完成规划 / 协作 / 拆解 / 实现。**」

upstream Boundary 抽象 = **`layer`（权限）+ `can`/`cannot` 10-token bundle（能力）+ `assert_boundary` API + `BOUNDARY_VIOLATED` event（状态 + 约束）**。

→ Boundary **正是第 3 句宪法的精确兑现**。我们当前 v0.1 用 `agent.layer` 3 值 + Review.decision=needs_human 是**两个分散的近似**，upstream Boundary 是**统一的精确表达**。

更进一步，upstream 论证 needs_human 的 use cases「可能本质是 Boundary check」——意思是：

> `db.exec DROP TABLE` → **Boundary 直接拒**（worker.cannot.delete_data），而不是走到 Review 才说"我决定不了"

这是个深刻的协议哲学：**「不会崩溃的协作宇宙」物理定律不是在 Review 层兜底，而是在 Boundary 层物理隔离**。

→ 升级到 v1.0 Boundary **加深第 3 句宪法的工程兑现**，不是被动让步。

---

## §五 5 个决策议题（每议题给 PM 推荐 + 备选 + 影响）

> 因 4 类「仍请示」全触发，**每议题需 ADMIN 显式拍板**。

### 议题 A — v0.1-alpha 是否暂停发布

| 选项 | 内容 | 影响 |
|---|---|---|
| **A.1（PM 推荐）** | **不暂停发布动作；改语义** — v0.1-alpha 完工标准从「PyPI/npm publish」改为「internal RC tag + 完成 S6 EXE bundle 给 ADMIN 试用」。**不**做公开发布 | 距 ~3-5h，不延迟 |
| A.2 | 暂停 — 等 fcop@1.0.0 final（5/16-5/20）+ schema 升级再发 | 延迟 ~7-11 天 + 1 个 sprint 工作量 |
| A.3 | 直接发 v0.1-alpha 到 npm/PyPI，标记 fcop>=0.7.2,<1.0 — 用 upstream 第一条 reply 给的 interim option | 短期可用，但 1-2 周后必须发 v0.2 升级 align v1.0，给试用者带破坏性升级 |

**PM 推荐 A.1 理由**：
- 我们 v0.1 是 **internal preview**（ADMIN + dev-team 自试），从未对外公开承诺 npm/PyPI 发布
- A.1 保留 S6 完工节奏 + 让 ADMIN 真实试用 + 同时给 v0.2 align v1.0 留出 7-11 天 buffer
- A.3 会给未来公开试用者制造 breaking upgrade 痛苦——背离第 3 句宪法「不崩溃的协作宇宙」

### 议题 B — `Review.decision` enum 处置

⚠️ **§3.3.1 严格解读 vs 折中解读**：design doc 原文「拒绝 = v2 必须移除这些字段」 — upstream 把 needs_human + human_approval **deferred 到 v1.2+** 在 v1.0 范围内**等价于拒绝**。严格解读 = **现在就移除**；折中解读 = **保留 v0.1 + 标 deprecation + v0.2 移除**。

| 选项 | 内容 | 影响 |
|---|---|---|
| B.0 | **§3.3.1 严格解读** — 立刻删 `needs_human` enum + `human_approval` 子结构 + 整套 NeedsHumanGate 实现 + Phase D 相关 4 测试 | ~4-6h 重构 + 失去 Phase D「governance loop closure」演示项 |
| **B.1（PM 推荐 — 折中解读）** | **保留当前 v0.1 enum 不动**（含 `needs_human` + `abstained` + `needs_changes`）+ 标明「v0.1 internal preview enum，v0.2 align v1.0 charter」+ 写 deprecation note | 0 工作量，commit 历史可追 |
| B.2 | 立刻调 enum 为 v1.0 形状 `["approved", "changes_requested", "blocked", "rejected"]` + 保留 needs_human 路径但改 enum 名 | ~3-4h 重构 + 11 测试改写 |
| B.3 | 双 enum 并存 — v0.1 路径 + v1.0 兼容路径，runtime 自动 translate | 复杂度爆炸，不推荐 |

**PM 推荐 B.1 理由**：
- v0.1 internal preview，enum 形状不影响 ADMIN 试用功能
- B.0（严格解读）虽符合 §3.3.1 字面，但**意外代价大**：删 NeedsHumanGate = 失去 §0.0 第 4 句宪法（dispatch / **review** / escalate）的工程展示项 — 这是 v0.1 内部演示给 ADMIN 看的核心闭环
- B.2 工作量大但收益小（v0.2 还要再调）
- 折中 B.1：**保留 v0.1 NeedsHumanGate + enum 不动**，标 deprecated note；v0.2 sprint 0 整体 align 时改 Boundary check —— 既保留 v0.1 演示价值，也尊重 §3.3.1 deal flow 锁定的「最终必须 align」语义

⚠️ **如果 ADMIN 严格解读 §3.3.1**（拒绝 = 必须移除）→ 选 B.0，PM 立即派单删 NeedsHumanGate。这是 ADMIN 的判定权，PM 不强推 B.1。

### 议题 C — 5 schemas → 7 schemas 切换时机

| 选项 | 内容 | 影响 |
|---|---|---|
| **C.1（PM 推荐）** | **v0.1 不动，v0.2 sprint 0 全量 align v1.0** — 把 packages/codeflow-protocol/ 重构为 mirror upstream v1.0 7 schemas | 集中 1 个 sprint 完成，~1 周工作量 |
| C.2 | 立刻在 v0.1 加 boundary / encoding / ipc-envelope / event / failure 5 个新 schema | ~2-3 天 + 推迟 v0.1 internal RC |
| C.3 | 逐 sprint 渐进切（每 sprint 加 1-2 schema）| schema 半新半旧，最难维护 |

**PM 推荐 C.1 理由**：
- 最干净 — v0.1 = 5 schemas era 终点；v0.2 = 7 schemas era 起点
- 工作量集中 + 上下文一致
- v0.2 同时升级 Boundary + 删 needs_human + 转 v1.0 charter，一气呵成

### 议题 D — `agent.layer` 升级 Boundary 的时机

| 选项 | 内容 | 影响 |
|---|---|---|
| **D.1（PM 推荐）** | **v0.2 一起做**（同 C.1）— v0.1 保留 3 值 layer | 0 工作量 v0.1 |
| D.2 | v0.1 立刻加 `boundary.schema.json` + 10-token can/cannot bundle | ~2-3h + 8 测试改写 |

**PM 推荐 D.1 理由**：同 C.1，v0.2 集中 align。

### 议题 E — 是否在 issue #2 回应 upstream 3 个问题

upstream 3 个问题：
1. Boundary 是否覆盖 worker/governance/admin + 10-token can/cannot 的需求？
2. 接受 `>=1.0,<2.0` 的 pin 推荐吗？
3. 愿意为 Fields 3+4 v1.2 提供 field evidence 吗？

| 选项 | 内容 |
|---|---|
| **E.1（PM 推荐）** | **PM 起草 reply 草稿 → ADMIN 审 → ADMIN 用 `@joinwell52-AI` 身份 post**。Q1 Yes（Boundary 满足）/ Q2 Yes 改成 v0.2 起锁 `>=1.0,<2.0` / Q3 Yes 等 v0.2 跑出实证后回报 |
| E.2 | ADMIN 自己直接 reply（不需要 PM 介入）| 最快 |
| E.3 | 暂不回应，先做 v0.1 internal RC | upstream 等待 |

**PM 推荐 E.1 理由**：保证 reply 与 CodeFlow side 决策一致 + 给 ADMIN 留最终 wording 权。

---

## §六 当前 OPS-026 / QA-027 处置

### PM 自决：**不 hold OPS-026 + QA-027**

理由：
- OPS-026 commit 内容**不会让情况变糟** — 它把现有 5-schema 设计扩展到 S5（fcop 强依赖闸 + KernelDependencyValidator）。fcop 强依赖语义**完全 align** v1.0 charter（v1.0 第 1 抽象 = Agent + Boundary，含 fcop 元能力）
- QA-027 跑回归测试 — 只是验证现有代码，不引入新设计
- v0.2 的 schema 升级独立于 S5 commit，不会 conflict

**待 OPS-026 完成后**，根据 ADMIN 拍 §五议题决定：
- 如 A.1 + C.1（PM 推荐）：S6 codeflow-shell EXE 包装继续 — 距 v0.1 internal RC ~3-5h
- 如 A.2：暂停 S6，立刻起 v0.2 schema 升级 sprint

---

## §七 时间表对比

### 方案 X：PM 推荐路径（A.1 + B.1 + C.1 + D.1 + E.1）

```
现在 → ~10 min   OPS-026 commit S5 + push origin/backup
~10 min → ~2h     QA-027 回归 + 双推荐
~2h → ~5h         S6 codeflow-shell EXE bundle + Hello World demo
~5h               v0.1 internal RC tag（不 publish）+ ADMIN 试用
~5h               PM 草拟 issue #2 reply → ADMIN 审 + post
~5h → ~1 周       ADMIN 试用 v0.1 internal RC（同时 fcop@1.0.0 final 5/16-5/20 落地）
~1-2 周           v0.2 sprint 0 启动：5 → 7 schemas + Boundary + enum align v1.0 + 删 NeedsHumanGate（转 Boundary check）
~3 周             v0.2 alpha — align v1.0，发 npm/PyPI 公开试用
```

### 方案 Y：A.2 暂停发布

```
现在 → ~10 min   OPS-026 commit S5
~10 min → ~5h    S6 EXE 包装继续（不浪费）
~5h → 5/20       等 fcop@1.0.0 final（~7-11 天）
5/20 → 5/27      v0.2 schema 升级
5/27             v0.1+v0.2 合并发布 align v1.0
```

→ 方案 X 比方案 Y 少**~1 周**+ 让 ADMIN 早 1 周试用 + 给 v0.2 留出 align 缓冲。

---

## §八 §0.0 宪法是否需要改

**不需要改**。5 句宪法（身份 + 定位 + 协议哲学 + 治理三动作 + 永久授权）全部与 v1.0 charter **同向**。

但**§0.0 的「解读表」**可能需要在 v0.2 sprint 0 时加一行：

```
| 「应用 fcop-mcp」 | 角色 = consumer / downstream → §8.0 硬规则 #5（只消费、不生产）
                    → v0.2 切换到 fcop@>=1.0,<2.0（v1.0 charter align） |
```

这一行不动 ADMIN 原话，只在解读表内部追加 v0.2 align 路径。

---

## §九 ADMIN 决策模板（5 个议题，请逐项拍）

```
A 议题（v0.1-alpha 发布）：A.1 / A.2 / A.3              PM 推荐 = A.1
B 议题（review.decision enum）：B.0 / B.1 / B.2 / B.3    PM 推荐 = B.1（B.0 = §3.3.1 严格解读分支）
C 议题（5→7 schemas 切换时机）：C.1 / C.2 / C.3          PM 推荐 = C.1
D 议题（agent.layer 升级 Boundary）：D.1 / D.2          PM 推荐 = D.1
E 议题（issue #2 回应方式）：E.1 / E.2 / E.3            PM 推荐 = E.1
```

或者按第 5 句宪法直接「**全按推荐**」。

如果 ADMIN 选「全按推荐」，PM 立刻：
1. 不 hold OPS-026 / QA-027
2. S6 完工后写 v0.1 internal RC tag（不 publish）
3. PM 起草 issue #2 reply 草稿（在另一份 REPORT 里）→ 等 ADMIN 审
4. v0.2 sprint 0 = 5→7 schemas + Boundary + 删 NeedsHumanGate + align v1.0 charter 全套（约 1 周工作量）

---

## §十 PM 自约束声明

本议题虽涉及 **4 类「仍请示」全触发**（修改宪法 + 架构变更 + 公开 API breaking + 跨 sprint 路线变更），但 PM 推荐**最小化打扰** —— 全按推荐 = ADMIN 一个字「按推荐」即可激活整套路径。

**仅在 ADMIN 选 A.2 / A.3 / B.2 / C.2 / C.3 / D.2 时，PM 才会回头确认细节**。

---

PM-01 紧急请示。状态：S5 已完工 + OPS-026 + QA-027 在跑（不 hold）+ S6 待 ADMIN 拍 §五议题后定路径 + issue #2 reply 待草拟。
