# @codeflow/runtime

> **Phase A + Phase B（Sprint S3）已完成 — AgentRegistry + PersistentStore + RuntimeBootstrap + SessionManager + SessionStore + TranscriptWriter 全部 v0.1 兑现。Task Scheduler / Skill Runtime / Review Engine 见路线图 Phase C / S4 / S5。**

CodeFlow AI Runtime —— 6 大 kernel 子系统中的 **2 个**（Agent Registry + Session Manager），现已 v0.1 全量落地。

- 上游设计：[`docs/design/codeflow-v2-on-fcop-sdk.md`](../../docs/design/codeflow-v2-on-fcop-sdk.md) §2.1（子系统 1 + 子系统 3）+ §3（Runtime Protocol & Schemas）
- Phase A 派单：[`docs/agents/tasks/TASK-20260509-009-PM-to-DEV.md`](../../docs/agents/tasks/TASK-20260509-009-PM-to-DEV.md)
- Phase B 派单：[`docs/agents/tasks/TASK-20260509-013-PM-to-DEV.md`](../../docs/agents/tasks/TASK-20260509-013-PM-to-DEV.md)
- Sprint 路线图：[`docs/design/codeflow-v2-on-fcop-sdk.md` §10.2](../../docs/design/codeflow-v2-on-fcop-sdk.md)
- 持久化决策：[`docs/crash-recovery.md`](./docs/crash-recovery.md)

## 包内职责（v0.1 全量）

| 子系统 / 类 | 文件 | OS 类比 | 状态 |
|---|---|---|---|
| **AgentRegistry** | `src/registry/AgentRegistry.ts` | 进程控制块表 (PCB) | ✅ Phase A 完成（6 方法 + race-defense） |
| **PersistentStore** + `JsonFileStore` | `src/registry/PersistentStore.ts` | 文件系统 + journal log | ✅ Phase A 完成（atomic-write + fsync） |
| **RuntimeBootstrap** | `src/registry/RuntimeBootstrap.ts` | init / systemd | ✅ Phase A 完成（reconciliation 同步流程 + TS-2.8 SDK.list HARD FAIL） |
| **AgentSdkAdapter** + `CursorSdkAdapter` / `InMemorySdkAdapter` | `src/registry/AgentSdkAdapter.ts` | SDK 适配层 | ✅ Phase A + Phase B 完成（含 send 接口） |
| **SessionManager** | `src/session/SessionManager.ts` | 进程调度器（会话层） | ✅ Phase B 完成（6 方法 + emergency stop） |
| **SessionStore** | `src/session/SessionStore.ts` | 单 record per file 的 PCB 存储 | ✅ Phase B 完成（atomic-write 复用 helper） |
| **TranscriptWriter** | `src/session/TranscriptWriter.ts` | 事件流 append-only md | ✅ Phase B 完成（streaming + concurrent-close safe） |
| **SdkRunHandle** | `src/session/SdkRunHandle.ts` | SDK Run 包装 + 8→`sdk.*` 事件映射 | ✅ Phase B 完成 |
| `ReconciliationReport` / `ReconciliationStrategy` | `src/types/state.ts` | 启动审计 | ✅ Phase A 完成（drift 检测留位 Phase B+） |

### AgentRegistry 6 方法 method-by-method

| 方法 | 状态 | 关键不变量 |
|---|---|---|
| `register(spec)` | ✅ 完成 | layer=admin 在 SDK 调用前 reject；ajv 验证；SDK 失败 → agents.json 不写 |
| `resume(agentId)` | ✅ 完成 | 找不到 → `AgentNotFoundError`；SDK 失败保留原 cause；更新 `runtime_last_reconciled_at` |
| `list(filter?)` | ✅ 完成 | layer / role / status 三字段 AND-combined |
| `get(agentId)` | ✅ 完成 | 不存在返 `null`，不抛 |
| `updateRuntimeBinding(agentId, runtime)` | ✅ 完成 | 不自动触发 resume（避免副作用串联） |
| `markFailed(agentId, error)` | ✅ 完成 | 写 `status=error` + `runtime_failure` |

### SessionManager 6 方法 method-by-method（Phase B 新增）

