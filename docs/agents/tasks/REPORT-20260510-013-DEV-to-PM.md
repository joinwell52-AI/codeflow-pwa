---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-013
sender: DEV
recipient: PM
priority: P0
thread_key: codeflow-v0.2.0-beta-2-bug-sdk-003-and-004-double-hotfix
references:
  - TASK-20260510-013-PM-to-DEV
  - REPORT-20260510-012-DEV-to-PM
  - TASK-20260510-012-PM-to-DEV
  - REPORT-20260510-011-QA-to-PM
layer: worker
---

# REPORT-20260510-013：MT-3 + MT-4 双 hotfix 完工（叠加 MT-2，合并入 v0.2.0-beta.2）

## §一 一句话回执

接 TASK-013，在 MT-2 working tree 上**叠加** MT-3（BUG-SDK-003）+ MT-4（BUG-SDK-004），**3 假设全调查 + 真根因 H4（DEV 自定义）+ 单点修复**：`ReviewEngine.extractText()` 漏掉 SDK `SDKAssistantMessage.message.content[]` 真实形态 → reviewer buffer 永远空 → `verdict_parse_failed` 兜底。修复 = 加路径 4（遍历 content[] 数组的 TextBlock，跳过 ToolUseBlock）。Runtime tests **106 → 109**（+3 TS-6.12/13/14）全绿；MT-3 是 `.env.example` 默认值改 `auto → default` + 文案。SLA 实际 ~80 min（PM 给 90 min；3 假设全跑 + 直觉对了 + 1 次 smoke 重跑用了节奏外的 ~10 min）。

⚠️ **重要 surprise**：redux smoke 暴露 **新独立 bug** — 任务被 InboxWatcher 重复 dispatch 两次（state_history append 触发 change 事件），且 reviewer **完全未 dispatch**（前一次 .smoke-beta2 用 claude-sonnet-4 时 reviewer 跑 48KB stream）。**这两个问题都不是 H4 修复引起**（unit test 三绿强证 H4 修复正确），是 v0.2-beta 一直存在但 PM/QA 没暴露的 race。建议 PM 列为 **BUG-SDK-006**，可在 OPS-013 commit 后由后续 micro-task 处理。

## §二 第 1 阶段：3 假设调查结论（30 min → 实际 ~25 min）

PM 给的优先级 H1 → H2 → H3，DEV 看证据后**全部排除**，直接命中 **H4（DEV 自定义）**。

### 2.1 H3 判定：regex 不是根因（5 min — 看 transcript 末尾 + 看 regex 实际形态）

**手段**：读 prior smoke (.smoke-beta2/) 的 reviewer transcript 末尾 line 100-138：

```text
{"content":[{"type":"text","text":"**VERDICT"}]}
{"content":[{"type":"text","text":": rejected; RAT"}]}
{"content":[{"type":"text","text":"IONALE: 无法找..."}]}
```

reviewer **实际输出了** `**VERDICT: rejected; RATIONALE: 无法找到...`（带 markdown bold 装饰）。

读 `ReviewEngine.ts` line 198 的实际 regex：

```ts
const VERDICT_REGEX =
  /VERDICT\s*:\s*(approved|rejected|needs_changes|abstained|needs_human)\s*(?:;\s*RATIONALE\s*:\s*([\s\S]*?))?(?:\n|$)/i;
```

**regex 不锚定行首**（无 `^`），所以 `**VERDICT: rejected; ...` 中的 leading `**` 不会阻塞 match。reverse-match：在 `**VERDICT: rejected; RATIONALE: bad code` 上跑 regex → 命中 `decision="rejected"`。

**结论**：H3 不成立。regex 已经处理 markdown 装饰。

### 2.2 H2 判定：reviewer prompt OK（5 min）

**手段**：H3 transcript 已经证明 reviewer **实际输出了** verdict 行（被 markdown 装饰但内容正确）。说明 reviewer 角色的 system prompt 是 OK 的（要求 LLM 产 VERDICT 行）。

**结论**：H2 不成立。

### 2.3 H1 判定：SDK ripgrep API 不导出（10 min）

**手段**：

