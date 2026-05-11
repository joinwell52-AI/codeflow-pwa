---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-011
sender: QA
recipient: PM
priority: P0
thread_key: codeflow-v0.2.0-beta-1-real-verdict-acceptance-and-bug-sdk-001-closure
references:
  - TASK-20260510-011-PM-to-QA
  - REPORT-20260510-010-DEV-to-PM
  - REPORT-20260510-009-QA-to-PM
layer: governance
---

# REPORT-20260510-011：v0.2.0-beta.1 真实 SDK 验收 — BUG-SDK-001 进展 + BUG-SDK-002 新发现

## 一、一句话结论

**MT-1 (defaultModel wire-through) 修复已确认生效（BUG-SDK-001 根因消除），但 real SDK 路径仍被
`BUG-SDK-002`（`agent already has active run`）阻塞，A-08/A-10 无法关闭。**
建议 DEV 紧急调查 `CursorSdkAdapter` run lifecycle 管理并修复 BUG-SDK-002。

---

## 二、Safety HARD GATE — ✅ 全通（5/5）

| 检查项 | 操作 | 结果 |
|---|---|---|
| 全程不读取 `.env` 内容 | 无 `cat .env` / `Get-Content .env` / `type .env` 操作 | ✅ 合规 |
| 全程不 echo key | banner 仅显示 `apiKey from config`，不打印实际 key | ✅ 合规 |
| REPORT 不含 key | 本 REPORT 无 key / stack trace 含 key | ✅ 合规 |
| `.env.example` 无真实 key | `git diff codeflow-shell/.env.example \| Select-String "crsr_[0-9a-f]{8,}"` → 0 匹配 | ✅ PASS |
| `.env` gitignored | `git status --short codeflow-shell/.env` → 无输出 | ✅ PASS |

---

## 三、A-07：Banner live adapter + WARNING 检查

### 测试 1：无 CURSOR_DEFAULT_MODEL（ADMIN `.env` 当前状态）

| 字段 | 结果 |
|---|---|
| 版本 | `CodeFlow v0.2.0-beta.1` ✅ |
| Cursor SDK | `live (CursorSdkAdapter; apiKey from config, listScope="local")` ✅ |
| Config sources | `project-env → process.env` ✅（`.env` 文件被读取） |
| WARNING | **触发**（ADMIN `.env` 未含 `CURSOR_DEFAULT_MODEL`）|

WARNING 内容：
```
WARNING : live SDK + local mode + no CURSOR_DEFAULT_MODEL set.
          First task drop will fail with 'Local SDK agents require an explicit model.'
          Set CURSOR_DEFAULT_MODEL in ~/.codeflow/v2/.env (e.g. `auto`, `claude-sonnet-4`)
          or per-task `spec.modelId`. See README §Cursor API key.
```

**A-07 结论**：✅ banner 正确显示 live adapter，WARNING 行为符合 DEV-010 设计意图（preflight 告警，非强制退出）。

### 测试 2：以 `CURSOR_DEFAULT_MODEL=claude-sonnet-4` env var 覆盖

| 字段 | 结果 |
|---|---|
| Cursor SDK | `live (CursorSdkAdapter; apiKey from config, listScope="local", defaultModel="claude-sonnet-4")` ✅ |
| WARNING | **未触发** ✅（model 已配置）|

**A-07 结论（含 model）**：✅ MT-1 wire-through 正确透传 `defaultModel="claude-sonnet-4"` 到 banner。

---

## 四、A-08/A-09/A-10：真实 SDK drop 测试

### 测试过程

使用 `CURSOR_DEFAULT_MODEL=claude-sonnet-4`（env var 覆盖），两次独立测试：

| 测试 | dataDir | 等待时间 | 结果 |
|---|---|---|---|
| 测试 1 | `.smoke-beta1`（全新） | 120s | `agent.send failed: already has active run` |
| 测试 2 | `.smoke-retry-1223`（全新，30s 间隔） | 120s | `agent.send failed: already has active run` |

### A-09 结果（sdk_agent_id UUID 格式）

两次测试均确认 `sdk_agent_id` 为 UUID 格式：
- 测试 1：`sdk_agent_id = "agent-fc838565-8166-4a72-9606-994a9c9b2d47"` ✅
- 测试 2：`sdk_agent_id = "agent-f07388df-ee4c-4b97-ac99-57794658b0f6"` ✅（新 UUID，确认 `Agent.create()` 成功）

**A-09 结论**：✅ `sdk_agent_id` 为 UUID 格式（非 `sdk-fake-XXXX`），`CursorSdkAdapter.create()` 正常调用并获得服务端 agent。

### A-08 / A-10 失败原因分析（BUG-SDK-002）

```
[TaskDispatcher] startSession failed for TASK-20260509-999-PM-to-DEV.md:
  agent.send failed for sdk_agent_id="agent-f07388df-...":
  Agent agent-f07388df-... already has active run (code=undefined, isRetryable=false)
```

**与 BUG-SDK-001 的关键区别**：

| | BUG-SDK-001（QA-009） | BUG-SDK-002（本轮） |
|---|---|---|
| 错误信息 | `Local SDK agents require an explicit model` | `Agent already has active run` |
| 触发位置 | `agent.send()` 阶段（model 未设置） | `agent.send()` 阶段（model 已正确设置） |
| MT-1 fix 后 | 错误已消除 ✅ | 新错误出现 |
| 根因 | `defaultModel` 未 wire-through | SDK run lifecycle 管理问题 |

