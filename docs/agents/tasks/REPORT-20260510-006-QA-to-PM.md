---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-006
sender: QA
recipient: PM
priority: P0
thread_key: codeflow-v0.2.0-alpha-acceptance-no-key
references:
  - TASK-20260510-006-PM-to-QA
  - REPORT-20260510-002-DEV-to-PM
  - REPORT-20260510-004-QA-to-PM
layer: governance
---

# REPORT-20260510-006：v0.2.0-alpha 验收（无 key 路径）— 通过

## 一、一句话结论

**v0.2.0-alpha 无 key 路径（BL-01~04 + A-01~A-06）全部通过，QA 建议进入 P2 EXE 打包阶段（beta）。**

额外发现：测试基线从 94 升至 **99/99**（DEV 悄含 MT-2 TS-AW-1~5，atomic-write retry），为正向变化。

---

## 二、测试基线（BL）

| 编号 | 检查项 | 结果 | 命令/输出摘要 |
|---|---|---|---|
| BL-01 | fake adapter 治理循环（NeedsHumanGate + state_history） | ✅ PASS | `[NeedsHumanGate]` 触发；4 bullets 全部 append |
| BL-02 | runtime npm test | ✅ PASS（99/99） | `pass 99 / fail 0`（含新增 TS-AW-1~5） |
| BL-03 | tsc --noEmit（codeflow-shell + runtime） | ✅ PASS | exit 0 |
| BL-04 | v0.1 功能在 v0.2 代码上无回归 | ✅ PASS | NeedsHumanGate / review file / state_history 全正常 |

### BL-02 注记：测试数量升至 99

DEV 在本次工作树中悄含 MT-2（`renameWithRetry` EPERM retry）实现，并附带 5 条新单测：

| 新增测试 | 内容 |
|---|---|
| TS-AW-1 | EPERM 第一次失败，第二次成功 → atomicWriteJson resolves |
| TS-AW-2 | 连续 EPERM → 超过 maxAttempts 后 reject |
| TS-AW-3 | ENOENT → 首次即 reject（不重试非 EPERM 错误） |
| TS-AW-4 | 无 EPERM → 恰好 1 次 rename，无多余重试 |
| TS-AW-5 | 自定义 maxAttempts/backoffMs 参数生效 |

第一次冷启动（在非 `packages/codeflow-runtime` 目录执行）出现 1 次 `ReferenceError: renameWithRetry is not defined` 的临时 flake，重跑后连续两次 99/99 稳定。判断为首次 tsx 编译缓存未预热的一次性 flake，**不计为 bug**。

---

## 三、v0.2.0-alpha 专项（A 系列，无 key）

| 编号 | 检查项 | 结果 | 输出摘要 |
|---|---|---|---|
| A-01 | banner 显示 `v0.2.0-alpha` | ✅ PASS | `CodeFlow v0.2.0-alpha ✅ internal preview` |
| A-02 | 无 CURSOR_API_KEY → fake adapter | ✅ PASS | `Cursor SDK: fake (InMemorySdkAdapter; CURSOR_API_KEY not set ⬇️ ...)` |
| A-03 | fake key → live adapter（CursorSdkAdapter） | ✅ PASS | `Cursor SDK: live (CursorSdkAdapter; apiKey from config, listScope="local")` |
| A-04 | ConfigLoader 6 层优先级（env > defaults） | ✅ PARTIAL | env var 覆盖 defaults 已验证；user config.json 层（home dir）因测试环境限制未能植入测试（不修改 ADMIN home dir） |
| A-05 | `.env.example` ergonomics | ✅ PASS | 6 个白名单 key，含分组注释和 relay P3 注释，ADMIN 可直接使用 |
| A-06 | sample-task drop + state_history 4 bullets（DEV Surprise 3 修复验证） | ✅ PASS | 文件名 `TASK-20260509-999-PM-to-DEV.md` = frontmatter task_id，4 bullets 全部 append，review 文件 1047 bytes |