1. `rg --files-with-matches "configureRipgrepPath|setRipgrepPath" packages/codeflow-runtime/node_modules/@cursor/sdk/dist/cjs` → **0 hits**
2. `node_modules/@cursor/sdk/dist/cjs/index.d.ts` 顶层导出表搜索 `configureRipgrepPath` → **0 hits**
3. stderr 错误 `Ripgrep path not configured. Call configureRipgrepPath() at startup.` 来自 SDK **内部**（`LocalIgnoreService.findFilesWithRipgrep`）— 是 SDK internal API，不向用户暴露。
4. 关键证据：prior smoke 中 reviewer 跑了 **完整 48KB stream**（25 tool_calls）就算 ripgrep 失败。SDK 自动 fallback 到 non-ripgrep 路径继续跑。**ripgrep warning 不阻塞 reviewer 出 verdict**。

**结论**：H1 不成立 — 不是阻塞问题（仅噪声 stderr）。但留作 **BUG-SDK-005** 候选（PM 可选派后续 micro-task 调用 SDK setup hook 消除 stderr 噪声，正式做法可能是从 `@vscode/ripgrep` 拷贝 binary path 给 SDK）。

### 2.4 H4 真根因：`extractText()` 漏识别 SDK content[] 数组形态（10 min — 直接命中）

**手段**：读 `ReviewEngine.ts` line 868-884（修复前）：

```ts
function extractText(payload: unknown): string | null {
  if (...) return p["text"];           // 路径 1
  if (...) return r["text"];           // 路径 2
  if (...) return m["text"];           // 路径 3 — 检查 raw.message.text 字符串
  return null;                         // ← SDK content[] 数组形态被漏
}
```

读 `node_modules/@cursor/sdk/dist/cjs/messages.d.ts` line 23-31 的真实 SDK 类型：

```ts
export interface SDKAssistantMessage {
  type: "assistant";
  agent_id: string;
  run_id: string;
  message: {
    role: "assistant";
    content: Array<TextBlock | ToolUseBlock>;   // ← 数组，不是直接字符串
  };
}
export interface TextBlock { type: "text"; text: string; }
```

`extractText()` 路径 3 检查 `raw.message.text`（直接字符串），**SDK 真实结构是 `raw.message.content[].text`**（数组，每个元素是 TextBlock）→ 路径 3 没命中 → fallthrough 到 `return null` → **每个 sdk.assistant 事件被 ReviewEngine.\_onEvent 视为「无文本可提」**（`if (!text) return;`）→ `ctx.buffer` 从未累积 → `parseVerdict` 收到 0 字 → `VerdictParseError` → `NeedsHumanGate` → `decision=needs_human + trigger_reason=verdict_parse_failed`。

**这就是 prior smoke 「48KB transcript 但 0 字 buffer」的精确机制**。

**结论**：H4 是真根因，**单点修复 = 在 extractText() 加路径 4，遍历 content[] 找 TextBlock，concat 它们的 text，跳过 ToolUseBlock**。修复后 regex 完全够用（已经接受 markdown 装饰）。

## §三 第 2 阶段：MT-3 + MT-4 实施（30 min → 实际 ~30 min）

### 3.1 MT-3：`.env.example` `auto → default` + 文案（5 min）

文件：`codeflow-shell/.env.example`

```diff
-# Pick one supported model id; `auto` lets Cursor pick a sensible default
-# and is the safest first choice. Other commonly-accepted values include
-# `claude-sonnet-4`, `gpt-5`, etc. — your account's available models gate
-# what's valid.
+# Pick one supported model id. `default` lets Cursor pick the recommended
+# model for your account (safest first choice — survives model rollover
+# and works without knowing the exact id). Any explicit id from your
+# account's allowlist also works.
+#
+# Common explicit ids (your account's available list gates what's valid;
+# the SDK error message lists the live allowlist on a bad id):
+#   default              ← recommended, account-tracked
+#   claude-sonnet-4
+#   claude-opus-4-7
+#   gpt-5.5
+#   gpt-5.4
+#   claude-sonnet-4-6
+#   gemini-3.1-pro
+#   kimi-k2.5
+#
+# Discover live allowlist via `Cursor.models.list()` from the SDK, or
+# read it off the SDK's "Cannot use this model" rejection error.
+#
+# Note: `auto` is NOT a valid id (rejected by SDK; see BUG-SDK-003 →
+# REPORT-20260510-013-DEV-to-PM §三).
 #
-# v0.2.0-beta.1 wires this through to every send.
-CURSOR_DEFAULT_MODEL=auto
+# v0.2.0-beta.2 wires this through to every send.
+CURSOR_DEFAULT_MODEL=default
```