**BUG-SDK-002 分析**：

`Agent.create()` 成功（返回新 UUID），但随后 `agent.send()` 报告该 agent "already has active run"。推测原因：
1. Cursor SDK local mode 的 `Agent.create()` 可能自动启动了一个 run
2. `CursorSdkAdapter.send()` 随后再次尝试启动 run，SDK 拒绝（"已有活跃 run"）
3. 需要 `CursorSdkAdapter` 复用 `create()` 已启动的 run，而非独立调用 `send()`

**A-08 结论**：❌ FAIL — 被 BUG-SDK-002 阻塞，无 verdict 产生，无 review 文件  
**A-10 结论**：❌ FAIL — 依赖 A-08，无 transcript 产生

---

## 五、BUG-SDK-001 关闭判断

| 条件 | 状态 |
|---|---|
| MT-1 model wire-through 代码已实现 | ✅（DEV-010 确认） |
| banner 显示 `defaultModel="claude-sonnet-4"` | ✅（QA-011 验证） |
| 错误不再是 "Local SDK agents require an explicit model" | ✅（错误已变为 BUG-SDK-002） |
| A-08 产出真实 LLM verdict（REVIEW decision ≠ needs_human） | ❌（被 BUG-SDK-002 阻塞） |
| A-10 产出 transcript | ❌（同上） |

**BUG-SDK-001 判断**：**无法关闭（Reopen P1）**。
- 根因已修复（MT-1），但被下游 BUG-SDK-002 阻断，A-08/A-10 功能性验证未能完成。
- BUG-SDK-001 在 BUG-SDK-002 修复并 A-08/A-10 通过前维持 P1 状态。

---

## 六、新 Bug 上报

### BUG-SDK-002（P1，新发现）

| 字段 | 内容 |
|---|---|
| **Bug ID** | BUG-SDK-002 |
| **严重度** | P1（阻塞 real SDK governance loop） |
| **发现版本** | v0.2.0-beta.1 |
| **症状** | `agent.send failed: Agent <uuid> already has active run (code=undefined, isRetryable=false)` |
| **复现步骤** | 1. 设置 `CURSOR_API_KEY`（有效）+ `CURSOR_DEFAULT_MODEL=claude-sonnet-4`；2. `npm start`；3. drop 任意 TASK 文件到 inbox |
| **一致性** | 2 次独立测试（不同 dataDir，不同 agent UUID），均出现相同错误 |
| **推测根因** | `CursorSdkAdapter.create()` 调用 `Agent.create()` 后 SDK 自动启动 run；`CursorSdkAdapter.send()` 再次尝试启动 run → SDK 拒绝 "already has active run" |
| **修复方向** | `CursorSdkAdapter` 应复用 `Agent.create()` 返回的 run handle，而非在 `send()` 中独立发起新 run |
| **是否影响 fake adapter** | 否（fake adapter 路径不受影响，BL 基线 99/99 仍有效） |
| **是否影响 v0.1 基线** | 否 |

---

## 七、测试结论总结

```
Safety HARD GATE：  ✅ 全通（5/5）
A-07（banner live）：✅ PASS（无 WARNING: model 已 wire-through；有 WARNING: ADMIN .env 未含 model）
A-08（real verdict）：❌ FAIL — BUG-SDK-002（agent already has active run）
A-09（UUID sdk_id）：✅ PASS — agent-fc838565-... 和 agent-f07388df-... 均为 UUID 格式
A-10（transcript）：❌ FAIL — 依赖 A-08

BUG-SDK-001：      未关闭（Reopen P1）— MT-1 根因已修复，但 BUG-SDK-002 阻断功能验证
BUG-SDK-002：      新 P1 bug 上报

v0.2.0-beta.1 是否推荐进入 P3 (relay-bridge)：
  → ⚠️ 有条件。BUG-SDK-002 不阻塞 relay-bridge 功能开发（relay 主要依赖文件协议，
    不直接依赖 real SDK verdict path）。建议 DEV P3 sprint 并行调查 BUG-SDK-002，
    P3 验收时再补跑 A-08/A-10。
```

---

## 八、PM 待处理事项

| 序号 | 事项 | 优先级 |
|---|---|---|
| 1 | **DEV 调查 BUG-SDK-002**：`CursorSdkAdapter` run lifecycle 管理 — 复用 create() run handle vs. send() 独立发起 run | P1 |
| 2 | **ADMIN 在 `.env` 中添加 `CURSOR_DEFAULT_MODEL=claude-sonnet-4`**：可消除 WARNING，为下次 A-08 重试准备 | P1 |
| 3 | **BUG-SDK-001 维持 P1**，待 BUG-SDK-002 修复后与 A-08/A-10 一并关闭 | P1 |
| 4 | **v0.2.0-beta.1 进入 P3（条件通过）**：BUG-SDK-002 并行修复，A-08/A-10 在 P3 验收时补跑 | P0 |
| 5 | **OPS 补 commit v0.2.0-beta.1 tag**（`-011-PM-to-OPS` 已发，等待执行） | P0 |

---

QA-01
2026-05-10 22:35 (UTC+8)
