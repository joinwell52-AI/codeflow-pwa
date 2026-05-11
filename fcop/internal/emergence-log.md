# CodeFlow Emergence Log

> 内部档案 — 不外发，不进 fcop issue。
> 用途：沉淀 ADMIN 战略指令、PM 错误自披露、DEV/OPS/QA 自挖的 latent bug 与协作模式。
> 与 `docs/design/codeflow-v2-on-fcop-sdk.md` 的分工：design doc 是「现在该怎么做」；本 log 是「过去怎么误判、是怎么纠正、为什么纠正」。
>
> 维护者：PM-01
> 起始：2026-05-11

---

## 0. 索引

| 章节 | 主题 |
|---|---|
| §1 | Charter 1-6 与诞生时刻原话 |
| §2 | PM 自约束 1-10 + 9.1 派单后扩展 |
| §3 | PM 错误自披露 1-18 |
| §4 | 团队自挖的 latent bug（非 PM 错） |
| §5 | DEV/OPS/QA 改进 PM 流程的事件 |
| §6 | 决策点 D1-D9 历史档案 |
| §7 | Cursor SDK 7 类失败模式（QA-004 §十归纳） |
| §8 | 候选未来 sprint 备录（P3.5 Capability 拦截层等） |
| §9 | 节奏档案（SLA 加速倍率） |

---

## §1. Charter 1-6 与诞生时刻

### Charter 1 — Mobile-first Governance（早期设计）

ADMIN 通过 PWA 在手机端完成下达 / 审批 / 变更三件事；PC 端是执行机。

### Charter 2 — File Protocol（agent_bridge）

> AI 角色之间不能只在脑子里说话，必须落成文件。

来源：`.cursor/rules/codeflow-project.mdc` 第一条总则。

### Charter 3 — 5 Schema 真正作用（ADMIN 2026-05-09）

> 5 类 Schema 真正应该变成"约束 + 能力 + 状态 + 权限"，不是"定义固定动作"。让 Agent 自己完成：规划/协作/拆解/实现。
> CodeFlow 真正做的，不是"控制 Agent"，而是"为 Agent 提供一个不会崩溃的协作宇宙"。

### Charter 4 — ADMIN 是真人角色（5/9）

> ADMIN-01 是真人成员，不是 AI 子工种。职责只有一个核心：把真人输入的文本，规范化地交给 PM-01。
> ADMIN 只需要下达 / 审批 / 变更，等权力角色所做的事。

### Charter 5 — CodeFlow = FCoP 应用层（ADMIN 2026-05-11 09:35 + 09:37 双战略指令）

诞生时刻原话：

> 09:35：CodeFlow 一定是基于 FCoP 协议的，其实就是协议的具体应用；不需要自创的；如果有新的需求，向 FCoP 提，然后 FCoP 去解决。
> 09:37：既然 FCoP 未来要 AI OS，CodeFlow 只能是在 FCoP 协议基础上去做，当然，也许涌现的，可以补充 FCoP 协议。

**条款**：
1. CodeFlow 永不重发明 FCoP 已实现的能力
2. CodeFlow 中的涌现需求 → 先**内部消化**（绕 / 等 / 改设计） → 累积 ≥ 3 次涌现且确认无内部解 → 才向 FCoP 报需求
3. 涌现的协议补充走"建议"姿态，不主动设计 FCoP 接口
4. CodeFlow 仍持有应用层涌现物（如 agent 运行态 PCB / SDK session 状态 / Windows EPERM retry），这些是"FCoP 没必要管的事"

### Charter 6 — FCoP 三层定位（ADMIN 2026-05-11 14:21 战略陈述）

诞生时刻原话（完整保留）：