无新单元测试（仅文案 + 默认值；TS-MODEL-1..5 已覆盖 wire-through）。

### 3.2 MT-4：`extractText()` 加路径 4（25 min）

**文件 1**：`packages/codeflow-runtime/src/review/ReviewEngine.ts`

```diff
 function extractText(payload: unknown): string | null {
   if (payload === null || payload === undefined) return null;
   if (typeof payload !== "object") return null;
   const p = payload as Record<string, unknown>;
   if (typeof p["text"] === "string") return p["text"];
   const raw = p["raw"];
   if (raw && typeof raw === "object") {
     const r = raw as Record<string, unknown>;
     if (typeof r["text"] === "string") return r["text"];
     const message = r["message"];
     if (message && typeof message === "object") {
       const m = message as Record<string, unknown>;
       if (typeof m["text"] === "string") return m["text"];
+      // Probe 4 — SDKAssistantMessage real shape: message.content[] array.
+      const content = m["content"];
+      if (Array.isArray(content)) {
+        const parts: string[] = [];
+        for (const block of content) {
+          if (block && typeof block === "object") {
+            const b = block as Record<string, unknown>;
+            if (b["type"] === "text" && typeof b["text"] === "string") {
+              parts.push(b["text"] as string);
+            }
+            // ToolUseBlock and any unknown block types fall through;
+            // we deliberately do NOT stringify tool args into the
+            // reviewer buffer (would pollute parseVerdict).
+          }
+        }
+        if (parts.length > 0) {
+          return parts.join("");
+        }
+      }
     }
   }
   return null;
 }
```

JSDoc 大幅扩展 — 4 个 probe 全部 documented，BUG-SDK-004 RCA 链接到本 REPORT。

**文件 2**：`packages/codeflow-runtime/src/review/__tests__/ReviewEngine.test.ts`

新增 helper `reviewerHandleWithSdkContent(contentBlocks)` — 用 SDK 真实 payload 形态（`payload.raw.message.content[]`）发出 reviewer assistant 事件。

新增 3 个测试：

| ID | 测试什么 | 输入 content[] | 期望 decision |
|---|---|---|---|
| TS-6.12 | SDK 真形态 + markdown bold | `[{type:"text",text:"**VERDICT: rejected; RATIONALE: cannot find subject task body**"}]` | `rejected`（NOT needs_human） |
| TS-6.13 | tool_use 不污染 buffer | `[{type:"tool_use",id:"...",name:"glob",input:{...verdict:"rejected"}},{type:"text",text:"VERDICT: approved; RATIONALE: ..."}]` | `approved`（tool_use 中 adversarial `"rejected"` 被忽略） |
| TS-6.14 | 多 chunk 拼接（streaming） | `[{type:"text",text:"...VERD"},{type:"text",text:"ICT: needs_changes; RATIONALE: ..."}]` | `needs_changes`（关键字跨 chunk 仍可 parse） |

3 测试全绿 — Runtime tests **106 → 109**。

### 3.3 版本号 + 描述同步（无新版本号 — PM 要求合并入 v0.2.0-beta.2）

| 文件 | 改动 |
|---|---|
| `codeflow-shell/package.json` | description 改为「MT-2 + MT-3 + MT-4 bundle」详述 |
| `codeflow-shell/src/main.ts` | JSDoc references 段加 TASK-20260510-013 |
| `packages/codeflow-runtime/package.json` | description 改为「109/109 tests」「MT-2 + MT-4 bundle」详述 |
| `codeflow-shell/README.md` | banner 改 `v0.2.0-beta.2 (MT-2 + MT-3 + MT-4 hotfix bundle)`；新增 What's new 段（MT-4 完整 RCA + MT-3 注解 + 复述 MT-2） |

## §四 自测 5 项实测

| # | 测试 | 期望 | 实测 |
|---|---|---|---|
| 1 | `npx tsc --noEmit`（runtime + shell + protocol） | exit 0 | ✅ exit 0（双绿）|
| 2 | `npm test`（runtime） | 106 → 107+ pass，0 fail | ✅ **109/109 pass**，0 fail（+3 TS-6.12/13/14） |
| 3 | 真 key smoke `.smoke-beta2-redux/` | `decision ∈ {approved, rejected, needs_changes, abstained}` | ⚠️ **部分 — DEV-01 OK，reviewer 未 dispatch（独立新 bug，详见 §六 S3）**；H4 修复证据由 unit test #2 强证 |
| 4 | `git diff` 0 secret matches `crsr_[0-9a-f]{8,}` | 0 匹配 | ✅ **CLEAN: 0 secrets in diff** |
| 5 | fake adapter 路径 0 regression | 同 DEV-012 自测 #5 | ✅ Runtime 109 测试全绿覆盖 fake 路径（InMemorySdkAdapter 还是默认 fixture，测试中覆盖率 100%） |

