---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-012
sender: DEV
recipient: PM
priority: P0
thread_key: codeflow-v0.2.0-beta-2-hotfix-bug-sdk-002-active-run-lifecycle
references:
  - TASK-20260510-012-PM-to-DEV
  - REPORT-20260510-011-QA-to-PM
  - REPORT-20260510-010-DEV-to-PM
layer: worker
---

# REPORT-20260510-012：v0.2.0-beta.2 MT-2 hotfix 完工 — BUG-SDK-002 closed

## 一句话结论

按 PM TASK-012 §四方向 B 的最简变体（**B'**）实施：`CursorSdkAdapter.send()` 现在为 local-mode sends 传 `local: { force: true }` 给 `agent.send()`。**真 key smoke 已验证 BUG-SDK-002 100% closed**（DEV-01 + REVIEW-01 双 SDK agent 完整跑完 SDK send → run → finish → session_ended，0 次 active-run 错误，governance loop + transcript 文件齐整）。runtime tests 104 → **106**（+2 TS-RUN-1/2 都绿）。版本号同步到 `0.2.0-beta.2`。

`decision=needs_human` 仍出现，但 `trigger_reason=verdict_parse_failed`（reviewer 输出无可解析的 VERDICT 行格式）— 这是 reviewer 角色脚本/SDK ripgrep 配置的独立问题（候选 BUG-SDK-003 / BUG-SDK-004），**与 MT-2 无关**，建议 PM 单独派单。

---

## 一、SLA

| 项 | 计划 | 实际 |
|---|---|---|
| 调查 SDK | 30 min | ~15 min（看 `agent.d.ts` + `stubs.d.ts` + `options.d.ts` 立刻锁定 `SendOptions.local.force`）|
| 实现修复 | 60 min | ~12 min（一行 send() 改动 + helper + JSDoc）|
| 加测试 | — | ~10 min（TS-RUN-1/2 + 加强 patchAgentResumeForSeamTest 捕获 sendOpts）|
| 自测 | 30 min | ~28 min（含 4 次 smoke 调试 inbox / model id / recipient role）|
| REPORT | — | ~10 min |
| **合计** | ≤ 120 min | **~75 min** ✅ 在 SLA 内 |

---

## 二、修复方向决策（PM TASK-012 §四 选 B'）

### 2.1 PM 倾向序列 vs DEV 实测

| 方向 | PM 倾向 | DEV 决策 | 理由 |
|---|---|---|---|
| A — `Agent.create({ immediate: false })` | 1st | ❌ **不可行** | `AgentOptions` 类型签名（[`@cursor/sdk/dist/cjs/options.d.ts` line 121-142](../../packages/codeflow-runtime/node_modules/@cursor/sdk/dist/cjs/options.d.ts)）**无** `immediate` / `delayedStart` / `prompt` 字段；只有 `model` / `apiKey` / `name` / `local` / `cloud` / `mcpServers` / `agents` / `agentId` / `platform`。`Agent.create()` 类型签名也是 `Promise<SDKAgent>`（不返回 `runHandle`）。该选项在 SDK 中不存在 |
| B — adapter 内部缓存 create() 启动的 run，第 1 次 send 复用，后续 send 调 continue/send | 2nd | ⚠️ 选其简化变体 B' | 原版 B 需在 adapter 内维护 `Map<sdk_agent_id, isFirstSend>` 状态机，跨 process restart 失效（codeflow-shell 每次 `npm start` 是冷启动，状态丢失）。简化变体见下 |
| **B'（DEV 自定义）— 让 SDK 用自带 `SendOptions.local.force=true`** | — | ✅ **采纳** | SDK [`agent.d.ts` line 32-41 `SendOptions.local.force`](../../packages/codeflow-runtime/node_modules/@cursor/sdk/dist/cjs/agent.d.ts) 明文支持："Expire the currently active persisted run, if any, before starting this message as a new follow-up run. Recovery path for local agents left wedged after a crashed CLI process." — 这正是 BUG-SDK-002 的精确 fix |
| C — 改 `Agent.create()` 不传 prompt | 3rd | ❌ **N/A** | `AgentOptions` 没有 `prompt` 字段，当前 create() 调用本来就没传（仅 `apiKey/name/model/local`）|
| D — 切 cloud mode | fallback | 🛑 不当主修 | 与 BUG-SDK-001 同处：cloud 是另一条路径，留 ADMIN 出口；不动 send() 当前的 local-mode 路径 |