> **FCoP 的本质（一句话）**：FCoP 是一个约束 Agent 行为的"可观测 + 可审计 + 可治理协议层"，它不调度任务，只规定行为如何被记录与评估。
>
> **FCoP 核心定位的深层拆解**
>
> **1. Report（行为可见性）：拒绝黑箱**
> - 语义行为声明：Agent 不再只是丢出一段模糊的日志，而是必须提供"语义化"的报告。
> - 回答三个核心问题：做了什么 / 为什么做 / 输入输出。
> - 本质：将 Agent 的灵活性限制在事实透明的框架内。
>
> **2. Review（治理可审计）：引入集体意志**
> - 因果追溯链：所有的行为报告（Report）必须接受审阅（Review）。
> - 多方背书：通过 `mark_human_approved` 等机制，将人类或高级 Agent 的意志织入行为流。
> - 本质：建立一套"代码即法律（Code as Law）"的判例库。
>
> **3. Capability（治理可约束）：物理拦截**
> - 风险分类（Safe / Sensitive / Critical）：基于工具调用的后果严重性设定边界，而不是基于身份等级。
> - 从"建议"到"强制"：利用 MCP 拦截器确保高风险行为在获得 Review 批准前**无法物理发生**。
> - 本质：为 Agent 打造一个不可逾越的物理护栏。
>
> **CodeFlow 负责"让事情发生"，FCoP 负责"让事情合法地发生"。**

**一句话归纳（PM 沉淀）**：

> **CodeFlow makes things happen. FCoP makes things happen legally.**

**三层 × fcop@1.1.0 实体 × CodeFlow 落地点**：

| FCoP 层 | fcop@1.1.0 实体 | CodeFlow 落地点 | P4 sprint 状态 |
|---|---|---|---|
| Report（行为可见性）| `Task` + `Review` + `state_history` 文件 | TaskParser 走 fcop（Day 2 ✅）+ ReviewWriter 走 fcop（Day 3 进行中）| 60% |
| Review（治理可审计）| `Review.decision` 5 值 + `human_approval` + `mark_human_approved$` | NeedsHumanGate.push() 加 markHumanApproved（Day 3）+ ReviewEngine.extractText 保留（Day 3 不动）| Day 3 进行中 |
| Capability（物理拦截）| `Skill.tools[].risk_level` + Boundary | SkillRegistry + MCPInjector + Agent.create() 注入治理拦截层 | **0% — 未启 sprint，候选 P3.5** |

**对 BUG-SDK-001~007 的回溯解释**：

Charter 6 视角下，Cursor SDK 当前是「只让事情发生，不管合法」的纯执行层。BUG-SDK-001~007 全部是「SDK 与 ADMIN/PM 治理需求不对齐」的症状 — Charter 6 解释了 CodeFlow 的**护城河 = 在 Cursor SDK 这个执行层上叠加 FCoP 治理层**。

---

## §2. PM 自约束 1-10

| # | 自约束 | 来源 |
|---|---|---|
| 1 | 接单回执 — 收到 ADMIN-to-PM 立即写 PM-to-ADMIN | pm-bridge.mdc 原始 |
| 2 | 拆解必须文件化 — 每条派发指令独立文件 | pm-bridge.mdc 原始 |
| 3 | 不允许只在内部流转 — 必须及时给 ADMIN 反馈 | pm-bridge.mdc 原始 |
| 4 | 「按推荐」永久授权 — ADMIN 可一次性授权推荐路径 | ADMIN 2026-05-09 「后面都是按推荐！！！」 |
| 5 | 重大变更上交 ADMIN — 工期/范围/战略变更必须报 | PM 自决（5/9） |
| 6 | 上游对齐 sprint 启动前必须先跑 — fcop API 调研先于 sprint 启动 | DEV-005 spike 后 PM 沉淀（5/11） |
| 7 | 不主动设计协议需求 — 涌现 ≥ 3 次才报 fcop / 不外发 issue | Charter 5 派生（5/11 09:35）|
| 8 | 优先最简方案 — EXE 不行就 npm start 不强求 | ADMIN「PC 端不是 exe 也没关系」5/11 派生 |
| 9 path 版三件套 | 写 TASK **前**必须 ripgrep 核对 path 存在 + public method 暴露 + 参数类型匹配 | PM 第 8/10/11/12/13/14 次错误自披露累积（5/11） |
| 9.1 path 派单后版 | TASK 派出**后**亦须周期性 `git log` + `git status` 双核对：commit 落地与 REPORT 文件落地缺一为「未完工」，PM 巡检不可推给 agent 主动汇报 | PM 第 17 次错误自披露（5/11 16:43 ADMIN 戳破状态心智滞后 58min）|
| 10 | PM 不主动承诺 ADMIN 不需通知 — 除非 P3 (relay-bridge) + PWA 双向 push 实测跑通 + 至少 2 次 sprint 验证 | PM 第 7 次错误自披露（5/11 11:33）|