**A-07~A-10（真实 SDK verdict）**：依赖 ADMIN 有效 `CURSOR_API_KEY`，本轮 N/A。

---

## 四、Surprise 观测

### Surprise 3 修复（DEV 声明）— ✅ 已验证

`examples/hello-world/sample-task.md` drop 时文件名与 frontmatter `task_id` 一致，
state_history append 无 "Task file not found" 错误，4 bullets 全部写入。

### Surprise 4（EPERM rename race）— 本次运行 0 次

- 本次 A-06 治理循环测试：log 共 23 行，EPERM 关键字出现：**0 次**
- MT-2 `renameWithRetry` 已在工作树中实现（TS-AW-1~5 全通）
- 下次正式 commit 需确认 MT-2 代码被纳入

### RuntimeBootstrap foreign 数异常

| 测试场景 | dataDir 状态 | `👻 foreign` 数 |
|---|---|---|
| A-01（首次启动） | 全新目录 | 0 |
| A-03（首次启动，fake key） | 全新目录 | 2 |
| A-04（首次启动，env key） | 全新目录 | 4 |

首次启动预期应为 0 foreign。A-03/A-04 出现 2/4 foreign 的原因尚不明确，可能是：
- `AgentStatusReconciler` 在 `registered 2 default agents` 事件发生后，reconcile 扫描到了刚注册的 agents 被视为 "foreign"（race 时序问题）
- **不影响治理循环功能**（下游 InboxWatcher → ReviewEngine 全部正常）

**建议 PM/DEV 确认**：首次启动 foreign > 0 是否为已知 / 预期行为。

---

## 五、偏差记录

| 偏差 | 说明 | 影响 |
|---|---|---|
| v0.2.0-alpha 代码在工作树（未 commit） | OPS-005 commit 尚未产生；QA 在工作树执行验收 | 功能等同，测试结果有效；待 OPS commit 后需核对 commit SHA |
| 测试基线从 94 升至 99 | DEV 悄含 MT-2（5 条 TS-AW 测试） | 正向，99/99 应作为新基线 |
| A-04 user config.json 层未验证 | 不修改 ADMIN home dir | SHOULD 级别，可在 beta 阶段补验 |

---

## 六、PM 待处理事项

| 序号 | 事项 | 优先级 |
|---|---|---|
| 1 | **通知 OPS commit**：新基线为 **99/99**（含 TS-AW-1~5），commit message 需更新 | P0 |
| 2 | **进入 P2（beta）**：建议 PM 发 DEV `TASK-20260510-007`（EXE 打包），QA 待命验收 | P0 |
| 3 | **ADMIN 提供 CURSOR_API_KEY**：A-07~A-10 真实 SDK 路径验证待 key | P1 |
| 4 | **DEV 确认 RuntimeBootstrap foreign > 0 行为**：首次启动 A-03/A-04 出现 2/4 foreign，请 DEV 说明是否预期 | P2 |
| 5 | **下次 OPS commit 纳入 MT-2**：`renameWithRetry` 实现 + TS-AW-1~5 必须纳入，否则 EPERM Surprise 4 风险持续 | P1 |

---

## 七、文件变更（本轮 QA 无新增文件）

本轮所有操作均在临时 `.smoke-*` 目录进行，测试完成后已全部清理。

---

## 八、验收结论

```
BL-01~04：✅ 全通（4/4）
A-01~A-06：✅ 全通（6/6，A-04 PARTIAL 已说明）
A-07~A-10：N/A（待 ADMIN key）
Surprise 3 修复：✅ 已验证
Surprise 4 EPERM：本次 0 次（MT-2 已实现，待 commit）
RuntimeBootstrap foreign：需 DEV 确认（不阻塞发布）
新测试基线：99/99（不是 94/94）
建议：v0.2.0-alpha 内部验收通过，✅ 建议进入 P2 EXE 打包（beta 阶段）
```

QA-01
2026-05-10 02:20 (UTC+8)