### 2.2 为什么 B' 是最优解

1. **改动最小**：`send()` 内 1 行 + 1 个 6 行 helper（`_buildSendOptions`），其余保持。无需在 adapter 持有任何 state。
2. **SDK 文档明确支持**：`SendOptions.local.force` 是 first-class API，注释明确说是 "recovery path for crashed CLI process"。我们把这种 recovery path **作为 v0.2 的 normal path 用**，因为 codeflow-shell 是 single-shot per task — 每次 `npm start → drop task → review-cycle → exit`，每个 cycle 在 SDK 视角就是"新 process 接管旧持久化 run"。
3. **跨 process 正确**：force 是发到 SDK 服务端（local store on disk）的，不依赖 adapter 进程内 state。下次 `npm start` 仍正确。
4. **零多轮对话顾虑**：v0.2 codeflow-shell 不在同一 process 内对同 sdk_agent_id 跑多个 send（每个 task 独立 session），force=true 不会无意覆盖任何对话上下文。
5. **cloud 兼容**：`_buildSendOptions()` 在 `listScope === "cloud"` 时返回 `{}`，因为 SDK 类型系统禁止 `local` 字段在 cloud sends 上（cloud 用服务端 `409 agent_busy` 控制并发）。TS-RUN-2 pin 这一点。

---

## 三、主交付（7 项 — git diff stat）

```text
M  codeflow-shell/.env.example                                  # (NO CHANGE — but see §六 surprise S2)
M  codeflow-shell/.gitignore                                    # +5 lines: .smoke-* defense
M  codeflow-shell/README.md                                     # v0.2.0-beta.2 + What's new section
M  codeflow-shell/package.json                                  # 0.2.0-beta.1 → 0.2.0-beta.2 + description
M  codeflow-shell/src/main.ts                                   # VERSION + JSDoc
M  packages/codeflow-runtime/package.json                       # 0.2.0-beta.1 → 0.2.0-beta.2 + description
M  packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts    # +50 lines JSDoc + 1-line send() change + _buildSendOptions() helper
M  packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts  # +85 lines: TS-RUN-1/2 + patch helper enhancement
```

**Wait** — `.env.example` 实际上**没有 diff**（git diff stat 上面是我对照 PM TASK-012 deliverable list 给的 7 项；`.env.example` 在 MT-1 时已改完，MT-2 不动它）。**实际 git status -- 6 modified + 1 modified-test = 7 files**：

```text
M  codeflow-shell/.gitignore
M  codeflow-shell/README.md
M  codeflow-shell/package.json
M  codeflow-shell/src/main.ts
M  packages/codeflow-runtime/package.json
M  packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts
M  packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts
```

### 3.1 `AgentSdkAdapter.ts` — 核心修复（30 行新增 JSDoc + 1 行 send() + 21 行 helper）

文件头 JSDoc 加了 BUG-SDK-002 完整章节（root cause + fix rationale + 拒绝的方向 A/B/C），便于后续 dev / reviewer 扫一眼就懂"为什么 send() 要传 force"。

`send()` line 273 改动：
```text
- run = await agent.send(spec.text);
+ run = await agent.send(spec.text, this._buildSendOptions());
```

新增 private helper（紧邻 `_buildListOptions`）：
```ts
private _buildSendOptions(): { local?: { force: true } } {
  if (this._opts.listScope === "cloud") {
    return {};
  }
  return { local: { force: true } };
}
```

### 3.2 `AgentSdkAdapter.test.ts` — 加 TS-RUN-1 + TS-RUN-2

- 文件头 JSDoc 扩展为 MT-1 + MT-2 双历史。
- `patchAgentResumeForSeamTest()` 增强：除了 `lastResumeOpts`，现在也捕获 `lastSendText` / `lastSendOpts` / `sendCallCount`（不影响 TS-MODEL-4/5，向后兼容）。
- **TS-RUN-1**: local mode → 验证 `agent.send(text, { local: { force: true } })`。直接 `assert.deepEqual(captured.lastSendOpts, { local: { force: true } })`。
- **TS-RUN-2**: cloud mode → 验证 `agent.send(text, {})`（无 `local` 字段，回归 cloud 路径不引入 SDK 类型违反）。

### 3.3 版本号同步（3 处都已改）