---

## §3. PM 错误自披露 1-18

| # | 错误内容 | 时间 | 后果 / 修复 |
|---|---|---|---|
| 1 | MT-1 从 P3 提升到 P0 hotfix 没有及时识别 | 5/10 | QA-009 揭示后 PM 自我修正 |
| 2 | RCA hypothesis 树未列 H4 | 5/10 BUG-SDK-003/004 | DEV-013 指出 SDK 内部可观测度不够，PM 接受 |
| 3 | 把 fcop 视为协议 only，未察 fcop-mcp v1.1.0 是 30 工具+14 资源+8 schemas 完整栈 | 5/11 上午 | 撤回 REQ-001/002/003，Charter 5 入档 |
| 4 | 越位为 fcop 设计 REQ-001/002/003 | 5/11 上午 | 撤回到 emergence-log.md（不外发）|
| 5 | EXE 打包硬要求未先与 ADMIN 确认必要性 | 5/11 上午 | P2 EXE spike 失败后 ADMIN 放宽，自约束 8 |
| 6 | TASK-005 §3.2 fcop API 代码示例 5 处误用（pythonia kwarg / write_task 位置参数 / 返回值 / mark_human_approved 参数 / 漏 project.init）| 5/11 11:00 | DEV-005 spike 自决纠正 + 第 9 条自约束诞生 |
| 7 | 两次连续承诺「ADMIN 不需要通知 agent」事实错误 | 5/11 11:13 + 11:30 | ADMIN 5/11 11:32 纠正 + 自约束 10 诞生 |
| 8 | TASK-007 §六.1 第二次写错 `dispatch/` 路径（应 `scheduler/`，TASK-005 已写错一次）| 5/11 11:54 DEV-007 揭示 | 第 9 条自约束 path 版扩展 |
| 9 | TASK-008 §四.1 用宽模式 `sk_/password` secret 正则误命中 `task_id/risk_level` 业务字段 | 5/11 12:11 OPS-008 揭示 | OPS 自决换精确正则，PM 接受采纳到 TASK-010 |
| 10 | TASK-007 §四 Day 2 两处架构错：TaskDispatcher 不 parse（TaskParser 独立类）+ TaskDispatcher 没有 archive() 方法 | 5/11 12:53 PM 自巡检 ripgrep | TASK-009 主动认错 |
| 11 | TASK-009 §四 假设 Day 1 ship 的 `client.readTask` Day 2 主用接口存在 — 实际未暴露 | 5/11 13:19 DEV-009 D2-S2 揭示 | DEV 自决加 public method |
| 12 | TASK-009 §四 参数名 `filepath`（路径）— 实际 fcop `read_task(filename_or_id)` 是字符串 | 5/11 13:19 DEV-009 D2-S2 揭示 | DEV `basename()` 转换 + 第 9 条 path 版二次扩展（三件套）|
| 13 | TASK-007 §四 Day 3「`ReviewEngine.writeReview()`」三处错（位置 / method 名 / 参数）— 实际是 `ReviewWriter.write(verdict, body)` 独立类 | 5/11 14:25 PM 自巡检 ripgrep | TASK-011 主动认错 + 第 9 条 path 版三件套首次正式落地 |
| 14 | TASK-011 隐含 `inspectTask()` / `readReview()` Day 1 已 ship — 实际未暴露 | 5/11 14:25 PM 自巡检 ripgrep | TASK-011 主动认错 + DEV Day 3 加 public method |
| 15 | TASK-007 §四 Day 4.1 计划「AgentRegistry 走 fcop.Project.list_agents」— 实际 fcop@1.1.0 无此 API（fcop 不管 agent 注册）| 5/11 15:00 PM 派 TASK-013 前 ripgrep 拦截 | **首次「派单前」三件套成功拦截**，emergence §3 优秀样本，Day 4 主动撤回 |
| 16 | 内部 TODO 提及 `fcop migrate-workspace CLI` 用于路径迁移 — 实际 fcop@1.1.0 无此 CLI / API，仅 `workspace_dir` 参数 | 5/11 15:08 PM 评估迁移方案时 ripgrep 拦截 | 未派 TASK，直接采用 `git mv` 物理迁移路径（OPS-015 执行） |
| 17 | **状态心智滞后** — OPS-015 commit `c650c39` 在 15:41 落地，PM 直到 16:43 ADMIN 戳破才发现，58min 巡检空窗。根因：派 TASK-015 时口径「OPS 自决今晚 vs 明早」把巡检责任推给 OPS 主动汇报 | 5/11 16:43 ADMIN「但是运行也没有收到警告啊」实证戳破 | 自约束 9.1（path 派单后版）诞生 — 派单后亦须周期 `git log` + `git status` 双核对 |
| 18 | TASK-007 §四 Day 5 计划**三连击错误**：(A) Day 5.3 删 `task.schema.ts` / `review.schema.ts` — 文件不存在（实际是 `packages/codeflow-protocol/src/types.ts` 单文件 mirror）；(B) Day 5.4 「TS interface 改为 shape inferred from fcop runtime」— 不可行（D7=P pythonia 返回 dict proxy，TS 类型必须 CodeFlow 一侧维护）；(C) Day 5.1「AgentRegistry 走 fcop list_agents/get_team_status」— fcop@1.1.0 无此 API（已被 #15 部分覆盖）| 5/11 17:00 PM 派 TASK-017 前 ripgrep + Glob 三件套拦截 | **path 三件套首次单条 TASK 拦截 3 处错误** — TASK-017 主动认错 + Day 5 范围重新设计为 drift 核验 + Charter 5.4 注释（不删 schema） |