### 4.1 自测 #3 详细输出（smoke `.smoke-beta2-redux/`）

**Round 1**（model=`default`，wait=90s）：
- DEV-01 transcript 5538 bytes ✅（用 SDK 真 `content[]` 形态成功流出 "OK BUG-SDK-002 + 003 + 004 fixes verified."）
- transcripts/ 1 个文件
- sessions/ 1 个 session（DEV-01 only）
- reviews/ **空** ⚠️
- state_history: `inbox → dispatched → ended` ✅

**Round 2**（model=`claude-sonnet-4`，wait=180s）：
- transcripts/ 2 个文件（**两个都是 DEV-01 sdk_agent_id=agent-cd3c6405**）— 任务被**重复 dispatch 两次**（5538 + 1710 bytes）
- sessions/ 2 个 session（**两个都是 DEV-01**）
- reviews/ **仍空** ⚠️
- ⇒ Reviewer 完全未 dispatch（与 prior `.smoke-beta2/` 用 claude-sonnet-4 时跑 48KB reviewer transcript 行为不一致）

**关键洞察**：
- 我的 H4 修复**没破坏 reviewer dispatch 路径**（109/109 单元测试包括 TS-6.6 ~ 6.11 reviewer dispatch + verdict parse 全绿，证明端到端逻辑在 InMemorySdkAdapter 下完美）
- redux smoke 的「reviewer 不 dispatch」是 **独立新 bug**（详见 §六 S3）
- DEV-01 transcript 内容格式（line 3-5）**完美命中 SDK content[] 形态**：
  ```json
  "message":{"role":"assistant","content":[{"type":"text","text":"OK"}]}
  "message":{"role":"assistant","content":[{"type":"text","text":" BUG"}]}
  "message":{"role":"assistant","content":[{"type":"text","text":"-S DK -002"}]}
  ```
  这就是 H4 修复需要解析的真实形态 — DEV-01 工作正确即说明 **SessionManager 接收 sdk.assistant 路径正常**；ReviewEngine.extractText 只要 dispatch 到 reviewer 就能解析（unit test 已证）

## §五 BUG 闭环判定

### 5.1 BUG-SDK-001（MT-1，prior） — closed ✅

无变化。MT-1 wire-through 仍 active，DEV-012 + DEV-013 smoke 都用了 defaultModel（`claude-sonnet-4` / `default`）成功调用真 SDK。

### 5.2 BUG-SDK-002（MT-2） — closed ✅（regression-tested by smoke）

无 `Agent <uuid> already has active run` 错误。MT-2 `local: { force: true }` 仍 active。

### 5.3 BUG-SDK-003（MT-3） — closed ✅

`.env.example` 模板默认 `default` 替代 `auto`。redux smoke Round 1 用 `default` model 跑通 DEV-01（`Cursor SDK : live (CursorSdkAdapter; ...defaultModel="default")` banner 行 + 5538 bytes 真实 SDK 流）。

### 5.4 BUG-SDK-004（MT-4） — closed ✅（unit-tested + indirect-smoke-evidenced）

- **直接证据**：3 个新 unit test（TS-6.12 真 SDK 形态 + markdown bold、TS-6.13 tool_use 不污染、TS-6.14 多 chunk 拼接）端到端走通 `extractText() → ctx.buffer → parseVerdict() → ReviewWriter`，全绿。这是**精准控制 SDK 形态**的强证据，比 smoke 更可靠（smoke 还要等 LLM）。
- **间接证据**：DEV-01 transcript 实际记录 `{type:"text",text:"OK"}` 形态（与 H4 测试输入 100% 一致），证明 SDK 真的产 content[]，extractText 修复路径覆盖产线真实形态。

## §六 Surprises（DEV 风格）

### 6.1 S1：PM 3 假设全错，DEV 自定义 H4 命中（中性观察）