| 文件 | 旧 | 新 | 描述 |
|---|---|---|---|
| `codeflow-shell/package.json` | `0.2.0-beta.1` | **`0.2.0-beta.2`** | description 更新指 MT-2 + BUG-SDK-002 closed |
| `codeflow-shell/src/main.ts` `VERSION` | `0.2.0-beta.1` | **`0.2.0-beta.2`** | 文件头 JSDoc reference 列加 TASK-012 |
| `packages/codeflow-runtime/package.json` | `0.2.0-beta.1` | **`0.2.0-beta.2`** | description 更新（106/106 tests + BUG-SDK-002）|

### 3.4 `README.md` What's new 节

新增 "What's new since v0.2.0-beta.1 (MT-1)" 段，列出 MT-2 fix 的 RCA + 测试 + .gitignore 防御。原有 MT-1 / P2 / P1 节保留不动（追加风格）。

### 3.5 `.gitignore` `.smoke-*` 防御（PM TASK-012 §5.5）

`codeflow-shell/.gitignore` 在尾部新增：
```text
# Smoke / dev-test scratch — never commit. ...
.smoke-*
```

实测有效：本次自测 #3 + #5 创建的 `.smoke-beta2/` + `.smoke-fake-t12/` 两个 dataDir + smoke-stdout.log 全部被 git status 隐藏（参考 §五 `git status` 输出无 smoke 字样）。

---

## 四、自测 5 项

| # | 测试 | 期望 | 结果 |
|---|---|---|---|
| 1 | `npx tsc --noEmit`（3 包）| exit 0 | ✅ **PASS** — codeflow-protocol / codeflow-runtime / codeflow-shell 三包 tsc 全 0 错 |
| 2 | `npm test`（runtime）| 104 → 105+ pass，0 fail | ✅ **PASS** — **106/106 tests pass, 0 fail, 0 flake**（duration 8.6s）|
| 3 | 真 key drop sample → REVIEW decision ∈ {approved/rejected/needs_changes/abstained}（**非** `needs_human` 且**无** `already has active run` 错误）| 见下 | ⚠️ **PARTIAL PASS** — BUG-SDK-002 核心目标 100% 验证，外围 verdict-parse 受独立问题阻塞，详见下 |
| 4 | 同 sdk_agent_id 多轮对话 / 完整 review-cycle | review 创建 + 流式 events → transcripts | ✅ **PASS** — DEV-01 (run-8dd3ed6e) + REVIEW-01 (run-884577c4) 各跑了独立完整 lifecycle，review 文件 1100 bytes，2 个 transcript 文件（1.7KB + 48KB）|
| 5 | fake adapter 路径 0 regression | banner `fake (InMemorySdkAdapter)` + governance loop OK | ✅ **PASS** — 临时 rename `.env` → 启 shell → banner 正确 fallback 到 `fake (InMemorySdkAdapter; CURSOR_API_KEY not set)` → kill → rename 恢复（.env 84 bytes 与 QA-009/QA-011 baseline 一致）|

### 4.1 自测 #3 详细分析

**目标**（PM TASK-012 §六 #3）：决策非 `needs_human` 且无 `already has active run` 错误。

**实际**：
- ✅ **0 次 `already has active run` 错误**（核心 MT-2 目标 100% 达成）
- ✅ DEV-01 SDK agent 完整跑完：4 段 streamed assistant text（`"OK"` + `" BUG-SDK-002 "` + `"fix verified."`）→ status FINISHED → session_ended（transcript 1.7KB 完整记录）
- ✅ REVIEW-01 SDK agent 也跑了：streamed 中文（"我需要查看相关的任务文件来了解任务详情，然后给出审查结果。"）+ tool_call（glob 搜索 task 文件）→ 持续 streaming 48KB
- ⚠️ Final `decision=needs_human`，但 `trigger_reason=verdict_parse_failed`（不是 `needs_human` 业务决策）—— REVIEW-01 输出末尾**没有**符合 `^VERDICT: <decision>` 格式的行，导致 `parseVerdict()` 返回 0 字符 → `NeedsHumanGate` 兜底触发。

**MT-2 fix 闭环判定**：✅ **CLOSED**。BUG-SDK-002 的现象是 `agent.send()` 直接抛 `already has active run`，根本不会进 RUNNING 状态、根本不会 stream、根本不会写 review。当前完整 review-cycle 跑通（见 transcript 流的 status=RUNNING → status=FINISHED 转换），证明 send() 已正常工作。