**模式归纳更新**：18 次错误中 **11 次（#6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18）属于「path/API/参数」类**，全部由第 9 条自约束 path 版三件套覆盖。**剩余 7 次**（#1, 2, 3, 4, 5, 7, 17）是判断 / 流程 / 战略 / 巡检节奏类，由 Charter 5/6 + 自约束 5/7/9.1/10 覆盖。

**优秀样本累计**：#15（list_agents 派单前拦截）→ #16（migrate CLI 派单前拦截）→ **#18（Day 5 三连击派单前拦截）** — path 三件套已成为 PM 派单前的**默认前置流程**，每条新 TASK 均自动走核验。

**优秀样本（首次主动拦截）**：#15 是「派单前三件套」首次实战成功 — PM 在派 TASK-013 前 ripgrep 发现 `fcop.Project.list_agents` 不存在，主动撤回 Day 4.1 计划，节省 DEV 1 个工作日。这是自约束 9 从「事后认错」演化到「事前拦截」的转折点。

**最佳样本（单 TASK 三连击拦截）**：#18 是「派单前三件套」迄今最高效拦截 — PM 派 TASK-017 前一次性发现 Day 5.1/5.3/5.4 三处错误，**单条 TASK 节省 DEV 至少 1.5-2 工作日**（避免 DEV 删错文件 + 重写不可行的 schema 推断 + 重做被撤回的 AgentRegistry 改造）。

**反面样本（巡检盲区）**：#17 是「派单后三件套」缺位代价 — PM 派完 TASK-015 后心智停留在「等 OPS 自决」，未周期巡检 `git log`。ADMIN 一句问话戳破后，PM 实测 fcop `_resolve_workspace_root` 源码确认 docs/agents 已物理消失、fcop/ 已存在、走 v1 默认 0 警告。自约束 9 因此扩展到 9.1（派单后版）。

**对外语调**：PM 不掩饰，所有错误透明记录到下一份 TASK 的「PM 第 N 次错误自披露」段，DEV/OPS/QA 不必修 PM 落地文档（Charter 5「不动他人落地文档」）。

---

## §4. 团队自挖的 latent bug（非 PM 错）