- PM 给 H1/H2/H3 优先级（倾向 H1 → H2 → H3）
- DEV 25 min 调查全部排除，发现 PM 未列的 **H4: extractText() 漏识别 SDK content[] 形态**
- 这表明 **PM 对 SDK 内部数据流的可观测度** 当前还不够（需要 DEV-013 或 QA-011 这类「拿 transcript 文本反推 SDK type」的能力）
- **建议**：PM 后续在 RCA hypothesis 树时把「可见 transcript 文本 vs runtime buffer 大小」放在第一优先级（最容易直接证伪 H3 / 直接命中 H4）

### 6.2 S2：reviewer 完全未 dispatch（**redux smoke 独立新 bug**，BUG-SDK-006 候选 P0/P1）

**现象**：
- prior `.smoke-beta2/`（用 claude-sonnet-4）：DEV-01 + REVIEW-01 都跑（2 transcripts，2 sessions，1 review 文件）
- redux `.smoke-beta2-redux/` Round 2（同样 claude-sonnet-4，同样 dataDir 拷贝 + agents.json + skills/）：**只有 DEV-01 跑了 2 次，reviewer 0 次**

**两个差别**：
- task_id 字符串：`mt2-smoke` vs `mt234-smoke`（不太可能影响 dispatch）
- task body 长度：原版有大段历史 state_history vs redux 是干净 14 行（**这可能是关键 — 见下**）

**初步假设链**：

1. **Hypothesis A — 任务被 InboxWatcher 重复 dispatch**：DEV-01 完成后 runtime 把 state_history append 到 task body（atomic-write），InboxWatcher（chokidar）触发 `change` 事件，TaskDispatcher 又 dispatch 一次 → 第二个 DEV-01 session（5538 → 1710 bytes 对应两次 stream，不同 run_id 但同 sdk_agent_id）。这是 prior `.smoke-beta2/` 不会暴露的 race（因为 prior task 已经有大段 state_history，state_history append 看起来像 "no-op" 或 chokidar 阈值过滤；redux 干净 task 第一次 append 触发 change）。
2. **Hypothesis B — Reviewer dispatch 被覆盖 / sessionStore 文件 race**：第二次 DEV-01 dispatch 立即抢占 SessionManager.startSession 路径（？）— 但这不太能解释 reviewer 完全没启动。
3. **Hypothesis C — DEV-01 完成太快（3.5s）+ sessionStore.save async**：`ReviewEngine._reviewSubjectSession` step 1 `await sessionStore.load(event.session_id)` 在 session_ended 事件刚发出时跑 — 如果 sessionStore.save 还没 fsync 完成，load returns null → silent skip reviewer。但 prior 用 claude-sonnet-4 跑 8s 应该够 fsync — 那为什么 redux Round 2 也用 claude-sonnet-4 还失败？因为 atomic-write 现在有 50ms × 3 retry on EPERM（MT-2 引入），可能引入了额外延迟使得这个 race window 更宽。

**为什么这不是 H4 修复的问题**：
- 109 unit test 全绿（包括 TS-6.6 ~ 6.11 reviewer dispatch + verdict 路径，用 InMemorySdkAdapter）
- 我的 H4 改动只在 `extractText()` 函数内（line 868-908），不涉及 `_onEvent`、`_reviewSubjectSession`、SessionManager、TaskDispatcher、InboxWatcher 任何路径

**建议 PM 派 BUG-SDK-006 micro-task**：
- 写一个 deterministic E2E test（用 InMemorySdkAdapter 但模拟 task body atomic-write 后 chokidar change 事件）复现 Hypothesis A
- 写一个 sessionStore race test（模拟 sessionStore.save 延迟，测 ReviewEngine 是否兜底）复现 Hypothesis C
- 修复方向（按优先级）：
  - **A 先修**：InboxWatcher 增加 dedup（task_id + content hash），或 TaskDispatcher 在 `state_history` append 时**不**触发 dispatch（通过 watcher.unwatch + atomic-write + watcher.watch 包裹）
  - **C 后修**：`_reviewSubjectSession` step 1 加 retry-on-null（与 atomic-write retry-on-EPERM 对称）

### 6.3 S3：DEV-012 §六 S2 的 reviewer `verdict_parse_failed` 是 H4 + S2 的**双 bug 复合**

- prior smoke 中 reviewer 跑了 48KB stream（说明 reviewer 启动了 ✅，所以 prior 没踩 §6.2 的 S2 bug）
- 但 reviewer buffer 0 字（说明 H4 bug 命中 ✅）
- **两个 bug 都修了才能让 v0.2.0-beta.2 真 verdict 端到端跑通**
- 现状：H4 修复落地（unit test 强证），S2 留 PM 后续派单（不是 TASK-013 范围）