| 方法 | 状态 | 关键不变量 |
|---|---|---|
| `startSession(agentId, taskId, payload)` | ✅ 完成 | agent 验证先于 SDK 调用；attach 早于 save 防 event race；save 失败 → SDK 反向 cancel + 状态回滚 |
| `getSession(sessionId)` | ✅ 完成 | 不存在返 `null`，不抛（与 `AgentRegistry.get` 对称） |
| `listActive()` | ✅ 完成 | 直接 SessionStore 反映；无内存缓存防止跨重启漂移 |
| `cancelSession(sessionId, reason)` | ✅ 完成 | **SDK cancel 严格先于持久化**；幂等（二次取消 → transcript warning） |
| `cancelAllForEmergencyStop()` | ✅ 完成 | `Promise.allSettled` 语义，单失败不阻塞同伴；EMERGENCY-{ts}.md 留 v0.2 S10 钩子 |
| `onEvent(handler)` | ✅ 完成 | 12 类 RuntimeEvent fan-out；throw listener 自动 unsubscribe + console.error |

### Phase B 4 大设计决策（实施时锁定，详见 `REPORT-20260509-013-DEV-to-PM.md`）

- **决策 J**：`SessionNotFoundError` / `InvalidAgentStatusError` 合并到 `registry/errors.ts`，不另起 `session-errors.ts`
- **决策 M**：`RuntimeEventType` 8 个 sdk.* 类型以 `_ignore/spike_sdk_doorbell/` 实测为准（system / thinking / assistant / tool_call / status / task / request / user），TASK-013 §主交付 3 line 110 列的 Anthropic-shaped 名字是该文档误植
- **决策 N**：每次 `send` 内部走 `Agent.resume → agent.send → 包装成 RunHandle → settled 时 dispose`，不在 adapter 内持池
- **决策（Phase B 顺手）**：把 atomic-write 抽成 `src/_internal/atomic-write.ts` helper 给 SessionStore + 未来 store 复用，Phase A 的 `JsonFileStore` 不重构（不动稳定代码）

## 不在本包内（按 §0.7 + §10.2 sprint 边界）

| 子系统 | 在哪个 sprint 落 |
|---|---|
| Task Scheduler (chokidar inbox 门铃) | **Phase C**（紧接 Phase B 之后的下一刀） |
| Skill Runtime (per-role MCP 注入) | **S5** —— 单独的 `@codeflow/skill-runtime` 包 |
| Review Engine ⭐ | **S4** —— 单独的 `@codeflow/review-engine` 包 |
| Mobile Console / 中继 | **v0.2 S7-S10** |
| EMERGENCY-{ts}.md 落档（emergency stop 完整审计） | **v0.2 S10**（接钩子） |
| 实际调用 `Agent.create / resume` 的 spike | 仍在 [`_ignore/spike_sdk_doorbell/`](../../_ignore/spike_sdk_doorbell/) — 作为参考实现保留 |

## 协议依赖纪律（Phase A + B 一致）

- 本包**只消费**`@codeflow/protocol`（FCoP spec 的 TS 镜像）的类型与 schema
- **不允许**在 `src/types/state.ts` 创造任何 schema 字段；只允许 *runtime 私有* 的纯运行时构造（如 `RuntimeEvent` / `ReconciliationReport` / `SessionHandle` / `RunHandle` 等）
- 任何 schema 缺口 → 写到 PM 的回执，**不在本包内私自加**
- Phase A + Phase B 实施过程中 **0 个** schema 缺口出现
- 详见设计文档 §8.0 硬规则 #4 + §3.3.1.b 唯一合法升级路径

## 目录结构