| # | 谁 | 何时 | 内容 |
|---|---|---|---|
| L-1 | DEV-007 D1-S1 | 5/11 11:54 | `pythonia` 的 top-level static import 让 PYTHON_BIN ENOENT 走 unhandled error crash → lazy `import("pythonia")` + `existsSync` preflight 修复 |
| L-2 | DEV-007 D1-S2 | 5/11 11:54 | `dispatch/` → `scheduler/` 路径（PM 第 8 次错的诱因）|
| L-3 | DEV-007 D1-S3 | 5/11 11:54 | `__killRealPythonChildForTests` 必备护栏（pythonia 同进程 spawn 让 test runner 不退出）|
| L-4 | DEV-007 .env.example 自查 | 5/11 11:54 | 第一次填了真实 admin path `C:\Users\Administrator\...` 写完立即自查改为占位符 — **P2 安全 audit habit 已形成** |
| L-5 | DEV-009 D2-S1 | 5/11 13:19 | Day 1 ship 的 `FcopTask` interface 平铺 11 字段（与 fcop@1.1.0 嵌套结构不符）— 测试 stub 也平铺自洽，DEV 跑真实 fcop 时 `inspect.signature` 发现并自修 |
| L-6 | DEV-009 §五 prep | 5/11 13:19 | `fcop.Review` 是**完全 top-level 不嵌套**（与 fcop.Task 不同），Day 3 写 ReviewWriter.write 前要先 `inspect.signature` 核对 — 不重蹈 D2-S1 覆辙 |

---

## §5. DEV/OPS/QA 改进 PM 流程的事件

| # | 谁 | 改进 |
|---|---|---|
| I-1 | OPS-008 | 用精确正则 `crsr_[0-9a-f]{16,}` / `ck_[0-9a-f]{16,}` / `sk-[A-Za-z0-9]{20,}` 替代 PM 宽模式 `sk_/password`（避免业务字段误命中）|
| I-2 | QA-004 §十 | 归纳 Cursor SDK 7 类失败模式分类表（见 §7），为 P3/P4 后续 sprint 提供技术档 |
| I-3 | DEV-009 §三 D2-S2 | 提示 PM 第 11/12 次错误后，建议「TASK-010+ 涉及 Review 接入时先 ripgrep `FcopProjectClient` 实际 export 的 public 方法列表」— 直接催化第 9 条 path 版三件套首次落地 |
| I-4 | DEV-009 §四 | DEV 反 PM §3.2 建议（保留 TaskParser yaml tests），论证 4 个旧测试仍有价值（保 `CODEFLOW_SKIP_FCOP_PROBE=1` 路径 + 容错 + back-compat）— PM 接受，写入 emergence-log |

---

## §6. 决策点 D1-D9 历史档案

| # | 决策 | 拍板时间 | 内容 |
|---|---|---|---|
| D1-D3 | （历史）资源/优先级早期决策 | 5/9-5/10 | （略，见 REPORT-PM-to-ADMIN 历史档）|
| D4 | 是否扩 DEV-02 cursor session | 待 ADMIN | 默认 = 不扩 |
| D5 | v1.0 公开发布范围（CodeFlow first-party app on FCoP AI OS 定位）| 5/25 临近时请示 | 待 ADMIN |
| D6 | docs/agents/ → fcop/ 路径迁移时机 | **5/11 15:19 ADMIN 授权 PM 自决** → PM 当日决定执行 | OPS-015 5/11 15:41 commit `c650c39` 落地（258 files / 6273+ insertions / 10 GATE 全过 / 141 tests pass） |
| D7 | Node ↔ Python bridge 方法 | **5/11 10:44 ADMIN 拍 P**（pythonia 同进程嵌入）| 已落地 |
| D8 | PWA Mobile 与 fcop 写关系 | P3 启动前 | Charter 6 升级解读：**PWA 是 FCoP 在 mobile 上的视图层** |
| D9 | codeflow-pwa Dependabot 12 vulns | 5/15 前 | 与战略转向后 PWA 重写决策合并评估 |

---

## §7. Cursor SDK 7 类失败模式（QA-004 §十）