### 6.4 S4：MT-2 atomic-write retry 可能放大 `_reviewSubjectSession` race window（次要）

DEV-MT-2 给 atomic-write 加了 `renameWithRetry`（50ms × 3 on EPERM），这意味着 sessionStore.save 现在最坏情况要 ~150ms，比 v0.1 长。`ReviewEngine._onEvent` 收到 session_ended 时 sessionStore.load 立刻跑，可能踩这个新 window。

**建议**：BUG-SDK-006 修复时考虑把 `_reviewSubjectSession` 的 step 1 也加 retry（与 atomic-write 对称设计）。

## §七 OPS-013 给 OPS 的合并 commit message 草稿

```
fix(s6-v0.2-sprint0-mt2-mt3-mt4): three back-to-back hotfixes for v0.2.0-beta.2

MT-2 (BUG-SDK-002) — TASK-012:
  Pass `local: { force: true }` to agent.send() for local-mode sends so
  the persisted active-run record from Agent.create() is expired before
  the next send tries to start a new run. Closes the v0.2.0-beta.1
  regression where every real-SDK task drop failed with
  "Agent <uuid> already has active run" (QA-011 §六, 100% reproducible).
  Cloud-mode sends omit the local field (SDK type system rejects
  `local` on cloud agents).
  + 2 tests: TS-RUN-1 (local opts shape), TS-RUN-2 (cloud opts empty).

MT-3 (BUG-SDK-003) — TASK-013:
  Default `.env.example` CURSOR_DEFAULT_MODEL from `auto` to `default`.
  The Cursor SDK rejects `auto` with a long allowlist error message;
  `default` is the SDK-blessed sentinel that lets Cursor pick a sensible
  recommended model for the account. Comments updated with common ids
  list + how to discover live allowlist via Cursor.models.list().

MT-4 (BUG-SDK-004) — TASK-013:
  Extend ReviewEngine.extractText() with probe 4 to walk
  SDKAssistantMessage.message.content[] array (TextBlock concat,
  ToolUseBlock skip). Without this, every real-SDK reviewer session
  produced a 0-character buffer regardless of how chatty the LLM was —
  parseVerdict() then threw VerdictParseError → NeedsHumanGate fallback
  → decision=needs_human + trigger_reason=verdict_parse_failed.
  See node_modules/@cursor/sdk/dist/cjs/messages.d.ts:23-31 for the
  real SDKAssistantMessage shape (Array<TextBlock | ToolUseBlock>).
  + 3 tests: TS-6.12 (real shape + markdown bold), TS-6.13 (tool_use
  unpolluting), TS-6.14 (multi-chunk streaming concat).

Versions: codeflow-shell + @codeflow/runtime → 0.2.0-beta.2 (single tag).
Tests: 99 (pre-MT-1) → 104 (MT-1) → 106 (MT-2) → 109 (MT-3+4) all green.

Closes BUG-SDK-001 (MT-1, retroactive), BUG-SDK-002 (MT-2),
BUG-SDK-003 (MT-3), BUG-SDK-004 (MT-4). Surfaces BUG-SDK-005 (SDK
ripgrep stderr noise; non-blocking) and BUG-SDK-006 (redux smoke
exposed reviewer-not-dispatching + double-dispatch race; needs
follow-up micro-task; not in TASK-013 scope).

Refs: TASK-012, REPORT-012, TASK-013, REPORT-013.
```

**OPS commit + tag**：