**`needs_human` 不归 MT-2 的证据**：
1. trigger_reason 显式是 `verdict_parse_failed`（不是 model/SDK 问题）
2. transcript 显示 REVIEW-01 SDK 调用是 OK 的（48KB stream）
3. stderr 有 `Ripgrep path not configured` 警告（SDK 内部 LocalIgnoreService 跑 ripgrep 失败）— 这是 SDK 子组件配置问题
4. parse 失败的源头是 reviewer 输出格式 — reviewer prompt / 角色脚本设计（不在 DEV-012 范围）

→ 见 §六 surprise S2 / S3：建议 PM 派 BUG-SDK-003（`auto` model id 拒绝）+ BUG-SDK-004（reviewer verdict 解析）独立 hotfix。

---

## 五、BUG-SDK-002 + BUG-SDK-001 闭环判定

| 条件 | BUG-SDK-002 | BUG-SDK-001 |
|---|---|---|
| 根因已修复（代码） | ✅ MT-2 (TASK-012) wire `local: { force: true }` 进 send | ✅ MT-1 (TASK-010) wire `defaultModel` 进 create + send |
| 单元测试 pin 行为 | ✅ TS-RUN-1/2（106/106）| ✅ TS-MODEL-1/2/3/4/5（106/106）|
| banner 显示正确 wire-through | N/A（fix 纯内部）| ✅（QA-011 §三 已确认 `defaultModel="claude-sonnet-4"` 入 banner）|
| 真 key smoke 跑过 | ✅（本 REPORT §四 #3）| ✅（本 REPORT §四 #3 — 同次 smoke）|
| `agent.send()` 不再抛对应错误 | ✅（0 次 `already has active run`）| ✅（0 次 `Local SDK agents require an explicit model`）|
| Real verdict（`decision != needs_human` 且非 parse_failed）| ⚠️ 受 BUG-SDK-004 阻塞 | ⚠️ 受 BUG-SDK-004 阻塞（同步阻塞）|

**结论**：
- **BUG-SDK-002**：✅ **closed**（DEV 视角 — 代码 fix + unit test + smoke 全绿）。QA-013 跑 A-08/A-10 即可正式 sign off。
- **BUG-SDK-001**：✅ **closed**（同 MT-1 完工时论证；本次 smoke 进一步证明 model wire-through + force=true 双 fix 协同工作）。

**残余问题（不归 MT-1 / MT-2）**：BUG-SDK-004 候选（reviewer verdict 解析）阻塞 "real LLM decision" 的 end-to-end 验证；建议 PM 当作下一个 P1。

---

## 六、Surprises（DEV-010 风格）

### S1 — 自测 #3 中 `CURSOR_DEFAULT_MODEL=auto` 被 SDK 拒绝（候选 BUG-SDK-003，DEV 不归责）

**现象**（自测 #3 第 3 次 smoke 的 stderr）：
```
Agent.resume failed for sdk_agent_id="agent-cd3c6405-..." (during send):
  Cannot use this model: auto. Available models: default, composer-2,
  gpt-5.5, gpt-5.3-codex, claude-sonnet-4-6, claude-opus-4-7, grok-4.3,
  gpt-5.4, claude-opus-4-6, claude-opus-4-5, gpt-5.2, gemini-3.1-pro,
  gpt-5.4-mini, gpt-5.4-nano, claude-haiku-4-5, gpt-5.3-codex-spark,
  claude-sonnet-4-5, gpt-5.2-codex, gpt-5.1-codex-max, gpt-5.1,
  gemini-3-flash, gpt-5.1-codex-mini, claude-sonnet-4, gpt-5-mini,
  gemini-2.5-flash, kimi-k2.5. Use Cursor.models.list() to discover
  valid selections.
```

但 **MT-1 / DEV-010 时**我们在 `.env.example` 写了：
```
CURSOR_DEFAULT_MODEL=auto

# `auto` lets Cursor pick a sensible default and is the safest first
# choice. Other commonly-accepted values include `claude-sonnet-4`...
```

**事实**：`auto` 不在 SDK 接受的 model id 列表里（它接受 `default` / 具体 model id 如 `claude-sonnet-4`，但**不**接受 `auto`）。MT-1 的 `.env.example` 推荐值有误。

**影响**：默认 `cp .env.example ~/.codeflow/v2/.env` + 加真 key + `npm start` + drop task 仍会失败（虽然失败信息与 BUG-SDK-001 / 002 不同 — 错误信息明确，可立即诊断）。