```
packages/codeflow-runtime/
├── package.json
├── tsconfig.json
├── README.md                                  ← 本文件
├── src/
│   ├── index.ts                               公开 API barrel
│   ├── _internal/
│   │   └── atomic-write.ts                    ✅ Phase B 抽取的 atomicWriteJson helper
│   ├── registry/                              Agent Registry（§2.1 子系统 3）
│   │   ├── AgentRegistry.ts                   ✅ Phase A 完成
│   │   ├── PersistentStore.ts                 ✅ JsonFileStore (atomic-write+fsync)
│   │   ├── RuntimeBootstrap.ts                ✅ Phase A + TS-2.8 SDK.list HARD FAIL
│   │   ├── AgentSdkAdapter.ts                 ✅ + send + InMemoryRunHandle (Phase B)
│   │   ├── errors.ts                          ✅ 8 个 named error class（含 Phase B 2 个 session 类）
│   │   ├── index.ts
│   │   └── __tests__/                         18 个 node:test，全部通过
│   │       ├── AgentRegistry.test.ts          场景 1-6
│   │       ├── RuntimeBootstrap.test.ts       场景 7-9 + 11 + 12 (TS-2.8 B-path)
│   │       ├── PersistentStore.test.ts        场景 10 + 11 (并发 upsert TS-1.6) + 5 sanity
│   │       └── helpers.ts
│   ├── session/                               Session Manager（§2.1 子系统 1）
│   │   ├── SessionManager.ts                  ✅ Phase B 完成（6 方法）
│   │   ├── SessionStore.ts                    ✅ Phase B 完成（单 record per file）
│   │   ├── TranscriptWriter.ts                ✅ Phase B 完成（append-only md + 并发 close 安全）
│   │   ├── SdkRunHandle.ts                    ✅ Phase B 完成（SDK Run 包装 + 8→sdk.* 映射）
│   │   ├── RunHandle.ts                       接口 re-export
│   │   ├── index.ts
│   │   └── __tests__/                         22 个 node:test，全部通过
│   │       ├── SessionManager.test.ts         TS-4.1 ~ TS-4.5 + onEvent 隔离
│   │       ├── SessionStore.test.ts           save/load/listAll/remove + tolerant-read
│   │       ├── TranscriptWriter.test.ts       attach/append/close/closeAll
│   │       └── helpers.ts
│   └── types/
│       └── state.ts                           AgentRecord / SessionRecord / RuntimeEvent
│                                              + Phase A: ReconciliationReport
│                                              + Phase B: RunHandle.onEvent + RuntimeEventType 12 类
├── fixtures/                                  样例数据（设计 review，非测试）
│   ├── agents.json                            §2.1 子系统 3 的 agents.json 样例
│   └── sessions/
│       └── valid-runtime-session-001.json
└── docs/
    └── crash-recovery.md                      4 个崩溃恢复设计决策
```

## 验收

| 项 | 验证方式 |
|---|---|
| 包编译通过 | `npx tsc --noEmit`（零报错） |
| 单元测试 | `npm test`（**40/40** 全过 — Phase A 16 + 场景 12 + 并发 11 + 22 Phase B） |
| `@codeflow/protocol` 包未受影响 | `cd ../codeflow-protocol && npm test`（仍 8/8 通过） |
| atomic-write 模式 | `PersistentStore.ts` + `_internal/atomic-write.ts` 含 `writeFile(*.tmp)` + `rename` + 父目录 `fsync` |
| layer=admin 拒绝在 SDK 调用前 | 测试场景 3 spy 验证 `sdk.calls.create.length === 0` |
| RuntimeNotReady 防御 | 测试场景 11 |
| TS-2.8 SDK.list HARD FAIL | 测试场景 12 |
| TS-1.6 并发 upsert 不损坏 JSON | 测试场景 11（PersistentStore） |
| SessionManager 串行不变量 | TS-4.4：`SDK cancel 时间戳 ≤ store cancelled 时间戳` |
| Phase B emergency stop allSettled | TS-4.5：1 失败 + 1 成功 = `cancelled.length + failed.length === 2` |
| 协议依赖纪律 | `src/registry`/`src/session`/`src/types` 不重新声明 schema 字段，仅 `import type` from `@codeflow/protocol` |

## 跑测试

```bash
cd packages/codeflow-runtime
npm install         # 一次性
npm run typecheck   # 0 错误
npm test            # 40/40 PASS
```

## v0.1 起未来 sprint 路径

- ✅ **Phase A**（commit `407cfa5`）：AgentRegistry + PersistentStore + RuntimeBootstrap
- ✅ **Phase B**（本里程碑）：SessionManager + SessionStore + TranscriptWriter + TS-2.8 patch + L2 文档落档
- ⏸ **Phase C**：Task Scheduler chokidar inbox 门铃 + state_history 自动追加 + E2E mini demo
- ⏸ **S4**：Review Engine（最关键⭐）
- ⏸ **S5**：Skill Runtime + fcop 强依赖校验
- ⏸ **S6**：E2E 跑通 §0.8.3 Hello World demo + v2 EXE 出厂（codeflow-shell + Node SEA）

详见 [`docs/design/codeflow-v2-on-fcop-sdk.md` §10.2](../../docs/design/codeflow-v2-on-fcop-sdk.md) + [§11 v2 Packaging](../../docs/design/codeflow-v2-on-fcop-sdk.md)。