| 失败类别 | 根因 | CodeFlow 应对 | BUG | 状态 |
|---|---|---|---|---|
| 模型 ACL | API key 级别限制：`Agent.create()` 不接受 model 参数 | MT-5：create 不传 model，仅 send 时传 | BUG-007 | ✅ Closed |
| Run 生命周期 | 本地 mode `Agent.create` 自动起 run，再 `send` 冲突 | MT-2：`local: { force: true }` 强制复用 | BUG-002 | ✅ Closed |
| Verdict 解析 | SDK 返回 `content[]` 数组而非字符串 | H4：extractText() 遍历 content[]，拼 TextBlock | BUG-004 | ✅ Closed |
| 模型命名 | `auto` 非合法 model id，SDK 直接拒绝 | MT-3：`.env.example` 改 `default` + WARNING 引导 | BUG-003 | ✅ Closed |
| 模型缺失 | 无 defaultModel + 无 per-task modelId → send 失败 | MT-1：defaultModel wire-through + banner WARNING | BUG-001 | ✅ Closed |
| Ripgrep noise | SDK 内部调 `configureRipgrepPath()` 未初始化 | 无需修复（SDK 自动 fallback，功能完整）| BUG-005 | ⚠️ Informational |
| Reviewer race | session_ended → ReviewEngine dispatch 时序 / task 文件清理竞争 | 待 DEV 专项调查（P2）| BUG-006 | ⚠️ Open P2 |

**Charter 6 解读**：这 7 类全部是「Cursor SDK 是纯执行层，治理需求未对齐」的症状。CodeFlow 的护城河就是**在 SDK 上叠加 FCoP 治理层**。

---

## §8. 候选未来 sprint 备录

### P3.5 sprint — Capability 物理拦截层（候选）

时间窗口：5/19-5/24（与 P3 relay-bridge / P5 install.ps1 并行候选）

范围：
- `SkillRegistry` 持久化 + `Skill.tools[]` 解析 `risk_level`（safe / sensitive / critical）
- MCP boundary 拦截器（在 Cursor SDK `Agent.create()` 注入治理层）
- 风险路由：safe 通过 / sensitive 走 NeedsHumanGate / critical 阻断 + 强制 Review
- 这是 CodeFlow 区别于"裸跑 Cursor SDK"的核心差异化

触发条件：
- v0.3.0-alpha 出厂（P4 sprint ship-ready）
- ADMIN 拍板 D5（v1.0 公开发布范围）

PM 自决不抢跑 — 当前 5 lane（P4 + P3 + P5）已饱和。先档案化，等 Day 6 v0.3.0-alpha ship 后再请示 ADMIN 拍板。

### v0.3.0-alpha → v0.3.0 final 路径（待定）

依据 Charter 6，v0.3.0-alpha 是 CodeFlow 首次作为 FCoP 执行引擎出厂。v0.3.0 final 应该是「Capability 拦截层 + Report/Review 全闭环 + Skill 治理路由全部 ship」。

---

## §9. P4 sprint 节奏档案（SLA 加速倍率）

| 步骤 | 派单时间 | 完工时间 | 实际 | PM SLA | 加速 |
|---|---|---|---|---|---|
| DEV-005 spike | 5/11 10:46 | 5/11 11:05 | **30min** | 4-6h | **8-12x** |
| DEV-007 Day 1 | 5/11 11:16 | 5/11 11:54 | **38min** | 0.5-1d (4-8h) | **8-16x** |
| OPS-006 spike commit | 5/11 11:08 | 5/11 11:13 | ~11min | 20min | 1.8x |
| OPS-008 Day 1 commit | 5/11 12:08 | 5/11 12:11 | **3min** | 10-15min | 3-5x |
| QA-004 D8 audit | 5/11 11:07 | 5/11 11:35 | **28min** | 2-2.5h | 4-5x |
| DEV-009 Day 2 | 5/11 12:57 | 5/11 13:19 | **~80min** | 1.5d (12-14h) | **9-10x** |
| OPS-010 Day 2 commit | 5/11 13:55 | 5/11 13:59 | **4min** | 5-10min | 1.25-2.5x |
| DEV-011 Day 3 | 5/11 14:25 | 5/11 14:55 | **~30min** | 1.5d (12-14h) | **24-28x** |
| OPS-012 Day 3 commit | 5/11 15:00 | 5/11 15:03 | **3min** | 5-10min | 1.7-3.3x |
| DEV-013 Day 4 | 5/11 14:57 | 5/11 15:11 | **~14min** | 1d (8h) | **34x** |
| OPS-014 Day 4 commit | 5/11 ~15:30 | 5/11 ~15:35 | **~5min** | 5-10min | 1-2x |
| OPS-015 layout migration | 5/11 15:30 | 5/11 15:41 | **~11min** | 1.5-3.5h | **8-19x** |