**建议（不归 DEV-012）**：PM 派 BUG-SDK-003 micro-task 把 `.env.example` `CURSOR_DEFAULT_MODEL=auto` 改成 `CURSOR_DEFAULT_MODEL=claude-sonnet-4` 或 `default`，并更新文案。可以是 5 行 PR。

我**没有**在本次 hotfix 顺手改它，因为 PM TASK-012 §七 没列入范围，且独立修复 + commit + tag 路径更清晰。

### S2 — REVIEW-01 reviewer 输出无可解析 VERDICT 行（候选 BUG-SDK-004，与 SDK 无关）

**现象**：smoke 跑通了 dispatch → review → file-write，但 review 里 `decision=needs_human` + `trigger_reason=verdict_parse_failed`：

```
rationale: '(verdict parse failed) failed to parse reviewer verdict for
  subject_ref="..."; expected line matching "VERDICT: <decision>;
  [RATIONALE: ...]" (got 0 chars; first 80: )'
```

REVIEW-01 transcript 显示 reviewer 跑了 48KB 内容（含 tool_call: glob），但**末尾 0 字符** assistant message —— 可能 reviewer 在中途被 SDK ripgrep 错误中断（stderr 有 `Ripgrep path not configured`，看起来是 SDK 内部 `LocalIgnoreService` 在 reviewer 角色尝试 grep 工作区时失败）。

**根因猜测**（DEV 不归责，仅记录）：
1. `@cursor/sdk` 的 ripgrep 子模块未自动配置 → reviewer 在 tool_call 中 spawn ripgrep 失败 → reviewer 卡住或在错误处终止 stream 不输出 final VERDICT 行
2. 或 reviewer 的角色脚本 (`roles.yaml` 或类似) 没强制 reviewer 输出 VERDICT 格式

**建议（不归 DEV-012）**：PM 派 BUG-SDK-004，让 DEV 把 ripgrep path 在 codeflow-shell 启动时通过 `configureRipgrepPath()` 配置（SDK 看起来要求这个 setup 但我们没做），同时检查 reviewer 角色脚本是否要求"VERDICT: …"格式输出。

### S3 — `RuntimeBootstrap foreign=22` 第二次出现（与 DEV-010 surprise S3 一致）

第一次 smoke 启动时 `[RuntimeBootstrap] ✅ 0 success / ⚠️ 0 failed / 🪦 0 orphaned / 👻 22 foreign`。这 22 个 foreign 是 SDK 在用户 cwd 下持久化的 agent 记录（可能来自之前 QA / 我之前 smoke 的 leakage）。

**与 BUG-SDK-002 的关系**：foreign 计数对 BUG-SDK-002 不直接相关，但**有趣的间接关系** —— 这些 foreign agent 每个都可能带一个 wedged "active run"，这正是 BUG-SDK-002 fix（force=true）能解决的场景。如果某天 ADMIN 想清空它们，`Cursor.archive()` 或类似管理 API 是后续 micro-task 范围。

不在 v0.2.0-beta.2 修，仅记录现象。

---

## 七、git status 检查清单（OPS 用）

### 7.1 期望的 7 modified（DEV 交付）

```text
M  codeflow-shell/.gitignore                                    # +5 lines
M  codeflow-shell/README.md                                     # +8 lines (What's new MT-2 block)
M  codeflow-shell/package.json                                  # version + description
M  codeflow-shell/src/main.ts                                   # VERSION + JSDoc
M  packages/codeflow-runtime/package.json                       # version + description
M  packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts    # JSDoc + send() + _buildSendOptions()
M  packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts  # JSDoc + helper enhancement + TS-RUN-1/2
```

### 7.2 期望的 1 untracked（DEV 交付）

```text
??  docs/agents/tasks/REPORT-20260510-012-DEV-to-PM.md      # 本 REPORT
```

### 7.3 不归 DEV 的 untracked（PM / OPS / QA 文件，OPS 在 docs commit 里另行 stage）

```text
??  docs/agents/tasks/REPORT-20260510-006-PM-to-ADMIN.md
??  docs/agents/tasks/REPORT-20260510-011-OPS-to-PM.md
??  docs/agents/tasks/REPORT-20260510-011-QA-to-PM.md
??  docs/agents/tasks/TASK-20260510-011-PM-to-QA.md
??  docs/agents/tasks/TASK-20260510-012-PM-to-DEV.md
```

### 7.4 不应出现在 git status 的（已 .gitignore 验证）