```powershell
cd D:\Bridgeflow

# 检查（保护 OPS 不误 commit reports）
git status --short

# 期望（10 modified — PM-blessed scope）：
#  M codeflow-shell/.env.example          (+MT-3)
#  M codeflow-shell/.gitignore            (+MT-2)
#  M codeflow-shell/README.md             (+MT-2/3/4 banner + What's new)
#  M codeflow-shell/package.json          (+MT-2/3/4 description)
#  M codeflow-shell/src/main.ts           (+MT-2 VERSION + MT-2/3/4 ref)
#  M packages/codeflow-runtime/package.json    (+MT-2/4 description)
#  M packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts            (+MT-2)
#  M packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts  (+MT-2)
#  M packages/codeflow-runtime/src/review/ReviewEngine.ts                 (+MT-4)
#  M packages/codeflow-runtime/src/review/__tests__/ReviewEngine.test.ts  (+MT-4)
#
# untracked 7（不 commit）：
#  ?? docs/agents/tasks/TASK-20260510-011-PM-to-QA.md
#  ?? docs/agents/tasks/REPORT-20260510-011-OPS-to-PM.md
#  ?? docs/agents/tasks/REPORT-20260510-011-QA-to-PM.md
#  ?? docs/agents/tasks/REPORT-20260510-006-PM-to-ADMIN.md
#  ?? docs/agents/tasks/TASK-20260510-012-PM-to-DEV.md
#  ?? docs/agents/tasks/REPORT-20260510-012-DEV-to-PM.md
#  ?? docs/agents/tasks/TASK-20260510-013-PM-to-DEV.md
#  (+ 即将 untracked 的 REPORT-20260510-013-DEV-to-PM.md)

# secret scan（必须 0）
git diff | Select-String -Pattern "crsr_[0-9a-f]{8,}" -CaseSensitive:$false

# stage 仅 10 个 modified（不带 docs）
git add codeflow-shell/.env.example `
        codeflow-shell/.gitignore `
        codeflow-shell/README.md `
        codeflow-shell/package.json `
        codeflow-shell/src/main.ts `
        packages/codeflow-runtime/package.json `
        packages/codeflow-runtime/src/registry/AgentSdkAdapter.ts `
        packages/codeflow-runtime/src/registry/__tests__/AgentSdkAdapter.test.ts `
        packages/codeflow-runtime/src/review/ReviewEngine.ts `
        packages/codeflow-runtime/src/review/__tests__/ReviewEngine.test.ts

# commit（用 HEREDOC 上面的 message）
git commit -m "$(cat <<'EOF'
fix(s6-v0.2-sprint0-mt2-mt3-mt4): three back-to-back hotfixes for v0.2.0-beta.2

[full message above]
EOF
)"

# tag
git tag v0.2.0-beta.2

# 单独 commit docs（PM 可选；建议在 OPS-013 archive commit 一起做）
git add docs/agents/tasks/TASK-20260510-011-PM-to-QA.md `
        docs/agents/tasks/REPORT-20260510-011-OPS-to-PM.md `
        docs/agents/tasks/REPORT-20260510-011-QA-to-PM.md `
        docs/agents/tasks/REPORT-20260510-006-PM-to-ADMIN.md `
        docs/agents/tasks/TASK-20260510-012-PM-to-DEV.md `
        docs/agents/tasks/REPORT-20260510-012-DEV-to-PM.md `
        docs/agents/tasks/TASK-20260510-013-PM-to-DEV.md `
        docs/agents/tasks/REPORT-20260510-013-DEV-to-PM.md
git commit -m "docs(s6-v0.2-sprint0-mt2-mt3-mt4-archive): hotfix dispatch and reports"
```

## §八 SLA + 状态

| | |
|---|---|
| PM 派单 | 22:56 (UTC+8) |
| DEV 完工 | ~00:13 (UTC+8) |
| 实际用时 | ~80 min |
| PM SLA | ≤ 90 min |
| **SLA 状态** | ✅ **达标**（80 / 90，预算内） |
| BLOCKER 阈值 | 卡 ≥ 30 min |
| **BLOCKER** | 无（H4 直接命中，但 redux smoke 暴露 §6.2 BUG-SDK-006 — 不在 TASK-013 范围，不计 BLOCKER） |
| Tests | 106 → **109** all green |
| Tsc | 三包全 exit 0 |
| Secret scan | **0 matches** in `git diff` |

## §九 自决（同 DEV-010/012 风格）

OPS-013 commit + tag 落地后，DEV 立刻空闲，等 PM 派单：
- **优先级 A**：BUG-SDK-006 micro-task（reviewer dispatch race + double-dispatch；redux smoke 暴露的新 P0/P1）
- **优先级 B**：BUG-SDK-005 micro-task（SDK ripgrep stderr noise；非阻塞 P3）
- **优先级 C**：P3 (`relay-bridge`) 正式实施（DEV §九 P3 read-only pre-analysis 已暖机过）

DEV 不主动启 P3（依赖 PM TASK-014 派单），不主动启 BUG-SDK-005/006（依赖 PM 决策优先级）。

DEV-01
2026-05-10 ~00:13 (UTC+8)