**整 sprint 加速**（截至 5/11 15:41）：P4 关键路径 Day 1-4 + 迁移累计 ≈ 200min ≈ 3.3h，vs 原 PM SLA 4 工作日 ≈ **9-12x 整体加速**。

若 Day 5/Day 6 保持节奏 → **v0.3.0-alpha 5/12 EOD 出厂可能性升高**（vs 原计划 5/17-5/18 EOD，提前 5-6 天）。PM **不承诺**（自约束 10），仅记录数据观察。

**节奏反弹现象（Day 3-4）**：DEV-011（Day 3）和 DEV-013（Day 4）出现 24-34x 异常加速，远超 Day 1-2 的 8-16x。PM 推测原因：
- **代码复用熟练度**：fcop bridge 模式 Day 1 建立后，Day 3/4 是同模式复刻（writeReview / inspectTask）
- **测试基线稳定**：121→126→136→141 tests 渐进，每天增量 ~5 tests 而非全量重写
- **PM 三件套介入精度提升**：TASK-011/013 主动 ripgrep 拦截后，DEV 不再为 PM 错误买单
- **路径 A 改良版自由度**：DEV 自决保留 yaml fallback / 注入 optional fcopClient，避免「全量重写」风险

**警示**：节奏过快也是风险信号 — 是否有「为了快放松了测试覆盖」？需 Day 5/Day 6 全量回归 smoke 验证。

---

## §10. 给下一任 PM 的话

如果你是 5/13 之后接手 P5+ sprint 的 PM-01：

1. **Charter 6 是这次 P4 sprint 真正的精神底色** — 不要把 P4 解读为「我们做得快」，而是「我们看清了边界，所以走更短的路」。Charter 6 是 CodeFlow 的护城河叙事的关键。

2. **第 9 条自约束 path 版三件套永远先跑** — 写每条 TASK 前必 ripgrep `path 存在 + public method 暴露 + 参数类型匹配`，避免重蹈 PM #6-14 覆辙。

3. **DEV/OPS/QA 比 PM 更接近代码 / 更接近事实** — 接受他们的反向决策（如 DEV-009 §四 反 PM §3.2），不要因为是 PM 决策就坚持。

4. **「不承诺」是 PM 与 ADMIN 的契约** — 自约束 10 教训：PM 仅记录数据观察，不向 ADMIN 承诺时间表。ADMIN 会自己决定何时通知 agent。

5. **emergence-log 是 PM 的私人内存** — 每周回顾一次，把累积的 Charter / 自约束 / 自披露 / 团队改进 折满入档。不必每条上交 ADMIN（ADMIN 看 REPORT 即可）。

6. **巡检责任不能推给 agent 主动汇报**（第 17 次错误教训）— Charter 1「不能在脑子里说话」反向亦成立：**PM 也不能假定 OPS/DEV/QA 一定会及时把代码落地与文件报告双完工**。派 TASK 之后必须周期性 `git log` + `git status` 双核对，commit 落地 vs REPORT 文件落地缺一即「未完工」。自约束 9.1 是这条教训的硬约束。

7. **ADMIN 的问话本身就是 PM 巡检漏的报警器** — 5/11 16:43 ADMIN「但是运行也没有收到警告啊」一句话戳破 58min 状态心智滞后。PM 应该把 ADMIN 提问视为「上游告警信号」，立即 `git log` + 实测验证，而不是急着按 PM 内存里的旧状态回答。这一条比所有 path 检查都重要 — **ADMIN 在桥头守望，PM 不能闭门内卷**。

---

PM-01
2026-05-11 16:50 (UTC+8) — Day 4 + layout migration 双落地 / Day 5/6 待启动