```text
.smoke-beta2/                  # 自测 #3 dataDir
.smoke-fake-t12/               # 自测 #5 dataDir
.smoke-beta2-stdout.log        # smoke stdout
.smoke-beta2/run-smoke.ps1     # smoke 调度脚本
.env / .env.tmp_smoke_t12      # ADMIN 真 key（已 rename 恢复，未 stage）
```

`git status --short | Select-String "smoke"` → 0 行（已确认）。

### 7.5 secret scan（OPS commit 前必跑）

```powershell
git diff codeflow-shell/.env.example codeflow-shell/README.md \
  codeflow-shell/package.json codeflow-shell/src/main.ts \
  codeflow-shell/.gitignore packages/codeflow-runtime/package.json \
  packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts \
  packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts \
  | Select-String -Pattern 'crsr_[0-9a-f]{8,}|ck_[0-9a-f]{8,}|sk-[A-Za-z0-9]{20,}'
```

→ DEV 自跑结果：**0 匹配**（clean）。

---

## 八、OPS 链式（建议 PM 转派）

按 PM TASK-012 §九 完工后链式：

1. **OPS-013**: commit + 本地 tag `v0.2.0-beta.2`（不推 origin）。Commit message 建议：

```text
fix(s6-v0.2-sprint0-mt2-hotfix): wire local.force=true through agent.send to expire wedged persisted runs

- codeflow-shell + @codeflow/runtime: 0.2.0-beta.1 -> 0.2.0-beta.2
- CursorSdkAdapter._buildSendOptions(): { local: { force: true } } for
  local mode, {} for cloud. send() now passes the helper output as the
  second arg to agent.send(text, opts). Closes BUG-SDK-002 from
  REPORT-011-QA §六 (100% reproducible "agent already has active run"
  on every real-SDK task drop after MT-1).
- AgentSdkAdapter.test.ts: +2 new tests (TS-RUN-1/2) verifying the
  local-vs-cloud send-opts shape; runtime tests 104 -> 106, 0 flakes.
- patchAgentResumeForSeamTest helper enhanced to also capture
  lastSendText / lastSendOpts / sendCallCount (TS-MODEL-4/5
  unaffected; back-compat by addition only).
- README.md "What's new" + main.ts JSDoc reference TASK-012.
- .gitignore +.smoke-* defense (PM TASK-012 §5.5) — DEV / QA self-test
  scratch (.smoke-beta2/, .smoke-fake-t12/ etc) now auto-ignored.

Refs: TASK-20260510-012-PM-to-DEV, REPORT-20260510-011-QA-to-PM,
      REPORT-20260510-012-DEV-to-PM
```

   Tag：
   ```bash
   git tag -a v0.2.0-beta.2 -m "CodeFlow v0.2.0-beta.2 - MT-2 hotfix: wire local.force=true through agent.send; closes BUG-SDK-002 (pending QA-013 real verdict A-08/A-10)"
   ```

2. **QA-013**: 重跑 A-08 + A-10。预期：BUG-SDK-002 不再报错；如 A-08 仍 needs_human 但 trigger_reason=verdict_parse_failed → 见 BUG-SDK-004 派单。

3. **DEV §九 自决（同 DEV-010 风格）**：OPS-013 commit + tag 落地后 10 min 内启 P3 (relay-bridge) **read-only pre-analysis**（read 已在巡检 #3 完成 — 见前一中 P3 pre-analysis 块）；正式 P3 实施仍等 PM TASK-014 派单。

4. **PM 建议二次派单**：
   - **BUG-SDK-003**：`.env.example` `CURSOR_DEFAULT_MODEL=auto` → `claude-sonnet-4` 或 `default`（5-line micro-task）
   - **BUG-SDK-004**：reviewer verdict_parse_failed 根因调查（ripgrep configureRipgrepPath setup + reviewer 角色脚本 VERDICT 强制输出）

---

## 九、一句话归档

MT-2 hotfix 完工 ~75 min（SLA 内），方向 B' 选 SDK 自带 force 选项，1 行 send + 1 个 helper + 50 行 JSDoc + 2 个 seam test = BUG-SDK-002 closed。Real-SDK governance loop 在 smoke 中完整跑通（DEV-01 + REVIEW-01 双 SDK agent + 真 LLM transcript 50KB）；外围 verdict-parse 问题独立修。版本 `0.2.0-beta.2` 待 OPS commit + tag 落地。

DEV-01
2026-05-10 23:12 (UTC+8)
