# CodeFlow AI Runtime — 设计文档

> **官方定位（SINGLE SOURCE OF TRUTH）：**
>
> > **CodeFlow AI Runtime**
> > *A lightweight AI Operating Runtime for multi-agent software development.*
>
> 状态：DRAFT · 起草人：ADMIN-01 + DEV-01（spike 验证后落笔）
> 日期：2026-05-09
> 当前主线版本：v2（v1 = "Cursor 外挂"形态，已规划下线，详见 §1.1 / §8）
> 关联：[FCoP 公仓](https://joinwell52-ai.github.io/FCoP/) · [Cursor SDK 文档](https://cursor.com/docs/api/sdk/typescript) · [论坛门铃 issue #158480](https://forum.cursor.com/t/feature-request-chat-notify-primitive-we-already-have-the-mailbox-files-we-just-need-the-doorbell/158480)

---

## 0.0 Executive Summary（1 屏读完）

> ### 📜 项目宪法（ADMIN 5/9 四总纲句，原话锁定）
>
> 1. ADMIN 5/9 10:48 — **身份 + 技术栈**：
>    > 「**这个项目文件就是码流的，目前项目是用 cursor 的 sdk，应用 fcop-mcp。**」
>
> 2. ADMIN 5/9 10:51 — **真正定位**：
>    > 「**码流是做成一个 CodeFlow 的真正定位：一个面向多 Agent 协作开发的轻量级 AI Runtime / AI OS。**」
>
> 3. ADMIN 5/9 13:51 — **协议本体的定位**：
>    > 「**5 类 Schema 真正应该变成：**
>    > **Task Schema = 定义目标与约束 / Agent Schema = 定义能力边界 /**
>    > **Session Schema = 定义运行上下文 / Review Schema = 定义治理规则 /**
>    > **Skill Schema = 定义可调用能力。**
>    > **❌ 不要：定义固定动作。**
>    > **✅ 而要：定义"约束 + 能力 + 状态 + 权限"，然后让 Agent 自己完成规划 / 协作 / 拆解 / 实现。**
>    > **现在真正做的，不是『控制 Agent』，而是『为 Agent 提供一个不会崩溃的协作宇宙』。**」
>
> 4. ADMIN 5/9 14:46 — **ADMIN 治理角色定位**：
>    > 「**等你们这个版本开发完，我就不需要每个去通知了；我应该只需要下达、审批、变更，等权力角色所做的事了。**」
>
> 解读（这四句联合定义了 v2 项目的全部边界）：
>
> | 句中关键词 | 锁定的含义 |
> |---|---|
> | 「**码流的**」 | 本仓 = CodeFlow 项目，**不是** fcop 项目 → §8.0 硬规则 #5 |
> | 「**用 cursor 的 sdk**」 | 主线技术栈 = `@cursor/sdk` → §1.2 + §0.7 身份反转（不是 IDE 外挂、不是 OCR、不是 CDP） |
> | 「**应用 fcop-mcp**」 | 角色 = consumer / downstream → §8.0 硬规则 #5（只消费、不生产） |
> | 「**面向多 Agent 协作开发**」 | scope = 开发型 AI Runtime → §0.8 first-phase scoping（不是通用 AI OS） |
> | 「**轻量级**」 | 风格约束 → §0.8.3 v0.1 6 条硬约束（拒绝 ERP / 大平台思维） |
> | 「**AI Runtime / AI OS**」 | 技术层级 = L2/L3 → §0.6 三层栈（不是 L1 AI Tool） |
> | 「**协作宇宙**」 | 协议层 = agent 自主决策的**边界条件**（哈密顿量 + 约束），**不是**轨迹脚本 → §3.0 设计哲学 |
> | 「**不需要每个去通知**」 | Runtime 自己负责唤醒 agent（chokidar inbox + Mobile push）→ §2.4 + §0.9.3 + §10.2 S3 Phase C |
> | 「**下达**」 | dispatch — 写 `TASK-{date}-{seq}-ADMIN-to-PM.md` → 触发 PM 调度链 → §3.3 Task state_history |
> | 「**审批**」 | review — 在 Mobile PWA 对 `needs_human` 决策点拍板 → §0.9.4 HITL + §3.4 Review Schema |
> | 「**变更**」 | escalate — 改优先级 / 撤销 / 重新分派 → §3.3 Task state_history 自动追加 |
> | 「**权力角色所做的事**」 | Governance Plane 的全部职责（**不下沉**到 Worker）→ §0.9.1 三层组织 + §0.7.5 v2 产品定位 |
>
> 英文 tagline `A lightweight AI Operating Runtime for multi-agent software development`（line 5-6）= 上述第 2 条的英文官方表述。
>
> **任何后续修改如果与这四句矛盾，必须先经 ADMIN 显式授权改动这一节。**

---

> 后续 §0-§11 共约 1800 行。如果你只有 60 秒，看完这一节就够。

### 6 句话理解 v2

1. **CodeFlow ≠ Cursor 外挂**。CodeFlow = **Agent Runtime**；Cursor / Claude Code / Codex 只是被驱动的执行终端。
2. **第一阶段只做"开发型"AI Runtime**——服务多 Agent 软件开发，不做通用 AI OS / 万能 Agent / 企业全场景。
3. **Mobile-first Governance**：手机不是通知端，是 *AI Runtime Remote Governance Plane*——AI 24h 跑，人不必坐电脑前。
4. **fcop-mcp 是内核（强依赖）**，启动校验缺它就拒绝加载。其他 MCP 是设备驱动，可选。
5. **真正护城河 = Agent Governability**（Agent 可治理化）+ **Human-in-the-loop via Mobile**（人侧治理）。
6. **核心交付物 = §3 Runtime Protocol（5 类 schema）**——对位 Linux POSIX / Docker OCI / K8s CRD。**先做内核，生态自己长**。

### 6 张概念表（架构地图）

#### A. v1 → v2 身份反转

| 维度 | v1（Cursor 外挂） | v2（Agent Runtime） |
|---|---|---|
| 项目身份 | IDE 增强工具 | AI 团队的"操作运行时" |
| Cursor 角色 | 必须依附 | 执行终端（可被 Claude Code/Codex 替换） |
| 主驱动 | UI 点击 / 巡检 | SDK `Agent.create/resume` |

#### B. 三节点拓扑（Mobile = Governance Plane）

| 节点 | 角色 | 为什么不可替代 |
|---|---|---|
| 📱 Mobile | **Governance Plane** | 人不在电脑前也能审批 / 急停 |
| 💻 Local PC | Execution Plane | 唯一能改本地代码 / 跑内网 |
| ☁️ Cloud | Execution Plane | 唯一能 24×7 不下线 |

#### C. 三层组织结构（roles.yaml `layer:` 字段）

| Layer | 角色 | 权限边界 |
|---|---|---|
| **L3 Admin** | ADMIN（人） | 内核态，唯一可打断/覆盖/回滚 |
| **L2 Governance** | REVIEW / SECURITY / AUDIT / PATROL | 签发 Review，路由到 Human |
| **L1 Worker** | DEV / PM / OPS / TEST / DOC | 纯执行，结果必经 Governance 审 |

#### D. 6 大 Kernel 子系统（§2.1）

| # | 子系统 | OS 类比 |
|---|---|---|
| 1 | Session Manager | 进程调度器（会话层） |
| 2 | Task Scheduler | scheduler（doorbell） |
| 3 | Agent Registry | PCB 表 |
| 4 | Skill Runtime | 动态库 + syscall 路由 |
| 5 | **Review Engine** ⭐ | 权限系统（chmod/sudo）—— **最关键** |
| 6 | State Store | 文件系统 + journal log |

#### E. 5 类 Runtime Schema（§3，v2 真正的核心交付物）

| Schema | 文件位置 | 对位 |
|---|---|---|
| Agent | `.codeflow/state/agents/<id>.json` | 线程 |
| Task | `tasks/**/*.md` (FCoP) | 进程 |
| Review | `REVIEW-*.md` | chmod/sudo 决策 |
| Session | `.codeflow/state/sessions/<id>.json` | 进程上下文 |
| Skill | `skills/<id>.json` | 动态库 / driver |

#### F. v0.1 → v1.0 路线图（§10）

| 版本 | 周期 | 核心 |
|---|---|---|
| v0.1 | 6 周 | Backend kernel：PM→DEV→REVIEW→DONE 文件化闭环（零 UI） |
| v0.2 | 4 周 | Mobile Governance MVP：4 屏 + Approval + 🛑 |
| v0.3 | 3 周 | AI Patrol（5 类异常巡检） |
| v0.5 | 4 周 | Review Board（REVIEW + SECURITY + AUDIT 共识） |
| v1.0 | 9 周 | §3 Schema 冻结 + 第一批外部实现 |

### 看完后该看什么？

| 你的角色 | 接下来读 |
|---|---|
| 想理解 *为什么* 这么做 | §0.5（AI OS 雏形） + §0.6（三层栈 + 护城河） + §0.7（身份反转） |
| 想理解 *做什么 / 不做什么* | §0.8（first-phase scoping） + §0.9（Mobile-first Governance） |
| 想动手实现 | §3（5 类 schema） + §10（sprint plan） |
| 想知道 v1 怎么退役 | §1.1（v1 vs v2 对照） + §8（迁移路径） |
| 只想跑起来一个 demo | §0.8.3（Hello World 验收脚本） |

> 📌 §0.0 是给 *第一次接触 v2* 的读者的速读卡。
> 任何后续修改 v2 重大方向的会议，应先从这一节开始对齐。
> 这一节的内容如果改，全文都要扫一遍——它是 **整份文档的"摘要-之-摘要"**。

---

## 0. 摘要

> **一句话定调：**
>
> > CodeFlow 不是在做"AI 自动写代码"，而是在做 **"让 AI 团队稳定工作的操作系统内核"**。

**CodeFlow AI Runtime（v2）** 是 FCoP 协议的参考实现，把两个 host-neutral 组件粘起来：

- **协议层**：FCoP（文件即消息总线，Zenodo DOI [10.5281/zenodo.19886036](https://doi.org/10.5281/zenodo.19886036)）
- **运行时层**：`@cursor/sdk`（agent 持久会话 + 跨进程 resume + 多模型统一接口）

v1 的核心 hack —— 用巡检引擎 UI-click 唤醒 Cursor IDE chat tab —— **彻底退役**。
v2 让每个 FCoP 角色变成一个长生命期的 SDK agent，通过 `Agent.resume(agentId).send(...)` 实现"门铃"语义，
不再依赖 Cursor 桌面端，不再要求 PC 解锁，不再受 IDE chat tab 数量限制。

**六句话定调：**

1. **身份反转**：CodeFlow ≠ Cursor 外挂。**CodeFlow = Agent Runtime，Cursor = 执行终端（之一）**。详见 §0.7。
2. **第一阶段聚焦 = 开发型 AI Runtime**：不做通用 AI OS、不做万能 Agent、不做企业全场景。只服务 AI 软件开发的 multi-agent 协作 / Task / Review / 审计。详见 §0.8。
3. **角色可选**：用户的 `roles.yaml` 决定团队编制（不再硬编码 PM/DEV/QA/OPS）。
4. **PC + 云端 + 手机三节点可选**：每个角色按需选 `runtime: local | cloud`，加上 mobile 指挥端，构成分布式 Agent Runtime。
5. **fcop-mcp 是内核（强依赖）**：`mcpServers` 必须挂 fcop，否则启动校验拒绝加载。其他 MCP（git / playwright / sql）是设备驱动，可选。
6. **Mobile-first Governance**：手机不是"通知端"，而是 *AI Runtime Remote Governance* —— Human Admin 在哪都能看 Task Flow / 看 Agent / 审 Review / 紧急停机。AI 24h 跑，人类不必坐电脑前。详见 §0.9。

**官方副定位（与正式名 `CodeFlow AI Runtime` 一并使用）：**

> *Mobile-first AI Runtime for governable multi-agent software development.*

CodeFlow v2 的意义不止于"重写"——它把 FCoP 从"协议 + Python 实现"扩展成"**协议 + 双语言双运行时 + 三节点分布式拓扑**"，
反过来 dogfood 自己宿主的协议。

更进一步——见 §0.5、§0.6、§0.7、§0.8——它是 **AI OS（Agent Runtime Infrastructure）** 在"开发型"垂直方向的一个雏形。
v2 的核心交付物不是"应用"，而是 **§3 定义的 Runtime Protocol（5 类 schema）**——对位 Linux POSIX / Docker OCI / K8s CRD。

> **关于"CodeFlow"这个名字**：
> 早期含义偏向"代码流 / 工作流"。在 §0.7 身份反转之后，它的真正含义浮现出来——
> **CodeFlow = AI Agent Flow Runtime = AI 团队的运行流**。
> "Code" 指代的不是字面意义的代码，而是协议化、文件化、可审计化的"行为流"。

---

## 0.5 关于 "AI OS 雏形"

> **ADMIN-01 在 review 第一刀时给出的判断：**
>
> > "这个可能 AI OS 的雏形。"

这不是过度修辞。把 CodeFlow v2 的组件跟传统操作系统对照看，**每一个 OS 概念都能在 v2 里找到对应物**——而且对应得很整齐：

| 传统 OS 概念 | AI OS（CodeFlow v2）对应物 | 备注 |
|---|---|---|
| **进程 (Process)** | **Task**（FCoP `TASK-*.md`） | 工作单元，有 lifecycle / state / owner / 可阻塞、可挂起 |
| **线程 (Thread)** | **Agent**（SDK agent 实例） | 执行上下文，可并发承接多个 Task |
| 进程控制块 (PCB) | `.codeflow/state/agents.json` + Task front-matter | 元数据持久化 |
| 文件系统 | **Task Store**（`docs/agents/tasks/`） | FCoP 协议规定的目录布局，所有 Task 与状态流转都在这 |
| 进程间通信 (IPC) | **FCoP** | 文件即消息总线，致敬 Plan 9 "everything is a file" |
| 系统调用 (syscall) | **MCP tool call** | agent → adapter 的 ABI |
| **kernel 子系统** | **`fcop-mcp`** | syscall 调度层，所有 agent 工具调用必经它（OS *实现* 层面） |
| **内核态 (Ring 0)** | **ADMIN** | 唯一可越过协议直接干预的权限主体（OS *权限* 层面） |
| **用户态 (Ring 3)** | **Skill** | Agent 在协议框架内行使的能力 |
| **权限系统** (chmod / sudo) | **Review** | QA / approval / role-check 是 AI OS 的 chmod/sudo |
| 设备驱动 (Driver) | **Adapter**（其他 MCP：git / playwright / sql / ...） | 提供具体能力，但都在 kernel 管辖下 |
| init / systemd | CodeFlow Lifecycle Manager | 启动 / 监控 / 停止全部 agent 进程 |
| 调度器 (scheduler) | Inbox Watcher | 事件驱动（Task 落地）触发 Agent 上工 |
| 守护进程 (daemon) | 24×7 云端监控 worker | 永远在线、不依赖用户登录 |
| Shell | **Chat UI**（PWA / fcop CLI / 文本编辑器） | 用户与 AI OS 的交互入口 |

> **注意 "kernel 子系统" 与 "内核态" 的区别**：
> - **kernel 子系统**（fcop-mcp）= OS 的*实现层*，所有 syscall 必经的 dispatch 中枢
> - **内核态**（ADMIN）= OS 的*权限环*，唯一能越过协议干预的主体
>
> 这是同一个"内核"概念在不同层面的两个切面。fcop-mcp 是"内核做什么"，ADMIN 是"谁在内核态"。

### 为什么 `fcop-mcp` 在这个映射里被定位成 "kernel"？

来自 ADMIN 的第二条决定性判断：

> "这个 SDK 本来是 Cursor 的，只有加了 `fcop` 才能让 agent 有纪律！
> 也就是所有的 MCP，都应该用 `fcop` 保证正确性！"

裸 SDK 给 agent 的能力是"无纪律的"——它能读任何文件、跑任何 shell、改任何代码，
但**不知道何时该停下来写 REPORT、何时该弹 ISSUE、何时该 role-switch**。

`fcop-mcp` 提供的就是这一层"语法和纪律"——把无形的协议规范固化成 agent 能调用的 tool，
并通过 tool 描述（schema docstring）把"什么时候该做什么"教给 LLM。
这正是 [FCoP Essay 04《让 LLM 说"不"——FCoP 给它语法》](https://joinwell52-ai.github.io/FCoP/) 在做的事，
现在被工程化成了 v2 的**强依赖**。

**v2 的 schema 校验硬约束一条**：
> 任何角色的 `mcp` 列表里 **必须包含 `fcop`**，否则 CodeFlow 启动时拒绝加载该角色。
> 其他 MCP（`git` / `playwright` / `sql`）只是"设备驱动"，可选；`fcop` 是"内核"，必选。

### 跟传统 OS 的 4 个本质差别

不要被对照表带偏——CodeFlow v2 跟 Linux 内核有 4 个根本差别：

| 维度 | 传统 OS | CodeFlow v2 |
|---|---|---|
| 进程是什么 | 确定性图灵机（指令逐条执行） | 概率推理引擎（同输入可能给不同输出） |
| 调度公平性 | 时间片轮转 / 优先级 | 不调度 CPU，调度的是 agent 的"注意力" |
| 系统调用语义 | 完全确定（`read` 就是读字节） | 有歧义（`read` tool 由 LLM 根据上下文选目标） |
| 故障模型 | crash → core dump | hallucinate → 协议违反 → `ISSUE-*.md` |

正是这 4 个差别，让"AI OS"不能照抄 Linux 设计。
但反过来——**FCoP 提供的"协议纪律 + 文件即 IPC"恰好是这 4 个差别下唯一能站得住的协调机制**：
确定性的文件名 + 确定性的目录约定 + 确定性的协议语义 ＝ 给概率性 agent 划出一条可观察、可审计、可恢复的轨道。

这就是为什么这条路走得通：
**把 AI OS 的"内核"建在 FCoP 文件协议之上，而不是建在某种新的 RPC 框架之上。**

> 📌 这一章不是 marketing 语言。它是 v2 后续所有设计决策的"定理"——
> 后面 §1-§10 里凡是出现"为什么要这么设计"的问题，都可以回到这里找答案。

---

## 0.6 三层栈、外部状态系统、与下一阶段

### 0.6.1 AI 系统的三层栈：我们在哪、要去哪

市面上叫"AI OS"的东西大多数都不是 OS。
按系统抽象层次拆，目前所有 AI 应用都落在以下三层之一：

| 层 | 形态 | 代表做法 | 价值上限 |
|---|---|---|---|
| **L1：AI Tool** | LLM + Tool Call + Workflow | 自动 SQL / 自动报表 / 自动客服 / Zapier-like 编排 | 单点提效，本质是"工作流自动化"换皮 |
| **L2：AI Runtime** ← *CodeFlow v2 在这* | Task Runtime + Review Engine + Skill System + State Store | 你能调度多 agent，agent 能跨进程持久化，状态全部协议化 | 多 agent 长期协作 |
| **L3：AI OS（终局）** | Agent 调度 + 长期记忆 + 权限体系 + 多租户 + 企业治理 + Skill 市场 + 自进化规则 | 还没有真正的开源参考实现 | 取代 / 包裹 ERP，成为企业 AI 中枢 |

**很多自称 "AI OS" 的项目其实只到 L1**——LLM + Function Call + 一点 workflow 编排，本质是工作流自动化换了个名字。
L1 → L2 的跃迁需要"持久化 + 协议化 + 状态可恢复"这三件事，正好是 `@cursor/sdk` + FCoP 这个组合解决的。

CodeFlow v2 = **L2 的一个具体实现**，并且是为 L3 留好接口的实现。

### 0.6.2 FCoP = AI 的"外部状态系统"

L1 → L2 的关键跃迁是给 AI 一个"外部状态系统"。
原因很简单：LLM 的内部状态（context window）有 3 个根本缺陷——

| 缺陷 | 后果 |
|---|---|
| **易失** | 进程退出 / context 满了，状态归零 |
| **不可见** | 你只能看输入输出，看不到中间推理过的什么 |
| **不可审计** | 出错后无法回放、无法定责、无法举证 |

FCoP 干的事就一件：

```
AI 脑内状态
      ↓ 文件化       （写到磁盘，进程退出不丢）
      ↓ 协议化       （文件名 + YAML 头有规范，机器可读）
      ↓ 可审计       （git log + Markdown diff，人/AI 都能查）
```

**这就是 FCoP 在 AI OS 里的真正定位——它不是"协议"那么简单，它是 AI 的 *state externalization layer*。**

放到对应的 OS 类比里：FCoP 之于 LLM agent，等同于 **文件系统 + 进程持久化 + journal log** 之于传统 OS 进程。
没有这一层，AI 就永远停在"会话级智能"，进不了"系统级智能"。

### 0.6.3 v2 的精确定位句

如果只能用一句话定位 CodeFlow v2，是这句：

> **CodeFlow v2 = Linux + Workflow + LLM 的混合体，但多了一样别人没有的 —— FCoP 协议层**

这句话每一段都不能省：
- **Linux** —— 进程/线程/IPC/调度/权限的概念结构
- **Workflow** —— Task 状态机的可编排性
- **LLM** —— 真正干活的执行引擎
- **FCoP** —— 让前面三个能"长期稳定协作"的协议层（**这是稀缺差异**）

### 0.6.4 不要走的歧路：UI-first / OCR / 聊天窗口 / SaaS 心态

> ⚠️ **下一阶段最危险的 4 个诱惑**：

| 诱惑 | 为什么是死路 | 替代立场 |
|---|---|---|
| **UI-first**（先做漂亮 PWA / dashboard） | 内核没成立前，UI 会消化掉所有团队精力 | 先做 kernel，UI 最后 |
| **OCR / CDP 主路线** | OCR/CDP 是"观察 AI"，治本是"驱动 AI"——SDK 才是治本 | OCR/CDP 仅作 fallback；主路线 = SDK / Protocol / Runtime |
| **聊天窗口思维** | 把 AI OS 误当 chatbot，错把"对话"当核心 | 真正的核心是 Task / State / Review / Execution |
| **AI SaaS 定位** | 把 v2 包装成 SaaS 卖订阅，赛道挤、护城河浅 | 定位 = AI Runtime Infrastructure（这个赛道还没成型） |

**类比参考**：Linux 早期没有漂亮 UI；Docker 最初没有生态；Kubernetes 一开始很难用。
它们的共同点是 **先把内核做成立**，然后生态会自己长出来。

**v2 的开发优先级硬规则：**

1. **先：** Task Runtime + Agent Lifecycle + State Store + Inbox Watcher（**内核四件套**）
2. **再：** Review Engine + Skill Registry + Adapter 权限（**kernel-grade 的 OS 服务**）
3. **再：** Runtime Protocol & Schemas 冻结发布（**对位 POSIX / OCI / CRD**，详见 §3）
4. **最后：** UI / chat / dashboard / 任何用户可视化（**生态层**）

倒过来做 = 死路。

> 📌 这条优先级是"宪法级"约束——任何 PR / 任何 sprint 计划如果违反它，应该被回退到设计阶段重审。

### 0.6.5 v2 的下一个学科：Runtime Engineering

到 L2 之后，关键工程能力不再是"prompt engineering"或"model fine-tuning"，
而是一个还没被广泛命名的新学科——**Runtime Engineering**：

| 关注点 | 包含内容 |
|---|---|
| **Task 生命周期** | 创建 / 派发 / 阻塞 / 重试 / 回滚 / 归档 |
| **状态流转** | inbox → in-progress → review → done / blocked / cancelled |
| **Agent 调度** | 谁来接 / 何时接 / 接不下来谁接 / 优先级 / 公平性 |
| **Review 系统** | 谁有权 review / 什么需要 review / review 失败怎么回滚 |
| **Skill 注册** | agent 能调哪些 skill（MCP tool）/ skill 升降级 / skill 版本 |
| **Adapter 权限** | 哪些 adapter 暴露给哪些 role / 横向越权防护 |
| **可观察性** | run 转录 / agent 健康度 / 协议违反告警 |
| **跨进程恢复** | 进程崩 / 机器宕 / VM 漂移后怎么不丢 task |

这一组能力组合起来，才有资格叫 "AI OS 的 init 系统"。

### 0.6.6 终局：AI OS 可能就是下一代 ERP

把镜头拉到 5 年尺度，企业 IT 的形态可能从——

```
旧：  员工 ──> ERP ──> 业务系统 ──> 数据库
```

变成——

```
新：  员工
       ↓
     AI OS（CodeFlow v2 这一类）
       ↓
     多个 Agent
       ↓
     业务系统 / 数据库 / API / RPA
```

**这不是科幻：**

- ERP 的本质是"把企业流程编码成不变的状态机 + UI"
- AI OS 的本质是"让 agent 在 FCoP 协议框架下，按需动态生成并执行流程"
- 后者既能做 ERP 该做的事，又能做 ERP 永远做不到的事（自适应、跨边界、跨形态）

所以"有些企业甚至不再需要传统 ERP"不是幻想，是 AI OS 长期形态的一个直接推论。

> 📌 §0.6 是 §0.5 的"为什么"。
> §0.5 告诉你 v2 *怎么* 像 OS；§0.6 告诉你 v2 *为什么要* 像 OS、为什么这一步不可逾越、终局长什么样。
>
> 后面 §1-§11 都是 §0.6 的工程兑现。任何设计决策只要不能用 §0.6 的某条原则解释，
> 大概率是走偏了，要回头检查。

### 0.6.7 真正的护城河：Agent Governability（Agent 可治理化）

经过 §0.5/§0.6 的拆解，CodeFlow 的护城河 **既不是 UI，也不是 prompt 调优，更不是模型选型**——而是一个目前极少有人触及的层：

> **Agent Governability ─ Agent 可治理化**
>
> 让一群概率性的 LLM agent，能在 *可观察、可审计、可恢复、可问责* 的协议框架下长期协作。

这一层的关键能力（`@cursor/sdk` 不提供，需要 v2 自己造）：

| 能力 | 解决什么 | v2 的实现位置 |
|---|---|---|
| **行为可观察** | LLM 内部状态不可见 | §3.5 Session + §2.5 Event Renderer |
| **决策可审计** | 出错无法回放 | §3.4 Review Schema + §3.5 Session |
| **状态可恢复** | 进程崩了状态丢光 | §3.2 Agent Schema + §3.3 Task state_history |
| **角色可问责** | 谁干的、谁批的、谁背锅 | §3.4 Review Schema 的 `reviewer_role` + Task 的 `state_history.by` |
| **协议可演进** | 系统不能永远 freeze 在 v0.1 | §3.7/§3.8 schema 演进策略 |

**为什么"Agent 可治理化"是真正的护城河？**

- UI 是表层：用户能看到的，竞争对手 1 个月就能 copy
- prompt 是黑盒：模型升级后 prompt 失效，护不住
- 模型是平台方的：永远不会被 wrapper 真正拥有
- **协议化的治理框架**：要 0-to-1 创造，需要长期 dogfood 沉淀，竞争对手补不出来

FCoP 已经在 protocol 层做了 0-to-1 创造（[Zenodo DOI](https://doi.org/10.5281/zenodo.19886036) + 6 篇 essay 沉淀）。
v2 要做的就是**把这个协议层 + 5 类 Runtime Schema + 6 大 kernel 子系统组合起来，构成一套可治理的 Agent Runtime**。

这就是护城河。

**护城河的 *人侧* 一半：Human-in-the-loop via Mobile（详见 §0.9）。**

Agent Governability 解决"AI 做的事可治理"，但还缺最后一公里——**当 AI 触到高风险红线（删数据/发生产/改权限）时，谁拍最终板子？**

答案是 **Human Admin via Mobile**：

- 24h 跑的 AI Agent + 不可能 24h 在电脑前的人 → 必须有 Mobile 治理面板
- 高风险操作 → 触发 mobile push → 人类点"准/否"才放行
- 紧急情况 → mobile 上一个红色按钮停掉所有 agent

这一半护城河别人更难抄——它要求 *Runtime + Mobile UI + 推送链路 + 协议化 approval flow* 端到端打通。
绝大多数 AI Agent 框架到今天为止还假设"人坐在电脑前用 IDE"，根本没想过 Mobile 治理这件事。

### 0.6.8 Docker 前夜类比：v2 在做的是 Agent Runtime 标准化

CodeFlow v2 在历史时间线里的位置 ≈ **"AI 时代的 Docker 前夜"**。

| 维度 | Docker 前 | Docker 后 |
|---|---|---|
| 程序运行 | 环境差异、依赖打架、不可迁移 | OCI 镜像 / 运行时标准化 |
| 团队协作 | "在我机器上能跑" | 跨开发机/CI/生产环境一致 |
| 生态扩展 | 每个工具自己一套打包 | 围绕 OCI 长出 K8s/podman/cri-o 等 |

| 维度 | Agent 当下 | CodeFlow v2 之后 |
|---|---|---|
| Agent 运行 | 各家框架各自实现，状态不可恢复，行为不可审计 | **Runtime Protocol 标准化**（§3 五类 schema） |
| 多 Agent 协作 | 自定义消息总线 / 紧耦合 / 难以替换 | **FCoP 文件即 IPC**，host-neutral |
| 生态扩展 | 每个新 Agent / Skill 都要重新对接 | 按 §3.6 Skill Schema 注册即可接入 |

**Docker 解决的是"程序运行时怎么标准化"，v2 解决的是"Agent 运行时怎么标准化"。**

护城河的本质是一样的——**先成为标准，再让生态自动长出来**。

> 📌 这一节锁住了 v2 的"为什么值得做"。
> 后面 §1-§11 任何"功能要不要做"的争论，都可以回到 §0.6.7（治理化）和 §0.6.8（标准化）找答案。
> 不能强化治理化或标准化的功能 = 偏离主线 = 应该后置或砍掉。

---

## 0.7 身份反转：从 Cursor 外挂到 Agent Runtime

> **ADMIN-01 在 §0.6 review 后给出的下一刀判断（identity-level 升级）：**
>
> > "CodeFlow ≠ Cursor 外挂。**CodeFlow = Agent Runtime，Cursor = 执行终端。**"

这是 CodeFlow 项目级的身份反转——不是命名变化，是**定位变化**。
配合 §0.6 的"AI OS = 下一代 ERP"，这一章把 v2 在 AI Runtime 赛道的具体形态彻底锁死。

### 0.7.1 旧定位（v1）的 3 个长期隐患

CodeFlow v1 把自己定位成"Cursor 的 ADMIN 桌面工具"，留下 3 个无法靠工程优化解决的隐患：

| 隐患 | 后果 |
|---|---|
| **"外挂"心态** | 必然依附 Cursor 的 UI / API / 生命周期，受制于宿主的版本升级、UI 变更、license 变化 |
| **OCR/CDP 主路线** | OCR 和 CDP 是"**观察 AI**"（被动看截图、抓 DOM），永远做不到"驱动 AI"（主动发指令） |
| **聊天窗口思维** | 把 agent 对话当核心，忽略了 task / state / review / execution 这些更本质的维度 |

### 0.7.2 新定位（v2）的关键反转

| 维度 | 旧（v1） | 新（v2） |
|---|---|---|
| 项目身份 | Cursor 外挂 | **Agent Runtime** |
| Cursor 的角色 | 宿主 / 容器 | **执行终端**（之一，可被替换为 Claude Code / Codex / 本地 ollama） |
| 主驱动机制 | OCR / CDP 观察 IDE 状态 | **SDK 直接驱动 agent**（OCR/CDP 仅作 fallback） |
| 用户意图入口 | Cursor IDE chat tab | **Task 文件 + ADMIN 调度** |
| 核心能力名称 | "控制 Cursor" | **"管理 Agent Session"** |
| 产品赛道 | AI 工具 / IDE 插件 | **AI Runtime Infrastructure** |

> ⚡ **"驱动" vs "观察" 是哲学差异，不是技术选型差异。**
>
> - OCR/CDP = "我能看到 Cursor 现在显示什么" → 被动旁观，治标
> - SDK = "我能让 agent 现在做什么" → 主动调度，治本
>
> v2 选 SDK 不是因为 SDK 更新更快，是因为只有 SDK 能让 CodeFlow 真正成为 *Runtime*。

### 0.7.3 4 个特殊优势（CodeFlow 在 AI Runtime 赛道的差异化）

| 优势 | 别人补不出来的原因 |
|---|---|
| **FCoP 协议** | 协议层是 0-to-1 创造的，已经 Zenodo DOI 备案 + 6 篇 essay 沉淀，工程优化补不出协议护城河 |
| **Filename as Protocol** | 已经很像 **Event Sourcing + AI Runtime** 的混合体——文件名即事件流，目录即状态机 |
| **多 Agent 分工** | PM/DEV/QA/OPS 已经接近真实组织结构，比 LangGraph / AutoGen 那种"工作流编排"更贴近 AI 团队的实际形态 |
| **Mobile + PC + Cloud 三节点** | "Agent 不应被锁在 IDE 里"——这是 AI Runtime 行业的关键认知，绝大多数同类项目还死守"AI 在 IDE 里"假设 |

### 0.7.4 三节点分布式 Agent Runtime

```
                ┌──────────────────────────────────────┐
                │ 📱 Mobile Node (PWA) ⭐ Governance Plane │
                │   AI Runtime Remote Governance         │
                │   - Task Flow / Agent 状态 / Review    │
                │   - Human-in-the-loop approval         │
                │   - 🛑 Emergency Stop                   │
                │   ─ 详见 §0.9 ─                        │
                └────────────┬─────────────────────────────┘
                             │
                             │ (WebSocket relay / HTTP)
                             ▼
                ┌─────────────────────────────┐
                │ 🧠 CodeFlow Runtime           │
                │   (Session/Task/Review/...)   │
                │   ─ 可部署在 PC 或 Cloud ─    │
                └─┬───────────────────────────┬─┘
                  │                           │
                  │ (SDK calls)               │ (SDK calls)
                  ▼                           ▼
   ┌─────────────────────────┐  ┌──────────────────────────┐
   │ 💻 Local Node (PC)       │  │ ☁️  Cloud Node (Server)   │
   │   - Cursor / Claude Code │  │   - 长任务 / CI/CD       │
   │   - Codex / 本地 ollama  │  │   - 自动部署 / Review    │
   │   - Local SDK agent      │  │   - RAG / 24×7 daemon    │
   │   - 改本地代码 / 跑内网  │  │   - 跨时区跨地点         │
   └─────────────────────────┘  └──────────────────────────┘
```

**三节点各自的不可替代性：**

| 节点 | 不可替代的价值 | 角色定位 |
|---|---|---|
| 📱 **Mobile** | 指挥 + 治理永远跟在人身边——AI 24h 跑，人不必坐电脑前 | **Governance Plane**（治理面） |
| 💻 Local PC | 唯一能直接访问本地代码 / 内网凭证 / 本地 IDE 的节点 | Execution Plane（本地执行面） |
| ☁️ Cloud | 唯一能 24×7 不下线 / 跨时区 / 提供干净 VM 环境的节点 | Execution Plane（云执行面） |

**关键认知 1**：Cursor 在这个图里只是 Local Node 上的 *一个* 执行终端，不是 CodeFlow 的宿主。
未来 Local Node 还可以挂：Claude Code / Codex / 本地 ollama agent / 任何 SDK 兼容的执行器。

**关键认知 2（新增）**：Mobile **不是** "PC 节点的 input proxy"，而是 *独立的 Governance Plane*。
传统认知里"手机控制 PC"=远程控制；CodeFlow 的认知是 *"手机治理一群 24h 跑的 Agent"* —— 这是 **AI Runtime Remote Governance**，是一个完整的产品形态。
完整 Mobile spec 见 **§0.9 Mobile-first Governance**。

### 0.7.5 v2 的产品定位句（SINGLE SOURCE OF TRUTH）

> **CodeFlow AI Runtime**
>
> *A lightweight AI Operating Runtime for multi-agent software development.*
>
> 中文：**面向多 Agent 软件开发的轻量级 AI 操作运行时**

**Mobile-first 副定位（与正式定位并列使用）：**

> *Mobile-first AI Runtime for governable multi-agent software development.*
>
> 中文：**移动优先、可治理的多 Agent 软件开发运行时**

加上 *Mobile-first* 这个限定词，是为了和市场上"假设人坐电脑前"的所有 AI 开发工具做明确区隔。完整论述见 §0.9。

**为什么不叫 "AI OS"？** —— 见 §0.8 first-phase scoping：
v2 第一阶段 *只* 做"开发型 AI Runtime"，不做通用 AI OS。叫 "AI OS" 会过度承诺、提前撑大 scope。
"Runtime" 是更准确、更克制、也更符合工程现状的命名。

**关于 "CodeFlow" 这个名字的真正含义：**

| 阶段 | 含义 |
|---|---|
| 早期（v1） | "代码流 / 工作流" —— 像 IDE 增强工具 |
| **现在（v2）** | **AI Agent Flow Runtime —— AI 团队的运行流** |

"Code" 不是字面意义的代码，而是协议化、文件化、可审计化的"行为流"。
"Flow" 不是 workflow，而是 Agent 之间通过 FCoP 文件传递的"事件流"。

> 🔁 **身份反转的工程后果（务必读 §8 + §8.0）：**
>
> - v2 不是 v1 的"下一个版本"，而是 *彻底换了身份的产品形态*；v1 / v2 *共享* `codeflow-pwa` 仓库，但作为 *不同身份的产品* 共生（v1 freeze 维护 + v2 新身份开发）——详见 §8 章首
> - 协议演进的唯一合法仓库 = `D:\FCoP`，不是本仓——本仓 `packages/codeflow-protocol/` 只能 *镜像* FCoP spec，不能 *单边创造* schema——详见 §8.0 硬规则 #4

CodeFlow v2 **不是**：

- ❌ AI 聊天工具
- ❌ Cursor 插件 / IDE 扩展
- ❌ 自动化工具 / Workflow SaaS
- ❌ 又一个 AutoGen/LangGraph 翻版
- ❌ "通用 AI OS" / "万能 Agent" / "企业全场景 AI 平台"（详见 §0.8 收窄）

CodeFlow v2 **是**：

- ✅ **Task 系统**（FCoP 协议，文件即消息）
- ✅ **Agent Runtime**（SDK 驱动的多 agent 调度）
- ✅ **Review Engine**（QA/审批/角色权限——v2 的*最核心*子系统，详见 §2.1） ⭐
- ✅ **Multi-Node**（Mobile / Local / Cloud 三节点）
- ✅ **IDE Driver**（Cursor / Claude Code / Codex 都是被驱动的执行终端）

> 📌 §0.7 锁死了 v2 的 *身份*。
> 后面 §1-§11 任何设计决策如果跟"Agent Runtime + 三节点 + IDE Driver"这个身份冲突，
> 不是设计错就是身份错——必须先解决这个冲突再继续。

---

## 0.8 First-phase scoping：先做"开发型 AI Runtime"，不做通用 AI OS

§0.5/§0.6/§0.7 把 v2 抬到了"AI OS 雏形"的高度。这一节则要**主动收窄**——
告诉自己第一阶段哪些不做、哪些必须先做、最小闭环长什么样。

### 0.8.1 第一阶段：开发型 AI Runtime（不是通用 AI OS）

| 维度 | ❌ 第一阶段不做 | ✅ 第一阶段聚焦 |
|---|---|---|
| 适用场景 | 通用 AI OS / 万能 Agent / 企业全场景（销售、客服、HR、财务……） | **AI 软件开发**：multi-agent 编程协作 |
| 用户画像 | 任意业务用户 / 大厂员工 / 普通消费者 | **AI 产品研发团队 / 重度 AI 编程用户**（自己就是第一批用户，dogfood） |
| 核心场景 | "什么都能做"的对话 | **Task / Code / Review / 审计** 闭环 |
| 商业形态 | SaaS 平台 / Marketplace / 收订阅 | **Runtime 内核 + 协议**（先把内核做稳，生态再说） |
| 横向整合 | 集成 ERP / OA / CRM / 数据库 | 只接 Code / Git / IDE / Test / Deploy |

**类比 Linux 早期**：
Linus 没有先做桌面、没有先做游戏、没有先做办公软件——
**先做一个稳定的内核，跑得起 GCC 和 Bash**，然后让生态自己长出来。
v2 的第一阶段同理：**先做能跑稳"AI 团队写代码"的内核**，其他场景往后放。

> 💡 **为什么收窄？**
>
> 1. **Dogfood 优势**：v2 的开发者本身就是 AI 编程团队，第一批用户就是自己，反馈最快、迭代最准。
> 2. **场景密度高**：AI 编程一天能产生几十次 Task / Review / Decision，是验证 Runtime 协议最高密度的场景。
> 3. **避免提前抽象**：通用 AI OS 现在做出来一定是脑补——必须先在一个高密度垂直场景里把协议磨穿。
> 4. **错位竞争**：所有大厂都在做"通用 AI Agent 平台"，v2 反而专注"AI 写代码这件事的 Runtime"，错位。

### 0.8.2 v0.1 最小闭环：`PM → DEV → REVIEW → DONE`

v0.1 **唯一**要证明的事是：

> 一个 Runtime 能稳定驱动一个 4 状态的 Agent 流水线，
> 全程文件化、可追溯、可恢复、可审计，**不依赖任何 UI**。

**最小闭环数据流：**

```text
ADMIN（人）
  │ 写 TASK-*-ADMIN-to-PM.md
  ▼
PM-01 (Agent)
  │ 拆解 → TASK-*-PM-to-DEV.md
  ▼
DEV-01 (Agent)
  │ 实现 → REPORT-*-DEV-to-REVIEW.md
  ▼
REVIEW-01 (Agent)
  │ 审核 → review.md (verdict: approved/rejected)
  ▼
[approved] → 状态机 done
[rejected] → 回 DEV，循环 ≤ N 次
```

**v0.1 的硬约束（任何一项不达成都不能算完成）：**

| # | 约束 | 验收方式 |
|---|---|---|
| 1 | 全流程**零 UI**（除 ADMIN 写第一个文件） | 关掉 Cursor IDE 也能跑完 |
| 2 | 所有状态变更**写文件**（FCoP `state_history` + `review.md`） | 任意时刻 `cat tasks/` 能还原全部状态 |
| 3 | 进程崩了**能恢复**（基于 §3.2 Agent Schema 的 `last_active_run_id` + `Agent.resume()`） | kill -9 后重启 daemon，所有 agent 自动续上 |
| 4 | 每一步**有 reviewer 角色** | review.md 必须有 `reviewer_role` 字段，不能匿名 |
| 5 | **不依赖云端**（全本地可跑） | 仅需本地 PC + cursor API key，无需任何云服务 |
| 6 | **fcop-mcp 是强依赖**（启动校验拒绝无 fcop 的角色） | 见 §2.2 schema 校验规则 |

**v0.1 *显式不做*：**

- ❌ 手机端 PWA / 移动指挥（v0.2 再说）
- ❌ 云端 cloud agent（v0.2 再说）
- ❌ Skill marketplace（v0.3 再说）
- ❌ 企业多租户 / 权限矩阵（v0.5 再说）
- ❌ 任何 UI 美化、控制台、报表（永远不是 v0.x 的事）
- ❌ 通用业务集成（ERP/CRM/工单系统/IM 推送）

### 0.8.3 v0.1 的"Hello World" Demo 验收脚本

任何"v0.1 是否完成"的争论，都用以下 demo 脚本判定：

```bash
# 1. ADMIN 写一个真实的小需求
echo "把 README 里的 'Cursor 外挂' 全部替换为 'Agent Runtime'" \
  > tasks/inbox/TASK-20260601-001-ADMIN-to-PM.md

# 2. 启动 runtime（一行命令，不开 IDE）
codeflow runtime start --roles roles.yaml

# 3. 等待最多 N 分钟
codeflow runtime wait --task TASK-20260601-001 --timeout 600

# 4. 验收：tasks/done/ 下应有完整的 4 文件链
ls tasks/done/TASK-20260601-001/
# 期望输出：
#   TASK-20260601-001-ADMIN-to-PM.md
#   TASK-20260601-001-PM-to-DEV.md
#   REPORT-20260601-001-DEV-to-REVIEW.md
#   REVIEW-20260601-001.md  (verdict: approved)
#   state.json              (state_history 完整)

# 5. 杀进程恢复测试
codeflow runtime start ... &
sleep 30 && kill -9 $!
codeflow runtime start ...     # 应自动续接
```

**这个 demo 跑通 = v0.1 完成。跑不通 = v0.1 没完成，不要往下做 v0.2。**

**v0.2 是什么？** —— v0.2 = **Mobile Governance MVP**，也就是把 §0.9 的 Mobile-first Governance 跑通最小子集。
v0.1 解决"AI 团队能不能稳定干活"，v0.2 解决"Human Admin 怎么在沙发上治理它"。

> 📌 §0.8 锁死了 v2 *第一阶段的边界*。
>
> §0.5/§0.6/§0.7 是**愿景**——它们告诉我们 v2 的天花板在 AI OS。
> §0.8 是**第一阶段**——它告诉我们 v0.1 只能做这么多，多一寸都是越界。
>
> 后续 §10 路线图必须以 §0.8.2 的 6 条硬约束为 v0.1 验收标准。

---

## 0.9 Mobile-first Governance：Human Admin = AI Runtime 的最终治理层

§0.7.4 把 Mobile 列为三节点之一，但 *没说清楚它和另外两个节点本质不同在哪*。这一节把它说清楚。

> **核心论点：**
> Mobile 不是 PC 节点的"input proxy / 通知器"，而是 **AI Runtime 的 Governance Plane（治理面）**——
> 它和"AI 自动化执行"是 *正交* 的两个产品形态，缺谁都不成立。

### 0.9.1 三层组织结构：Worker / Governance / Human Admin

CodeFlow v2 的角色体系，按治理层级重新分组：

```
┌────────────────────────────────────────────────────────────┐
│  L3: Human Admin                       👤 ADMIN            │
│       ─ "最终 boss"                    📱 Mobile-only       │
│       ─ 高风险红线决策                  ─ 谁也撤不掉的角色  │
└──────────────────────┬─────────────────────────────────────┘
                       │ approve / reject / 🛑
                       ▼
┌────────────────────────────────────────────────────────────┐
│  L2: AI Governance Layer               🤖 治理类 Agent      │
│       ─ 协议化 + 可审计                                     │
│       ─ REVIEW-01 (代码 review)                             │
│       ─ AUDIT-01  (合规审计)                                │
│       ─ SECURITY-01 (安全审计)  ⭐ 新角色（详见 §0.9.5）    │
│       ─ PATROL-01 (Agent 巡检)  ⭐ 新角色（详见 §0.9.5）    │
└──────────────────────┬─────────────────────────────────────┘
                       │ assign task / route review
                       ▼
┌────────────────────────────────────────────────────────────┐
│  L1: AI Worker Layer                   🤖 执行类 Agent       │
│       ─ 不带治理职能，纯生产力                              │
│       ─ DEV-01 (写代码) / TEST-01 (跑测试)                  │
│       ─ DOC-01 (写文档) / OPS-01 (部署)                     │
│       ─ PM-01 (拆解任务)                                    │
└────────────────────────────────────────────────────────────┘
```

**三层结构的两个铁律：**

1. **L1 → L2 → L3 单向依赖**：Worker 的产物必须经 Governance 审，Governance 的高风险结论必须经 Human Admin 拍板。**反向不允许**——Worker 不能绕过 Governance 直接找 Human。
2. **L3 是"内核态"**：Human Admin 的指令具有最高优先级，可以打断、覆盖、回滚 L1/L2 的任何决策。这是 §0.5 OS 类比中"内核态 vs 用户态"的具体落地。

> 📌 这个三层结构是 *roles.yaml 的隐含 schema*。
> §2.2 角色注册表会显式加 `layer: worker | governance | admin` 字段，运行时按 layer 强制约束权限边界。

### 0.9.2 Mobile = AI Team Console（不是 Chat Box）

Mobile 端的产品形态判定：

| 形态 | 选不选 | 理由 |
|---|---|---|
| ❌ AI 聊天框 | 不选 | "对着 AI 聊天"是 L1 的事，不是 L3 的事 |
| ❌ Prompt 调试台 | 不选 | 那是开发者工具，不是治理工具 |
| ❌ 文档查看器 | 不选 | 没有"治理动作"就不算治理面 |
| ✅ **AI Team Console**（运维控制台风格） | **选** | 类比：K8s Dashboard / Datadog / PagerDuty 的合体，加 AI 治理 |

类比一句话：**CodeFlow Mobile ≈ "K8s Dashboard + DevOps + AI Runtime"，且 Mobile-first**。

K8s Dashboard 让运维不在终端也能管 cluster；
CodeFlow Mobile 让 Admin 不在 IDE 也能管一群 Agent。

### 0.9.3 Mobile 必须显示的 4 屏（v0.2 MVP 范围）

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 1. Task Flow     │  │ 2. Agent 状态    │  │ 3. Audit 通知    │  │ 4. Approval 审批 │
│  (核心)          │  │                  │  │  (重点)          │  │  (关键)          │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ TASK-1001        │  │ ● DEV-01  运行中 │  │ ⚠️ SECURITY-01    │  │ 待你拍板:        │
│  Reviewing       │  │ ● PM-01   等待   │  │   SQL 缺 tenant  │  │                  │
│  by REVIEW-01    │  │ ● REVIEW-01 审计 │  │   _id, 是否继续? │  │ TASK-1003        │
│  Risk: Medium    │  │ ● PATROL-01 巡检 │  │                  │  │  发布到生产?     │
│                  │  │ ○ DOC-01  空闲   │  │ [查看详情]       │  │                  │
│ TASK-1002        │  │                  │  │                  │  │ [✓ 准]  [✗ 否]   │
│  Done ✓          │  │ Cloud 节点:2 在线│  │ 历史审计: 17 条  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

**四屏 ≠ 四个独立 tab**：它们共享同一个事件流（FCoP 文件 watcher），只是不同的视图聚合。

| # | 屏 | 数据源 | 关键交互 |
|---|---|---|---|
| 1 | Task Flow | `tasks/**/*.md` 的 Task Schema | 看进度 / 看链路 / 跳到具体 Task |
| 2 | Agent 状态 | Agent Schema + Session Schema | 看谁在跑 / 谁卡死 / 强制重启 |
| 3 | Audit 通知 | Review Schema 中 `severity ≥ medium` 的事件 | 推送 + 历史查询 |
| 4 | Approval | Review Schema 中 `verdict: needs_human` | **一键 approve/reject** |

### 0.9.4 Human-in-the-loop 触发条件（高风险红线）

哪些事 *必须* 经 Mobile approval、不能让 AI 自决？以下是 v0.2 的初版红线清单：

| 类别 | 具体动作 | 触发方式 |
|---|---|---|
| **数据破坏类** | 删数据库表 / drop schema / `rm -rf` 项目目录 | Skill Runtime 拦截 → 转 needs_human Review |
| **生产环境类** | 部署到 production / 修改生产配置 / restart 生产服务 | OPS 类 Agent 默认无生产权限，需提权 |
| **权限类** | 改 `roles.yaml` / 改 MCP 注入 / 撤销 Reviewer | 任何对 Runtime 自身的修改 |
| **协议类** | 修改 `.codeflow/protocol/*.schema.json`（v0.1 freeze 期内） | 改协议 = 改宪法 |
| **资金类** | 调外部计费 API / 触发付费云资源 | 事先在 roles.yaml 标注 `cost_sensitive: true` 的 Skill |
| **不可逆操作** | force push / 删 git tag / 公开发布 | git 类 Skill 标注 `irreversible: true` |

**实现**：每个 Skill（MCP tool）在 Skill Schema 里声明 `risk_level`（详见 §3.6）。
Skill Runtime 在调用前检查 risk_level → 高风险 → 自动构造 `REVIEW-*-needs_human.md` → push 到 Mobile → 等 approval。

> 📌 这一段是把 §0.6.7 *人侧* 那一半护城河落到工程上。
> 没有这套红线机制，再强的 Agent Runtime 也只是 "可怜的 demo"，企业不敢用。

### 0.9.5 三种未来 Governance Capability（v0.2+）

#### A. AI Patrol（巡检 Agent）—— v1 patrol 引擎的"灵魂转世"

> v1 的 patrol 引擎是"用 UI 点击叫醒 Cursor"——是个工程 hack。
> v2 的 PATROL-01 是"用 SDK 巡检一群 Agent 是否健康"——是个治理角色。
> 名字相同，本质完全相反：v1 patrol 服务于 *执行*，v2 patrol 服务于 *治理*。

PATROL-01 的职责：

- ⏰ 周期 / 事件触发，扫所有 Agent 的 Session 文件
- 🔍 检查 5 类异常：
  1. **漂移**：Agent 行为偏离 brief（用 brief vs recent transcripts 做 LLM-judge）
  2. **卡死**：Session `status: running` 但超过阈值无新事件
  3. **越权**：调用了 brief 未授权的 MCP tool
  4. **长期无响应**：Inbox 已堆积 N 个 Task 但 Agent 未消费
  5. **协议违规**：写出的文件不符合 FCoP Schema
- 📤 异常即 push 到 Mobile（→ §0.9.3 第 3 屏 Audit）

#### B. AI Review Board（多 reviewer 共识）

> 单 reviewer 的盲区，靠 multi-reviewer 互锁解决。

REVIEW Board 模型：

```yaml
# roles.yaml 片段
review_board:
  enabled: true
  members:
    - REVIEW-01    # 业务/代码 review
    - SECURITY-01  # 安全 review
    - AUDIT-01     # 合规 review
  policies:
    high_risk:
      require_consensus: 2   # 至少 2 票同意
      include_security: true # SECURITY-01 必须参与
    normal:
      require_consensus: 1   # 单 reviewer 即可
```

实现：Review Engine（§2.1.1）按 Task 的 `risk_level` 选 policy，路由到对应的 board members，等共识达成。

#### C. Mobile Emergency Stop 🛑

最简单也最关键的功能：**Mobile 上一个红色按钮，按一下停掉所有 Agent。**

实现：
- Mobile 发出 `EMERGENCY_STOP` 事件 → Runtime
- Runtime → Session Manager → 对所有 in-progress Run 调用 `run.cancel()`
- 落 `EMERGENCY-{timestamp}.md` 文件（包含触发人、时间、当时 in-progress 的所有 Task ID）
- 所有 Agent 状态置 `paused`，等 Human 解除

> 📌 这三个 capability 不是 v0.1 范围，但**架构必须为它们留口**。
> 任何 §1-§9 的设计都不能让这三个 capability 变成"以后做不了"。

### 0.9.6 Staged delivery：v0.1 / v0.2 / v0.3 路径

| 版本 | 目标 | 包含的 Mobile 能力 |
|---|---|---|
| **v0.1** | Backend kernel：PM→DEV→REVIEW→DONE 文件化闭环 | ❌ 完全无 Mobile（CLI + 文件即可验收） |
| **v0.2** | **Mobile Governance MVP** | ✅ §0.9.3 的 4 屏只读 + §0.9.4 高风险 approval + 🛑 Emergency Stop |
| **v0.3** | 治理深化 | ✅ AI Patrol（PATROL-01 接入） |
| **v0.5** | 多 reviewer 共识 | ✅ AI Review Board (含 SECURITY-01) |
| **v1.0** | 协议冻结 + 第一批外部用户 | ✅ 完整 Mobile-first AI Runtime |

> 📌 §0.9 锁住了 v2 *人侧* 的产品形态。
>
> §0.7 锁住"CodeFlow ≠ Cursor 外挂"——*技术身份*。
> §0.8 锁住"v2 第一阶段只做开发型"——*scope*。
> §0.9 锁住"Mobile = Governance Plane，不是 input proxy"——*人机分工*。
>
> 三个一起，v2 的产品轮廓基本闭合。

---

## 1. 定位与边界

### 1.1 CodeFlow v1 vs v2 重新定位

| 维度 | CodeFlow v1（现状） | CodeFlow v2（本设计） |
|---|---|---|
| **项目身份**（定位） | **Cursor 外挂** / IDE 增强 | **Agent Runtime** / AI Team OS |
| **Cursor 的角色** | 宿主、容器、必须依附 | **执行终端（之一）**，可被替换 |
| **主驱动机制** | OCR / CDP 观察 IDE 状态 | **SDK 直接驱动**（OCR/CDP 仅 fallback） |
| 项目对外定位 | Cursor IDE 的 ADMIN 桌面工具 | FCoP 协议的 SDK 运行时绑定 + AI OS 雏形 |
| 角色容器 | Cursor IDE chat tab | `@cursor/sdk` agent 进程 |
| 唤醒机制 | 巡检引擎 UI-click（pyautogui） | `Agent.resume(id).send(...)` |
| 桌面依赖 | 必须开 Cursor 桌面端、PC 解锁 | 不需要 |
| 角色数量 | 上限 = chat tab 数 | 无上限（取决于内存/quota） |
| 部署形态 | 仅本地 PC | **本地 / 云端 / 手机 三节点分布式** |
| 角色编制 | 硬编码 4 角色 | 用户 `roles.yaml` 配置 |
| 主要语言 | Python（codeflow-desktop） | TypeScript（@cursor/sdk 只有 TS 版） |
| **核心交付物** | 桌面应用 | **Runtime Protocol（5 类 schema）+ 参考实现**（详见 §3） |

**v2 的 README 第一句应该写：**

> CodeFlow v2 不是 IDE 工具，它是 [FCoP](https://joinwell52-ai.github.io/FCoP/) 协议在 [Cursor SDK](https://cursor.com/docs/api/sdk/typescript) 上的一个具体绑定。它跑你电脑、跑云端服务器、或两者混合，由你的 `roles.yaml` 决定。

### 1.2 三节点分布式 Agent Runtime（Mobile / Local / Cloud）

延续 FCoP 站点 hero quote「**The agents are your digital employees**」的隐喻，**v2 的"数字员工"分布在 3 个节点**：

| 维度 | 📱 Mobile（PWA） | 💻 Local PC | ☁️ Cloud Server |
|---|---|---|---|
| 角色定位 | **指挥端** | **现场员工** | **远程员工 + 总部** |
| 现实类比 | ADMIN 在沙发上 / 出差路上 | 现场办公 | 远程办公 / 24×7 总部 |
| 在线时间 | 你打开 PWA 时 | PC 开机时 | 永不下线 |
| 工作环境 | 不直接干活，只下指令 | 你的本地文件 / 凭证 / 内网 | 干净 Cursor cloud VM |
| 干的活 | 派任务、审批、看通知 | DEV 改代码 / OPS 调内网 | PM 派单 / QA cloud CI / 24×7 监控 / 长任务 |
| 启动成本 | 0（PWA 永远在线） | 0（本地进程） | 几秒（拉 VM） |
| 计费模型 | 不计 | 仅 token | token + VM 时间 |
| 数据不出域 | （不持有数据） | ✅ | ❌（信任 Cursor cloud） |
| 直接改本地代码 | ❌ | ✅ | ❌（只能 PR 回仓） |
| 不依赖 PC 开机 | ✅ | ❌ | ✅ |

**完整三节点拓扑（v2 终态）：**

```
                ┌─────────────────────────────┐
                │ 📱 Mobile (PWA)              │
                │   ADMIN 在哪它就在哪          │
                └────────────┬─────────────────┘
                             │ WebSocket relay
                             ▼
                ┌─────────────────────────────┐
                │ 🧠 CodeFlow Runtime           │
                │ (可部署在 PC 或独立云服务器)  │
                └─┬───────────────────────────┬─┘
                  ▼                           ▼
        ┌─────────────────┐         ┌──────────────────┐
        │ 💻 Local Node    │         │ ☁️  Cloud Node     │
        │  Cursor / IDE 端 │         │  Cursor cloud VM │
        │  Local agents    │         │  Cloud agents    │
        └─────────────────┘         └──────────────────┘
```

**自然的角色分配（三节点对仗）：**

```
📱 指挥端                    ☁️ 云端总部                      💻 PC 现场
─────────────              ─────────────────────             ─────────────────────
ADMIN（你）                  PM-01    拆单不看代码            DEV-01   改本地文件
派单 / 审批 / 通知          QA-01    cloud CI 干净环境       OPS-01   ssh 内网
                            监控/巡检 worker（24×7）          调试 / 临时操作
                            PWA 后端 / 长任务调度
```

这就是 **AI 团队的 hybrid work，再加上 mobile-first 指挥**——把现实中"指挥官 + 远程办公 + 现场办公"的三元结构直接搬到数字员工身上。

> 📌 §0.7.4 已经画过同款拓扑图，这里强调的是 *角色*视角，§0.7.4 强调的是 *节点能力*视角。
> 同一个三节点架构，从两个不同侧面理解。

### 1.3 与 FCoP 协议的边界（重要）

> **历史渊源**（详见 §8.0）：codeflow-pwa 是 FCoP 协议的 *母体仓*，FCoP（spec + `fcop` / `fcop-mcp` PyPI 双包）后期被抽离到独立仓 [`D:\FCoP` / `joinwell52-AI/FCoP`](https://github.com/joinwell52-AI/FCoP) 维护。
> 抽离边界由 [`docs/integrations/fcop-standalone-zh.md`](../integrations/fcop-standalone-zh.md) 写死：**协议 + MCP = FCoP（独立）；手机驭 AI 工具 = 本仓（独立）**。
> v2 在本仓内继续演化协议（TS 端 `packages/codeflow-protocol/`）是合法的——但 schema 必须与 `D:\FCoP` 的 Python 双包跨语言等价，详见 §3.3.1.b。

**CodeFlow v2 不替代 FCoP，也不绑定 FCoP**——它是 FCoP 的一个具体实现，遵守且仅遵守 FCoP 公开协议：

| 归 FCoP 管 | 归 CodeFlow v2 管 |
|---|---|
| 文件命名（`TASK-*.md` / `REPORT-*.md` / `ISSUE-*.md` / `role-switch-*.md`） | 谁去写 / 谁去读这些文件 |
| YAML 元数据头规范 | inbox watcher 实现细节 |
| 4 类协调 pattern（PLANNER/CODER、PM/DEV/QA/OPS、PM.TEMP、role-switch） | agent 生命周期 / 模型选择 / cloud-local 混合 |
| 协议演进 / Essay 的现场观察 | doorbell 触发逻辑 / 渲染层 |

**底线规则 #1（兼容性）：**
CodeFlow v2 写出来的任何文件，必须能被任何其他 FCoP 兼容工具（fcop-mcp / fcop CLI / 一个空 shell）识别和处理。
反之亦然——别人用 fcop-mcp 写的 TASK 文件，CodeFlow v2 必须能正常 dispatch。
这条规则保证了 FCoP 的 host-neutral 特性不会被 CodeFlow v2 偷偷锁死。

**底线规则 #2（kernel 强依赖）：**
任何角色的 `mcp` 列表里 **必须包含 `fcop`**（即 fcop-mcp）。
未挂 fcop-mcp 的角色 = 失去"纪律层"的裸 SDK agent ≈ AI OS 没装内核就启动用户态进程，结果是不可预测的。
CodeFlow v2 启动时会执行 schema 校验，缺 fcop 直接拒绝加载该角色并报错。

**底线规则 #3（kernel-first 的 MCP 编排）：**
其他所有 MCP（`git` / `playwright` / `sql` / 用户自定义）都是"设备驱动"，必须**在 fcop 协议框架之内**被调用。
具体含义：CodeFlow v2 不会去校验 agent 怎么用 git 这些 tool，但会要求 agent 在用之前/用之后通过 fcop 的 `create_task` / `report` 接口留下协议级痕迹（FCoP 文件）。
这是"kernel 管纪律，driver 提供能力"的工程兑现。

---

## 2. 核心架构

### 2.1 总览图：CodeFlow Runtime 的 6 大内核子系统

按 §0.5 OS 类比，CodeFlow Runtime 由 **6 个 kernel-grade 子系统**组成：

```
┌──────────────────────────────────────────────────────────────────────┐
│  CodeFlow Runtime (Node.js / TypeScript)                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. Session Manager        管理 Agent ↔ Task ↔ Run 的会话三元 │   │
│  │   - 谁正在跑哪个 task / 哪些 run 在 stream / 优雅关闭        │   │
│  │   - 对位 OS：进程/线程调度的会话层                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 2. Task Scheduler         事件驱动的 Task 派发器              │   │
│  │   - chokidar 监听 inbox/<role>/                               │   │
│  │   - Task 落地 → 选 agent → Agent.resume(...).send(...)       │   │
│  │   - 这就是"门铃"                                              │   │
│  │   - 对位 OS：scheduler                                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 3. Agent Registry         Agent 实例的中央目录                │   │
│  │   - .codeflow/state/agents.json：agentId / runtime / 模型     │   │
│  │   - 启动时：lazy create or resume                             │   │
│  │   - 对位 OS：进程控制块 (PCB) 表                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 4. Skill Runtime          Skill (MCP) 的注册 / 加载 / 权限   │   │
│  │   - 解析 roles.yaml.mcp_servers，按 role 注入对应 skill      │   │
│  │   - per-role 权限：DEV 能用 git，QA 不能（隔离）              │   │
│  │   - 对位 OS：动态库 / syscall 路由                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 5. Review Engine ⭐ 最关键子系统                              │   │
│  │   - 监听 review-required Task，路由到 Reviewer agent         │   │
│  │   - 落 Review Schema 文件（详见 §3.4）                       │   │
│  │   - 对位 OS：权限系统 (chmod / sudo / ACL)                   │   │
│  │   - § Why 最关键：见 §2.1.1                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 6. State Store            所有持久化状态的统一管理            │   │
│  │   - .codeflow/state/agents.json (PCB)                        │   │
│  │   - .codeflow/state/sessions/<id>.json (会话记录)            │   │
│  │   - .codeflow/state/transcripts/<run-id>.md (事件转录)       │   │
│  │   - docs/agents/tasks/ (Task Store, FCoP 协议目录)           │   │
│  │   - 对位 OS：文件系统 + journal log                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│      ↑↑↑ kernel 子系统全部在 fcop-mcp 的"内核纪律"约束下运行 ↑↑↑   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
              ▲                         ▲                       ▲
              │                         │                       │
   ┌──────────┴──────────┐  ┌───────────┴──────────┐  ┌─────────┴────────┐
   │ FCoP 文件系统       │  │ Agent 节点（任意）   │  │ ADMIN 入口       │
   │ docs/agents/tasks/  │  │  - Local SDK agents  │  │  - PWA 手机端    │
   │   ├─ inbox/<role>/  │  │  - Cloud SDK agents  │  │  - fcop CLI      │
   │   ├─ in_progress/   │  │  - (未来) Claude Code│  │  - 任意文本编辑  │
   │   ├─ review/        │  │  - (未来) Codex      │  │                  │
   │   └─ done/          │  │  - (未来) ollama     │  │                  │
   └─────────────────────┘  └──────────────────────┘  └──────────────────┘
```

**6 个子系统对应 §0.5 OS 类比的精确映射：**

| 子系统 | OS 对应物 | 主要职责 |
|---|---|---|
| Session Manager | 进程调度器（会话层） | 维护"哪个 agent 在跑哪个 task 的哪个 run" |
| Task Scheduler | scheduler | Task 落地驱动 Agent 上工（doorbell） |
| Agent Registry | 进程控制块表（PCB table） | agentId/runtime/模型/mcp 的权威存储 |
| Skill Runtime | 动态库 + syscall 路由 | per-role MCP 注入与权限隔离 |
| **Review Engine** ⭐ | **权限系统（chmod/sudo）** | **Review 决策与路由 — v2 的最关键子系统** |
| State Store | 文件系统 + journal log | 所有持久化状态的统一管理 |

> 📌 这 6 个子系统是 v2 的 **kernel 四件套（§0.6.4）+ kernel-grade OS 服务** 的工程对应物。
> 后面 §2.2-§2.7 会逐一展开每个子系统的接口设计。

### 2.1.1 为什么 Review Engine 是 6 大子系统中*最关键*的一个

按 §0.6.7 护城河（Agent Governability）的逻辑，6 大子系统并非等权重——
**Review Engine 是把"概率性 LLM"转化为"可治理 Agent"的关键转换器**，没有它，前面 5 个子系统加起来也不够撑起"AI Runtime"这个名号。

**为什么这么说？**

| 没有 Review Engine | 有 Review Engine |
|---|---|
| Agent 输出 = 黑盒，对错全看人肉 spot-check | Agent 输出 = 必经审核，每条决策都有 verdict |
| 多 agent 协作 = 一群概率机器 chain 起来，错误指数级放大 | 每个 chain 节点有 reviewer 角色，错误在节点处被截断 |
| 出事后无法追责（"是 LLM 干的"） | `review.md` 有明确 reviewer_role + verdict + 时间戳，**可问责** |
| 跑得越多越乱（state 漂移） | 跑得越多越稳（review 反馈循环修正 prompt / brief） |

**Review Engine 在工程上承担三个职责：**

1. **路由**：把 `review-required` Task 投递到正确 reviewer agent（按角色 / 主题 / SLA）
2. **裁决**：落 §3.4 Review Schema 文件（`verdict: approved | rejected | needs_changes`）
3. **回环**：rejected 时构造新 Task 回投发起者，rejected ≥ N 次升级到 ADMIN

**v0.1 必须做、v0.x 不能砍的子系统：**

- ✅ Task Scheduler（没有它没法触发）
- ✅ Agent Registry（没有它无法 resume）
- ✅ State Store（没有它无法持久化）
- ✅ **Review Engine（没有它就只是个 prompt chain，不是 Runtime）** ⭐
- ⚠️ Session Manager（v0.1 可以最简单实现）
- ⚠️ Skill Runtime（v0.1 可以只挂 fcop + filesystem 这两个 MCP）

> 📌 **如果让我们在 6 个子系统里只留 1 个，留 Review Engine。**
> 因为 Task/Agent/State 都是 "AI 工具" 时代就有的概念，
> 而 Review Engine 才是 "AI Runtime" 时代独有的治理设施——它是护城河。

### 2.2 角色注册表（`roles.yaml` + `briefs/`）

CodeFlow v2 启动唯一必需的配置 = **一份 yaml + 一组 brief 文件**：

```
.codeflow/
├── roles.yaml              # 团队编制（数量/名字/模型/runtime/mcp）
└── briefs/                 # 角色身份脚本，每个角色一份独立 .md
    ├── PM.md
    ├── DEV.md
    ├── QA.md
    └── OPS.md
```

**为什么把 brief 拆出去？** 三个理由：

1. **brief 通常很长**（FCoP 规则 + role-specific 约束 + 域知识），塞 yaml 多行字符串会让 yaml 不可读
2. **brief 经常需要 git diff / review**，独立 .md 文件比 yaml 多行字符串友好得多
3. **brief 本身就是 markdown**，可以放代码块 / 表格 / 链接，独立文件更自然

#### `roles.yaml` 完整示例

```yaml
# .codeflow/roles.yaml
version: 1

defaults:
  runtime: local
  cwd: "."
  inbox_root: "docs/agents/tasks/inbox"
  done_root: "docs/agents/tasks/done"
  brief_dir: ".codeflow/briefs"

roles:
  # ─── L1: AI Worker Layer（执行类，详见 §0.9.1）──────────────
  - id: PM
    layer: worker            # ⭐ worker | governance | admin
    brief_file: "PM.md"      # 解析为 ${defaults.brief_dir}/PM.md
    runtime: cloud           # ← PM 不需要本地文件，跑云端
    model:
      id: default            # Auto，最便宜
    mcp:
      - fcop                 # 强依赖；缺它会被启动校验拒绝

  - id: DEV
    layer: worker
    brief_file: "DEV.md"
    runtime: local           # ← 必须改本地文件
    model:
      id: claude-sonnet-4-6
      params:
        - { id: thinking, value: "true" }
        - { id: context,  value: "1m" }
        - { id: effort,   value: high }
    mcp:
      - fcop
      - git                  # 设备驱动，可选

  - id: OPS
    layer: worker
    brief_file: "OPS.md"
    runtime: local
    model:
      id: gpt-5.3-codex
      params:
        - { id: reasoning, value: high }
        - { id: fast,      value: "true" }
    mcp:
      - fcop

  # ─── L2: AI Governance Layer（治理类，详见 §0.9.1 & §2.1.1）──
  - id: QA                   # 也叫 REVIEW，按团队习惯命名
    layer: governance        # ⭐ 治理层；签发的 Review 才有合法性
    brief_file: "QA.md"
    runtime: cloud
    model:
      id: claude-haiku-4-5
    mcp:
      - fcop
      - playwright

  # 以下角色 v0.2+ 启用，v0.1 用 `enabled: false` 标注但保留 schema 占位
  - id: PATROL               # 巡检 Agent（详见 §0.9.5.A）
    layer: governance
    enabled: false           # v0.3+ 启用
    brief_file: "PATROL.md"
    runtime: cloud
    model: { id: claude-haiku-4-5 }
    mcp:
      - fcop

  - id: SECURITY             # 安全 Reviewer（详见 §0.9.5.B Review Board）
    layer: governance
    enabled: false           # v0.5+ 启用
    brief_file: "SECURITY.md"
    runtime: cloud
    model: { id: claude-sonnet-4-6 }
    mcp:
      - fcop

  - id: AUDIT                # 合规 Reviewer
    layer: governance
    enabled: false           # v0.5+ 启用
    brief_file: "AUDIT.md"
    runtime: cloud
    model: { id: claude-haiku-4-5 }
    mcp:
      - fcop

  # ─── L3: Human Admin（人，不是 agent）────────────────────────
  # ADMIN 不写在 roles 里——它是从 Mobile/CLI 进入 Runtime 的真人入口
  # 但 layer=admin 的合法性校验由 Agent Registry 做，详见 §3.2

review_board:                # ⭐ Review Board 配置（v0.5+，详见 §0.9.5.B）
  enabled: false
  policies:
    high_risk:
      members: [REVIEW, SECURITY, AUDIT]
      consensus_required: 2
      include_security: true
    normal:
      members: [REVIEW]
      consensus_required: 1

mcp_servers:                 # 引用上面 mcp 列表里的名字
  fcop:
    type: stdio              # local agent 用 stdio
    command: fcop-mcp
  git:
    type: stdio
    command: mcp-server-git
  playwright:
    type: http               # cloud agent 必须用 http
    url: https://your-relay.example.com/mcp/playwright
```

#### `.codeflow/briefs/PM.md` 示例

```markdown
# PM-01 brief

你是 FCoP 体系的 PM-01，负责拆任务、调度、回执 ADMIN。

## 你被允许做的事

- 接收 `TASK-*-ADMIN-to-PM.md`，立即写 `TASK-*-PM-to-ADMIN.md` 回执
- 拆解任务，派发给 DEV / OPS / QA（各自独立 TASK 文件）
- 汇总团队结果给 ADMIN

## 你被禁止做的事

- 不允许只在内部流转，有阶段结果必须写 PM-to-ADMIN
- 不允许直接给 DEV/OPS/QA 跨级派单（必须经文件）
- 不允许写代码或部署（那是 DEV/OPS 的活）

## 任务文件命名规范

`TASK-YYYYMMDD-序号-发送方-to-接收方.md`，优先级 `P0`/`P1`/`P2`/`P3`。

## 完整规则

详见 `.cursor/rules/pm-bridge.mdc`。
```

> 💡 brief 文件本身可以挂任意 markdown 内容，包括嵌入 [.cursor/rules/](../../.cursor/rules/) 已有的 rule 文件作为引用，避免规则两处定义。

#### Schema 校验规则（启动时强制）

| 规则 | 失败行为 |
|---|---|
| `roles[].id` 必须唯一，仅允许 `[A-Za-z][A-Za-z0-9_-]*` | 拒绝加载整个团队 |
| `runtime` ∈ `{ local, cloud }` | 拒绝加载该角色 |
| `model.id` 必须在 `Cursor.models.list()` 返回结果里 | 拒绝加载该角色 |
| `brief_file` 文件必须存在且非空 | 拒绝加载该角色 |
| `mcp[]` 引用必须在顶层 `mcp_servers` 里能找到 | 拒绝加载该角色 |
| **`mcp[]` 必须包含 `fcop`（kernel 强依赖，见 §0.5）** | **拒绝加载该角色，日志写明"缺 fcop = 裸 SDK = 违反 AI OS 内核强依赖"** |
| `runtime: cloud` 的角色所引用的所有 `mcp_servers` 必须 `type: http` | 拒绝加载该角色（cloud VM 跑不了 stdio） |

### 2.3 Agent 生命周期

```typescript
// 伪代码 - 实际实现见 packages/codeflow-core/src/lifecycle.ts
class AgentLifecycleManager {
  private agents = new Map<string, SDKAgent>();   // role.id → agent
  private registry: AgentRegistryFile;             // .codeflow/state/agents.json

  async start() {
    for (const role of this.config.roles) {
      const existing = this.registry.lookup(role.id);
      const agent = existing
        ? await Agent.resume(existing.agentId, this.toAgentOptions(role))   // 已有则恢复
        : await this.createFresh(role);                                     // 否则新建
      this.agents.set(role.id, agent);
    }
  }

  private async createFresh(role: RoleConfig): Promise<SDKAgent> {
    const agent = await Agent.create({
      apiKey: process.env.CURSOR_API_KEY,
      name: `FCoP ${role.id}`,
      model: role.model,
      ...(role.runtime === "cloud"
        ? { cloud: { repos: [{ url: this.config.repoUrl }] } }
        : { local: { cwd: role.cwd ?? process.cwd() } }),
      mcpServers: this.resolveMcpServers(role),
    });
    // 给 agent 灌 brief（"你是 PM-01..."），落 agentId 到 registry
    await (await agent.send(role.brief)).wait();
    this.registry.save(role.id, { agentId: agent.agentId, runtime: role.runtime });
    return agent;
  }

  async dispatch(roleId: string, message: string): Promise<RunResult> {
    const agent = this.agents.get(roleId);
    if (!agent) throw new Error(`Unknown role: ${roleId}`);
    const run = await agent.send(message);
    this.renderer.attach(run);                     // 把 stream 接到渲染层
    return await run.wait();
  }

  async stop() {
    for (const [, agent] of this.agents) {
      await agent[Symbol.asyncDispose]();
    }
  }
}
```

**关键设计点：**

1. **agent registry 持久化**：`agentId` 落盘到 `.codeflow/state/agents.json`，重启 CodeFlow 进程时自动 resume，不重新创建（不浪费 token、不丢角色记忆）
2. **lazy creation**：注册表里没有的 role 才 create；已有的 resume
3. **优雅退出**：捕获 SIGTERM/SIGINT，依次 dispose 全部 agent，避免泄漏 local executor 子进程
4. **重新创建逃生口**：用户手动删 `.codeflow/state/agents.json` → 下次启动等于 fresh 团队（用于角色记忆"中毒"时复位）

### 2.4 Inbox watcher（doorbell 触发器）

```typescript
// packages/codeflow-core/src/watcher.ts
import chokidar from "chokidar";

class InboxWatcher {
  constructor(private lifecycle: AgentLifecycleManager, private config: Config) {}

  start() {
    for (const role of this.config.roles) {
      const inboxPath = path.join(this.config.inbox_root, role.id);
      chokidar.watch(inboxPath, { ignoreInitial: true })
        .on("add", (filePath) => this.onFileAdded(role.id, filePath));
    }
  }

  private async onFileAdded(roleId: string, filePath: string) {
    if (!this.isFcopTaskFile(filePath)) return;       // 不符合 FCoP 命名的忽略
    const relPath = path.relative(process.cwd(), filePath);

    // ↓↓↓ 这就是"门铃" ↓↓↓
    await this.lifecycle.dispatch(
      roleId,
      `inbox 收到新任务，请处理：${relPath}\n\n（请按 FCoP 协议读文件、做事、写回执）`,
    );
  }

  private isFcopTaskFile(p: string): boolean {
    return /TASK-\d{8}-\d{3}-[A-Za-z]+-to-[A-Za-z]+\.md$/.test(path.basename(p));
  }
}
```

**为什么 watcher 不直接读文件内容塞进 send？**

让 agent 自己通过 **fcop-mcp 的 `read_task` 工具**去读，原因有 4 条（最后一条最关键）：

1. 文件可能很大（含附件链接、长 body），SDK send 一上来就塞会浪费 context
2. 让 agent 走 tool 调用，事件流里能看到完整"读文件 → 思考 → 行动"，可观察性更好
3. 文件落地时可能还在写（半成品），fcop-mcp 可以做完整性校验，watcher 只负责"通知"
4. **kernel 强制原则**：根据 §0.5 + §1.3 底线规则 #2，所有 agent 必须挂 fcop-mcp，watcher 这边不需要兜底"如果 agent 没挂 fcop 怎么办"——schema 校验阶段就把这种角色拒掉了，根本启动不起来

> ⚠️ **不留降级路径**：早期设计稿曾考虑"如果没挂 fcop-mcp，watcher 就把文件全文塞进 send"。
> 这个设计被否决了。理由：留降级路径等于鼓励用户跳过 kernel，违反 §0.5 的内核强依赖立场。
> v2 的态度是**硬规则**：不挂 fcop = 启动失败 = 修配置 = 重启。这是 AI OS 应该有的纪律。

### 2.5 事件渲染层

继承 spike 验证过的设计（见 `_ignore/spike_sdk_doorbell/ringer.ts`），扩展为多 sink 架构：

```typescript
interface EventSink {
  attach(run: Run, meta: RunMeta): void;
}

// 内置 3 个 sink：
class TerminalSink implements EventSink { /* 流式打印 */ }
class MarkdownSink implements EventSink { /* 落 state/transcripts/<run_id>.md */ }
class PwaPushSink  implements EventSink { /* 经中继推手机端 */ }

// CodeFlow 启动时按配置组装：
const sinks = config.event_sinks.map(spec => createSink(spec));
const renderer = new MultiSink(sinks);
```

**8 类 SDKMessage 的渲染映射**（已在 spike 里验证过格式）：

| SDKMessage type | terminal 渲染 | markdown 渲染 | PWA 渲染 |
|---|---|---|---|
| `system` (init) | `⚙️  system/init  model=...` | `### system/init` | start 通知 |
| `thinking` | `💭 thinking (2.3s): ...` | `> 引用块` | 折叠的"思考中" |
| `assistant` | 流式 token | 累积成段落 | 流式推送 |
| `tool_call` | `→/✓/✗ tool_call(name) [status]` | code block | 工具卡片 |
| `status` | `─ status: FINISHED` | `### status: ...` | 状态条 |
| `task` | `📌 task [...]` | `### 📌 task` | 进度条 |
| `request` | `❓ request id=...` | metadata | 等待用户 |
| `user` (echo) | 跳过（已知） | metadata only | 跳过 |

**性能优化**：spike 里 30 秒一个 run 流出 209 个事件。Markdown sink 必须按 200ms 时间窗 + 同类型聚合，
否则转录文件会胀到几十 KB。聚合策略放在 `MarkdownSink` 内部，对 `TerminalSink` 不生效（终端要实时性）。

---

## 3. Runtime Protocol & Schemas（v2 的核心交付物）

> **ADMIN-01 在 §0.6 / §0.7 review 后下达的"最重要一件事"：**
>
> > "定义 Runtime Protocol —— 一旦协议稳定，生态会自己长出来。
> > 这其实就是 Linux 的 POSIX、Docker 的 OCI、Kubernetes 的 CRD。"

CodeFlow v2 不是"先做应用、协议慢慢演进"，而是 **"协议先冻结、应用按协议长出来"**。
本章定义 5 类 schema，构成 **CodeFlow Runtime Protocol v0.1**。

> 📌 §3 是这份设计文档的**真正交付物**。
> 后面 §4-§11 都是这套 schema 的部署细节、迁移细节、风险细节，本质是"按协议实现"。
> 如果时间不够、其他章节都来不及做，**也必须先把 §3 完成并冻结**。

### 3.0 设计哲学：协议是协作宇宙的"物理定律"，不是脚本

> **ADMIN 5/9 13:51 锁定**（见 §0.0 项目宪法第 3 句）：
>
> > 「5 类 Schema 真正应该变成：
> > Task = 定义目标与约束 / Agent = 定义能力边界 /
> > Session = 定义运行上下文 / Review = 定义治理规则 / Skill = 定义可调用能力。
> > ❌ 不要：定义固定动作。
> > ✅ 而要：定义『约束 + 能力 + 状态 + 权限』，让 Agent 自己规划 / 协作 / 拆解 / 实现。
> > 现在真正做的，不是『控制 Agent』，而是『**为 Agent 提供一个不会崩溃的协作宇宙**』。」

这一节把这条哲学锁进设计文档，作为 §3.1-§3.8 所有 schema 字段评审的"判定准则"。

#### 5 类 Schema 的"维度"对照

| Schema | 维度 | 不应该有的字段类型 |
|---|---|---|
| Task | 目标 + 约束 | ❌ `next_action` / `must_run_step` |
| Agent | 能力边界 | ❌ `should_execute` / `forced_role` |
| Session | 运行上下文 | ❌ `next_send_payload` / `mandatory_step` |
| Review | 治理规则 | ❌ `auto_approve_after_n_minutes`（这是策略，不是规则） |
| Skill | 可调用能力 | ❌ `must_call_first` / `default_invocation_args` |

**判定准则**：每加一个 schema 字段时问自己——

- 这个字段是**让 agent 自己决策依据**（保留），还是
- 这个字段是**替 agent 决策**（删掉）？

#### 物理学的隐喻

5 类 schema = **哈密顿量 + 边界条件**；
agent 的具体执行 = **轨迹**；
协议层不规定轨迹，只规定**轨迹必须满足的边界条件**。

- 轨迹崩了 → agent 自身能力问题（不是协议背锅）。
- agent 想出新轨迹 → 协议不阻拦（协议从来没规定过轨迹长什么样）。

这跟 §0.7 的"身份反转"在协议层是一回事：v1 cursor 外挂时代，CodeFlow 写脚本指挥 cursor 做 X；v2 Agent Runtime 时代，CodeFlow 只规定"什么样的 X 是合法的"，agent 自己决定做不做、怎么做、用什么顺序做。

#### 这条哲学是 §0.6.7 / §0.7 在协议层的精确表达

- §0.6.7「Agent Governability 护城河」= 让概率性 LLM 可治理 = 给 agent **边界**让它自治
- §0.7「身份反转」= Cursor 不再是依附宿主，而是被驱动的执行终端 = agent 不再被 *脚本控制*，而是被 *协议约束*
- §3.0（本节）= 在协议层把这条思想锁死，作为 §3.1-§3.8 的字段评审准则

#### 落地到 v0.1 的 4 条工程后果

1. **schema 不长动作字段**——5 类 schema 的字段全部是约束 / 能力 / 状态 / 权限维度（详见 §3.1-§3.8 的 schema 定义，没有任何 `mandatory_*` / `forced_*` / `next_*` 字段）。
2. **runtime 层的"事件"也不规定动作**——`RuntimeEvent` 只暴露"发生了什么"（sdk.* + runtime.session_*），从不暴露"必须做什么"。
3. **Review Engine（S4）== 协议执法者**，不是流程控制器——审核失败时 Review 只能 reject + 退回 agent 重做，不能"替 agent 改答案"。
4. **§3.0 是 §8.0 硬规则 #4 的灵魂**——任何 schema 升级提案，PM/DEV 必须先在本节判定准则下自证"这是约束/能力/状态/权限维度，不是动作维度"。

### 3.1 协议设计原则（4 条）

1. **JSON Schema 作为机器可读规范**
   放在 `packages/codeflow-protocol/schemas/`，发布独立 `@codeflow/protocol` npm 包。
   任何语言、任何工具都能消费此规范，不仅限于 v2 自己用。

2. **Markdown front-matter (YAML) 作为人/AI 可读形式**
   任何 schema 实例都必须能在 .md 文件的 YAML front-matter 里完整表达。
   理由：FCoP 的 host-neutral 立场要求"任何文本编辑器都能直接看",JSON-only 不满足。

3. **向后兼容硬规则**
   - minor 版本升级（1.0 → 1.1）：**只允许加字段**，新字段对旧消费者不可见
   - major 版本升级（1.x → 2.0）：必须提供官方迁移脚本，且至少与上一个 major 共存 6 个月
   - 任何字段重命名 / 删字段 / 改语义 = major bump

4. **遵守 FCoP 命名约定**
   Runtime Protocol **不替代** FCoP，是 FCoP 协议的 schema 化扩展。
   所有 schema 定义的文件必须遵守 FCoP 的命名规则（`TASK-*`, `REPORT-*`, `ISSUE-*`, `REVIEW-*`）。

### 3.2 Agent Schema

定义"一个数字员工"的完整状态。对应 §0.5 OS 类比里的"线程"。

```jsonc
// .codeflow/state/agents/<agent_id>.json  或  Markdown front-matter
{
  "$schema": "https://codeflow.dev/schemas/agent/v1.0.json",
  "agent_id": "DEV-01",                      // 全局唯一，与 SDK agentId 不同（这是 role-level 标识）
  "sdk_agent_id": "agent-c2b242c3-...",      // SDK 返回的 agentId，用于 Agent.resume()
  "role": "developer",                       // 与 roles.yaml 里 roles[].id 对应
  "layer": "worker",                         // ⭐ worker | governance | admin（详见 §0.9.1 三层组织结构）
  "node": "local",                           // local | cloud | mobile
  "runtime": "local",                        // local | cloud（local agent 必须 local 节点；cloud agent 可在 local 或 cloud 节点）
  "workspace": "/abs/path/to/project",       // local agent 的 cwd；cloud agent 是 repo URL
  "model": {
    "id": "claude-sonnet-4-6",
    "params": [
      { "id": "thinking", "value": "true" },
      { "id": "context",  "value": "1m" }
    ]
  },
  "skills": ["fcop", "git"],                 // 当前激活的 MCP skill 列表（必含 "fcop"）
  "status": "idle",                          // idle | running | blocked | review | error | stopped
  "current_task": "TASK-20260509-001-PM-to-DEV",  // 当前持有的 Task ID，idle 时为 null
  "current_session": "session-...",          // 当前 Session ID
  "memory_usage": {                          // 可观察性
    "tokens_in_context": 12345,
    "max_context": 1000000
  },
  "started_at": "2026-05-09T15:00:00Z",
  "last_active_at": "2026-05-09T15:30:00Z",
  "labels": {                                // 用户自定义标签，用于路由 / 计费 / 审计
    "team": "platform",
    "cost_center": "r-and-d"
  }
}
```

**`layer` 字段的运行时约束（兑现 §0.9.1 的两条铁律）：**

| layer | 典型 role | 运行时强制约束 |
|---|---|---|
| `worker` | DEV / TEST / DOC / OPS / PM | 不允许签发 Review；不允许调用 Human Admin；不允许撤销其他 agent |
| `governance` | REVIEW / AUDIT / SECURITY / PATROL | 不允许直接修改业务代码；签发的 Review 才有合法性；可以路由到 Human Admin |
| `admin` | ADMIN（人，不是 agent） | 唯一可以打断/覆盖/回滚任何决策的层；只通过 Mobile 或 CLI 进入 Runtime |

**默认值**：缺省 `layer` 字段时按 `worker` 处理（向后兼容旧 fcop-mcp 写的 agent 文件）。
**校验时机**：Agent Registry（§2.1 第 3 子系统）在 `Agent.create()` / `Agent.resume()` 时校验。

### 3.3 Task Schema（FCoP `TASK-*.md` 的 YAML front-matter）

定义"一份工作"的完整生命周期。对应 §0.5 OS 类比里的"进程"。
**这是 FCoP 协议的 schema 化锚点——v2 的 Task 100% 兼容现有 FCoP `TASK-*.md` 文件**。

```yaml
---
$schema: https://codeflow.dev/schemas/task/v1.0.yaml
protocol: fcop
fcop_version: "1.0"
runtime_protocol_version: "1.0"

task_id: TASK-20260509-001-PM-to-DEV         # 全局唯一，与文件名一致
sender: PM                                   # FCoP role
recipient: DEV                               # FCoP role
priority: P2                                 # P0 / P1 / P2 / P3

thread_key: refactor-utils                   # 同一会话线程的多个 Task 共享
parent_task: null                            # 拆出来的子任务指向父任务

status: pending                              # pending | dispatched | in_progress | review | done | blocked | cancelled
state_history:                               # 状态流转审计（追加，不删）
  - { state: pending,    at: "2026-05-09T15:00Z", by: PM }
  - { state: dispatched, at: "2026-05-09T15:01Z", by: codeflow-runtime }

review_required: true                        # 是否需要 Review Engine 介入
review_assignee: QA                          # null = Runtime 自动选 reviewer
risk_level: medium                           # ⭐ low | medium | high | irreversible（详见 §0.9.4 高风险红线）
                                             # high/irreversible 自动触发 Human-in-the-loop（needs_human）

created_at: "2026-05-09T15:00Z"
updated_at: "2026-05-09T15:30Z"
deadline: null                               # 可选

labels:
  area: refactor
---

# 任务正文（Markdown body）

请把 src/utils.ts 里的字符串拼接重构成模板字符串...
```

**与 FCoP 现有 `TASK-*.md` 的兼容性：**
- FCoP 协议要求的字段（`protocol`, `task_id` from filename, `sender`, `recipient`, `priority`）**完全保留**
- v2 新增字段（`status`, `state_history`, `review_*`, `runtime_protocol_version` 等）放在 front-matter
- **旧 fcop-mcp 写的 TASK 文件，v2 必须能读**；缺失新字段时按 default 处理（`status: pending`）

#### 3.3.1 未来扩展：Task-as-folder（v0.x+ 演进路径）

> **v0.1 范围**：单文件 Task（本节上方的 schema），与 FCoP 1.0-pre 完全兼容。
> **v0.x+ 演进路径**：当一个 Task 演化出多份产出物（plan / execution / result / review）时，可升级为目录化结构。

**目标形态：**

```text
docs/agents/tasks/
└── TASK-20260601-001-PM-to-DEV/        ← 目录，沿用 FCoP 命名
     ├── task.md                         ← Goal + Constraints（取代单文件 body）
     ├── plan.md                         ← PM 拆解结果
     ├── execution.md                    ← DEV 实施记录
     ├── result.md                       ← 最终产物索引
     └── review.md                       ← Review 决议（取代独立 REVIEW-*.md）
```

**为什么先不在 v0.1 做？**

1. **FCoP 兼容性**：FCoP 现有实现 + 第三方 fcop-mcp 集成都假设 `TASK-*.md` 是文件，目录化是 breaking change
2. **小任务不需要**：90% 的开发 Task 一个文件足够，目录化反而增加心智负担
3. **协议升级路径未定**：见下面 3.3.1.b

##### 3.3.1.a 双形态共存的判定规则（如果 v0.x 启用）

| 文件系统状态 | 判定 | 处理 |
|---|---|---|
| `TASK-*.md` 是文件 | 单文件 Task（v0.1 默认） | 直接读 front-matter |
| `TASK-*/` 是目录，且含 `task.md` | 目录化 Task（v0.x+） | 读 `TASK-*/task.md` 的 front-matter，其他文件按 schema 字段索引 |
| 同名文件 + 目录冲突 | 配置错误 | 启动时校验失败，拒绝加载 |

##### 3.3.1.b 与 FCoP 主协议的关系（重要 — 唯一合法路径）

> **协议演进唯一合法仓库 = `D:\FCoP` / [`joinwell52-AI/FCoP`](https://github.com/joinwell52-AI/FCoP)**（见 §8.0 硬规则 #4）。
>
> codeflow-pwa 早期是 FCoP 的母体——但 FCoP 抽离独立维护之后，**协议层的所有改动必须在 `D:\FCoP` 仓里发生**。本仓 `packages/codeflow-protocol/` 是 FCoP spec 的 TS 镜像实现，**只能镜像，不能创造**。

#### 唯一合法的协议升级路径

```text
1. v2 在工程实践中发现 FCoP 当前 spec 不够用
   （例：Task-as-folder / risk_level / layer 等字段需求）
        ↓
2. 在 D:\FCoP 仓提 Issue / Discussion，描述需求 + v2 上的实测证据
   （把 packages/codeflow-protocol/ 里的 schema 草案作为参考材料附上）
        ↓
3. 在 D:\FCoP 仓内：spec 文档 + Python 双包同步演进
   （按 D:\FCoP 自己的 release process 走 → 发新版本到 PyPI）
        ↓
4. 等 D:\FCoP 发版后，本仓 packages/codeflow-protocol/ 同步 TS schema
   ── 必须以 D:\FCoP 的 spec 为准，不允许偏离
        ↓
5. 在本仓 packages/ 写 schema fuzz 测试，证明跨语言等价
```

#### 砍掉的反面路径（绝不允许）

| 反面路径 | 为什么不允许 |
|---|---|
| ❌ 在 `packages/codeflow-protocol/` 加 `task_format: file \| folder` 字段，先用着 | 这就是 schema 单边 fork，会让 v2 与 D:\FCoP Python 双包跨语言不等价 |
| ❌ 给 v2 加一个 "实验性 schema" 命名空间，绕过 D:\FCoP | 同上，只是换了 fig leaf；并且让 D:\FCoP 失去权威性 |
| ❌ 在本仓写 Task-as-folder reference impl 然后等 FCoP "采纳" | 顺序错了——必须 *先* 在 D:\FCoP 仓里 review 通过，本仓 *后* 实现 |

#### 两个例子（对比）

**正例 — Task-as-folder 应该怎么走：**
1. 在 `D:\FCoP` 提 Issue：「FCoP 1.1 是否考虑 Task-as-folder？」附 v2 上发现的多产出物 use case
2. FCoP 维护者评审 → 同意写进 1.1 spec → 发 `fcop@1.1.0` / `fcop-mcp@1.1.0` 到 PyPI
3. 本仓 `packages/codeflow-protocol/` 同步加 schema 字段（与 PyPI 1.1 等价）
4. 本仓 v2 Runtime 升级到 fcop@>=1.1，启用 folder 模式

**反例 — 现在 §3.2/§3.3 已加的 `layer` / `risk_level` 字段怎么办？**
这些字段是 v2 设计文档先写出来的，*已经超前了 D:\FCoP 当前 spec*。这属于 **"v2 草案 → 待提案到 D:\FCoP" 的待办状态**，不是合法状态。处理路径：
- v0.1 实施前：在 `D:\FCoP` 提对应 Issue（`layer` / `risk_level` / `needs_human` 等）
- 等 D:\FCoP 反馈：接受 = 进 fcop spec；拒绝 = v2 必须移除这些字段
- 在反馈出来之前：本仓 schema 文件标记为 `v0.1-alpha-pending-fcop-review`

**与 overview 的对账**：[`docs/codeflow-overview.md` §四.2](../codeflow-overview.md) 已经按"v0.1 单文件 + v0.x+ Task-as-folder"两段叙事对外讲；本节是它的工程兑现 + 协议升级路径锁死。

### 3.4 Review Schema（`REVIEW-*.md` 的 YAML front-matter）

定义"一次审批"的完整记录。对应 §0.5 OS 类比里的 chmod/sudo 决策。

```yaml
---
$schema: https://codeflow.dev/schemas/review/v1.0.yaml
protocol: fcop
runtime_protocol_version: "1.0"

review_id: REVIEW-20260509-001-QA-on-TASK-20260509-001
subject_type: task                          # task | code_change | report | role_switch
subject_ref: TASK-20260509-001-PM-to-DEV    # 被 review 的对象 ID

# 单 reviewer 模式（v0.1 默认）
reviewer_role: QA
reviewer_agent: QA-01

# 多 reviewer 模式（Review Board，v0.5+，详见 §0.9.5.B）
# review_board:
#   policy: high_risk
#   members:
#     - { role: REVIEW,   agent: REVIEW-01,   decision: approved, decided_at: "..." }
#     - { role: SECURITY, agent: SECURITY-01, decision: approved, decided_at: "..." }
#     - { role: AUDIT,    agent: AUDIT-01,    decision: needs_changes, decided_at: "..." }
#   consensus_required: 2
#   consensus_reached: true

decision: approved                          # approved | rejected | needs_changes | abstained | needs_human
                                            # ⭐ needs_human：governance 层判定需 Human Admin 拍板
                                            #    会自动 push 到 Mobile（详见 §0.9.3 第 4 屏 + §0.9.4）
rationale: |
  代码改动符合 FCoP 协议，无副作用，已自测通过。
required_changes: null                      # decision=needs_changes 时必填，列具体待改项

# decision=needs_human 时必填
human_approval:
  pushed_to: mobile                         # mobile | cli
  pushed_at: "2026-05-09T16:01Z"
  approved_by: null                         # 待人确认时为 null；approved 后填 ADMIN handle
  approved_at: null
  trigger_reason: "task.risk_level=high"    # 触发原因（task 风险 / skill 风险 / board 共识失败）

decided_at: "2026-05-09T16:00Z"
decision_duration_ms: 4523                  # review 耗时（用于 SLO 监控）
---

# Review 详情（Markdown body）

## 检查清单

- [x] 代码改动是否完成 FCoP 协议要求...
- [x] 是否有 unit test 覆盖...
```

**Review 决策的 OS 类比**：
- `approved` ≈ chmod +x（授权执行）
- `rejected` ≈ chmod -x（撤销授权）
- `needs_changes` ≈ ENOENT（要先补齐前置）
- `abstained` ≈ EPERM（reviewer 表示自己无权决定）
- `needs_human` ≈ syscall 走到 ring 0（必须切换到内核态——Human Admin 拍板）

### 3.5 Session Schema（`.codeflow/state/sessions/<id>.json`）

定义"一段 agent ↔ task 的会话"。对应 §0.5 OS 类比里的"进程上下文"。

```jsonc
{
  "$schema": "https://codeflow.dev/schemas/session/v1.0.json",
  "session_id": "session-7f82fb65-...",
  "agent_id": "DEV-01",
  "task_id": "TASK-20260509-001-PM-to-DEV",
  "started_at": "2026-05-09T15:01:00Z",
  "ended_at": "2026-05-09T15:30:00Z",
  "status": "completed",                     // running | completed | failed | cancelled
  "runs": [                                  // 每次 agent.send() 是一个 run
    {
      "run_id": "run-7f82fb65-...",
      "started_at": "...",
      "ended_at": "...",
      "status": "finished",
      "tokens_used": { "input": 1234, "output": 567, "thinking": 89 },
      "tool_calls_count": 6,
      "transcript_path": ".codeflow/state/transcripts/run-7f82fb65-....md"
    }
  ],
  "total_cost_usd": 0.12,                    // 跨 run 累计计费
  "outcome": {
    "files_changed": ["src/utils.ts"],
    "report_ref": "REPORT-20260509-001-DEV-to-PM"
  }
}
```

### 3.6 Skill Schema（`packages/codeflow-protocol/skills/<id>.json`）

定义"一个能力（MCP server）"的注册元数据。对应 §0.5 OS 类比里的"动态库 / driver 注册"。

```jsonc
{
  "$schema": "https://codeflow.dev/schemas/skill/v1.0.json",
  "skill_id": "git",
  "version": "1.2.0",
  "displayName": "Git 操作",
  "provided_by": {
    "type": "mcp_server",
    "transport": "stdio",                    // stdio | http | sse
    "command": "mcp-server-git"              // stdio 必填
    // 或 url: "https://..."                  // http/sse 必填
  },
  "tools": [                                 // 这个 skill 提供的具体 tool
    {
      "name": "git_commit",
      "required_perms": ["repo:write"],
      "risk_level": "low",                   // ⭐ low | medium | high | irreversible
      "irreversible": false,                 // 是否不可回滚
      "cost_sensitive": false                // 是否触发付费操作
    },
    {
      "name": "git_status",
      "required_perms": ["repo:read"],
      "risk_level": "low"
    },
    {
      "name": "git_push_force",
      "required_perms": ["repo:write"],
      "risk_level": "high",                  // ⭐ 触发 §0.9.4 高风险红线
      "irreversible": true                   // 强制推送可能擦除别人提交
    }
  ],
  "available_to_roles": ["DEV", "OPS"],      // 哪些 role 可以挂这个 skill
  "required_kernel": ["fcop@>=1.0"],         // 强依赖（这个 skill 的某些 tool 必须在 fcop 协议下使用）
  "compatible_runtimes": ["local"],          // local | cloud | both
  "homepage": "https://github.com/.../mcp-server-git",
  "license": "MIT"
}
```

**`risk_level` × `irreversible` × `cost_sensitive` 的运行时行为**（由 Skill Runtime / §2.1 第 4 子系统执行）：

| 标记组合 | 运行时行为 | 触发的 Review 路径 |
|---|---|---|
| `risk_level: low` | 直接调用 | 无（事后 audit log） |
| `risk_level: medium` | 调用前记录 intent | 走单 reviewer Review |
| `risk_level: high` 或 `irreversible: true` | **拦截调用** → 构造 `decision: needs_human` | Push 到 Mobile，等 Human approval（§0.9.4） |
| `cost_sensitive: true` | 调用前先估算 cost | 单笔超阈值 → 同 high；累计超日预算 → 同 high |

**实现要点**：所有 MCP tool 的调用都被 Skill Runtime 包了一层 wrapper，校验 `risk_level` 后才决定是放行还是转 Review。
**v0.1 起**所有 v2 自带 skill 都必须声明 `risk_level`，第三方 skill 缺省按 `medium` 处理。

### 3.7 Schema 演进：POSIX / OCI / CRD 类比

| 系统 | 内核 | 标准接口 | 生态形态 |
|---|---|---|---|
| Linux | kernel | **POSIX** | glibc / musl / 各发行版 |
| Docker | dockerd | **OCI Image / Runtime spec** | containerd / podman / cri-o / Kubernetes |
| Kubernetes | kube-apiserver | **CRD + API conventions** | 数千个 operator / controller |
| **CodeFlow v2** | **fcop-mcp + Runtime** | **CodeFlow Runtime Protocol（§3.2-§3.6）** | 待生长 |

**冻结这套 schema 之后，外界开发者就可以做：**

| 第三方做的事 | 基于哪条 schema |
|---|---|
| 写新的 Skill（提供新 MCP server） | §3.6 Skill Schema |
| 写新的 Reviewer 实现（不一定是 LLM） | §3.4 Review Schema |
| 接入新的 Agent 实现（Claude Code / Codex / 自建 LLM 包装） | §3.2 Agent Schema |
| 写第三方 Task 来源（Jira/GitHub Issue → Task） | §3.3 Task Schema |
| 做 Session 分析 / 计费 / 审计工具 | §3.5 Session Schema |

**这就是"内核成立后生态自动长出来"的工程兑现。**

> ⚠️ **重要 — schema 演进发生在哪里？**
>
> 以上 5 个 schema 的任何 *演进动作*（加字段、改语义、bump 版本）都**必须发生在 `D:\FCoP` 仓**，不是这里。
> 本仓 `packages/codeflow-protocol/` 是 FCoP spec 的 TS 镜像，跟 `D:\FCoP` 的 Python 双包是 *同一协议的两个语言绑定*。
> 详见 §8.0 硬规则 #4 + §3.3.1.b "唯一合法的协议升级路径" 5 步流程图。

### 3.8 v0.1 schema 冻结策略

| 字段范围 | v0.1 → v1.0 升级路径 |
|---|---|
| **必填字段** | v0.1 起冻结，不允许重命名/删除/改语义；v1.0 时确认 |
| **可选字段** | v0.1 试用期，v1.0 前可调整；v1.0 后冻结 |
| **labels 字段** | 永远开放，作为用户/团队自定义扩展位 |
| **新增字段** | 任何 minor bump 都允许加，要求"对旧消费者透明" |

**v0.1 → v1.0 的判定标准（4 选 3）：**
- 至少有 3 个第三方实现接入（含至少 1 个非作者实现）
- 跑过 90 天无 breaking change
- 至少 1 篇 Essay 级文档（如 FCoP Essay 07）总结协议演化经验
- 通过 schema fuzz 测试（边界值 / 缺失 / 多余字段全覆盖）

> ⚠️ **冻结 / 升级动作发生在哪里？**
>
> - 冻结决定 → 在 `D:\FCoP` 仓里发布 `fcop@1.0.0` + `fcop-mcp@1.0.0`
> - 本仓 `packages/codeflow-protocol/` *跟随* 这次冻结，发布 TS 镜像同版本号
> - "v0.1 → v1.0 判定标准 4 选 3" 这套规则也是 *FCoP 协议层的标准*，不是本仓单方面定的——它属于 §8.0 硬规则 #4 范围内，需要在 `D:\FCoP` 仓评审通过

---

## 4-7, 9. 中段章节占位（待后续刀次展开）

| § | 标题 | 主要内容 |
|---|---|---|
| §4 | 部署形态 | local-only / cloud-only / hybrid 详解 + 三节点中继协议 |
| §5 | FCoP 协议接入策略 | 接入方式 A: fs 直接写 / 接入方式 B: fcop-mcp 强依赖（推荐） / 接入方式 C: @fcop/core npm 包（注意：这是 *消费协议* 的 3 种方式，不是 *演进协议* 的路径——后者唯一合法 = §8.0 硬规则 #4） |
| §6 | MCP 注入策略 | per-role MCP / resume 重注入 / cloud HTTP 改造 |
| §7 | 关键技术决策 | 语言/包管理/错误码/计费/可观察性 |
| §9 | 已知坑 & 风险 | Windows 中文乱码 / cloud stdio 限制 / token 计费突发 / 角色记忆中毒 |

> 这 5 章是工程细节，必须建立在 §0-§3 + §8 + §10 已经稳定的前提下。
> 任何具体技术选型如果跟 §0.6.7（治理化护城河）/ §0.8（开发型 scope）/ §0.9（Mobile-first）冲突，
> **必须先解决前置冲突再回来填这 5 章**。

---

## 8. codeflow-pwa 仓库：v1 freeze + v2 新身份共生

> **核心事实（务必先读）：**
>
> v2 不是 v1 的"下一个版本"——v2 是 *彻底换了身份的产品形态*。
> v1 = "Cursor 外挂"（Desktop EXE + UI 自动化）；v2 = "AI Runtime"（FCoP 协议 + SDK + 治理）。
> 两者**共享同一个 git 仓库 `codeflow-pwa`**，但作为 *不同身份的产品* 共生：
> - **v1 进入 freeze + 维护期**（`codeflow-desktop/` 不再加新功能，仅安全 fix）
> - **v2 在同一个仓库内重新定义产品**（`packages/codeflow-protocol/` + Runtime + Mobile Console）
>
> **两个独立 git clone**：
>
> 1. `D:\Bridgeflow` → [`joinwell52-AI/codeflow-pwa`](https://github.com/joinwell52-AI/codeflow-pwa) —— v1 维护 + v2 主战场
> 2. `D:\FCoP` → [`joinwell52-AI/FCoP`](https://github.com/joinwell52-AI/FCoP) —— FCoP 协议 + `fcop` / `fcop-mcp` PyPI 双包，**协议演进的唯一合法仓库**（详见 §8.0 硬规则 #4）
>
> 这一节把仓库内的"v1 freeze + v2 新身份"边界、子项目角色、与 `D:\FCoP` 的协作关系一次性说清楚，避免后续 contributor 把 v1 维护和 v2 开发混在一起做。

### 8.0 历史溯源（先有 codeflow-pwa，后有 FCoP）

```text
2025         2026-Q1                     2026-Q2 (现在)              2026-Q3+
  │            │                            │                          │
  │ codeflow-pwa  ────►  从 codeflow-pwa   ────► v2 设计文档落定         │
  │ (Cursor 外挂) │       中沉淀出 FCoP                                 │
  │              │       协议规范                                       │
  │              │       │                                              │
  │              │       └─► FCoP 抽离到独立仓                          │
  │              │           joinwell52-AI/FCoP                         │
  │              │           本机：D:\FCoP                              │
  │              │           (协议 + spec + Python 双包是权威)          │
  │              │                                                      │
  │              │       ┌─► 本仓的 fcop-mcp/ 进入 legacy ⚠️             │
  │              │       │   按 docs/integrations/fcop-standalone-zh.md │
  │              │       │   迁移期引用，新规范一律以 FCoP 仓为准         │
  │              │       │                                              │
  │              │       └─► v2 在母体仓内继续演化协议（TS 端）           │
  │              │           packages/codeflow-protocol/                │
  │              │           （5 类 schema 的 reference implementation） │
  │              │           ↕ 跨语言姊妹关系 ↕                          │
  │              │           D:\FCoP 里的 Python 双包                    │
  │              │                                                      │
  │              │       任何 schema 演进 → 在母体仓试 → 逆向贡献到      │
  │              │       FCoP 仓 → 协议层达成跨语言一致                  │
```

**5 条由这段历史推出的硬规则：**

1. **母体只是 *诞生地*，不是 *继续演化* 的地方**：codeflow-pwa 早期孵化了 FCoP——但 FCoP 抽离独立维护之后，"母体"身份就转交给了 `D:\FCoP`。本仓 *再也不是* 协议主线。类比：Linux 早期长在 Linus 个人电脑里，后期必须在 `kernel.org` 做。

2. **`D:\FCoP` 是规范权威**：本仓 `fcop-mcp/` 子目录曾是抽离前的 *历史副本*，按 [`docs/integrations/fcop-standalone-zh.md`](../integrations/fcop-standalone-zh.md) 写死的边界，**新规范、新包版本、MCP 行为一律以 `D:\FCoP` 为准**。**该副本已于 2026-05-09 按硬规则 #5 物理删除**（详见 §8.6 退役记录）；本仓后续一律 `pip install fcop-mcp` 走 PyPI 版本。

3. **v2 的 TS 实现 = 协议镜像，不是协议主线**：`packages/codeflow-protocol/` 是 FCoP 协议的 TS reference implementation，跟 `D:\FCoP` 的 Python 双包是 *同一协议的两个语言绑定*——schema 必须保持等价。任何 schema 改动必须 *先* 在 `D:\FCoP` 仓里发生，本仓 *后* 镜像。**绝对不允许本仓单边创造 schema 字段**。

4. **协议演进的唯一合法仓库 = `D:\FCoP`** ⭐：
   - 任何"v2 想要但 FCoP 没有"的字段需求 → 必须先去 `D:\FCoP` 提 Issue / PR
   - 任何"v2 想试用某个 schema 演进"的实验 → 必须先在 `D:\FCoP` 评审通过，本仓再镜像
   - 任何"暂时在 v2 这边加个字段先用着"的捷径 → **不允许**（即使 ADMIN 默许也不允许；ADMIN 同意 = 应该去 D:\FCoP 仓走流程）
   - 任何 §3 / §3.3.1.b 之外的"实验性 schema 命名空间"提案 → **不允许**（这是绕过 D:\FCoP 权威的 fig leaf）

   具体执行路径：详见 §3.3.1.b "唯一合法的协议升级路径" 5 步流程图。

5. **本仓 = 应用方（消费方/下游），不是定义方（spec author/上游）** ⭐⭐：

   ADMIN 5/9 10:25 原话：
   > 「我们现在这个码流项目，就是应用 fcop-mcp；不是定义 fcop！」
   > 「作为整个码流项目文件夹，由于 fcop 已经独立，涉及到 fcop 的升级内容，是另一个项目文件了。」

   这条规则是 #4 的对偶面：
   - **#4 防外**：防别人在本仓改 schema（"你们别在我家改我的协议"）
   - **#5 防内**：防本仓自己 ship "定义/分发 fcop" 的任何东西（"我家也别留下定义协议的东西"）

   两条加起来，**本仓与 fcop spec/包的关系彻底单向化**——只消费、不生产。

   #### 5.a 项目文件夹的物理边界

   - **本仓 / 码流（CodeFlow）项目** = `D:\Bridgeflow` = `joinwell52-AI/codeflow-pwa`
     - 职责：应用 fcop-mcp + 多 agent runtime + Mobile Console + role briefs + 文档
   - **D:\FCoP 项目** = 完全独立的项目文件夹 = `joinwell52-AI/FCoP`
     - 职责：fcop spec + `fcop` / `fcop-mcp` PyPI 双包 + 协议升级 + 安装/集成指引

   两个项目文件夹是 *姊妹关系*，不是 *父子关系*——本仓不是 D:\FCoP 的下级，也不是 D:\FCoP 的上级。

   #### 5.b 本仓"不该 ship"的东西清单（按 #5 的 *防内* 精神）

   状态列：⛔ = 历史上违规存在（已于 2026-05-09 物理删除，详见 §8.6）；🚫 = 永久禁止再出现。

   | 类目 | 本仓不该 ship | 应当归属 | 状态 |
   |---|---|---|---|
   | fcop / fcop-mcp 包源码 | 本仓 `fcop-mcp/` 子目录 + `codeflow-plugin/src/fcop/` 副本 | D:\FCoP（已有） | ⛔ → 已删 |
   | fcop-mcp 安装脚本 | 本仓 `codeflow-plugin/scripts/install-fcop.{ps1,sh}` | D:\FCoP README（应有） | ⛔ → 已删 |
   | fcop-mcp 在 Cursor 的 mcp.json 模板 | 本仓 `codeflow-plugin/mcp.json` | D:\FCoP README（应有） | ⛔ → 已删 |
   | PyPI 包名 `fcop` | 本仓 `codeflow-plugin/pyproject.toml` `name = "fcop"` 占着 | D:\FCoP 拥有 | ⛔ → 已删 |
   | Cursor plugin 名 `fcop` | 本仓 `codeflow-plugin/.cursor-plugin/plugin.json` `name: fcop` 占着 | D:\FCoP 或 codeflow-plugin 重命名 | ⛔ → 已删 |
   | fcop 升级指引 / 迁移文档 | 本仓不该有"如何升级 fcop"类型文档（仅可有"本仓如何对齐到新版 fcop-mcp"的内部记录） | D:\FCoP `docs/MIGRATION-*.md` | 🚫 |
   | fcop pip 依赖声明 | 本仓 `codeflow-plugin/requirements.txt` 拉 fcop 包 | D:\FCoP 自管依赖 | ⛔ → 已删 |
   | "如何安装 fcop MCP" 教程 | 本仓 `codeflow-plugin/README.md`（v1 内容） | D:\FCoP README | ⛔ → 已删 |

   #### 5.c 本仓"可以 / 应当 ship"的东西

   - **应用层**：consumer-side 代码（`packages/codeflow-runtime/` / `packages/codeflow-protocol/` 镜像 / role briefs）
   - **集成层**：本仓自己的 mcp.json *用于本仓开发* 的样例（不是给最终用户用的）；如果保留，**必须明确标注 "this is codeflow-pwa internal dev config"**
   - **接入指引**：「如何在码流里 *使用* fcop-mcp」类型文档；不允许「如何 *安装* fcop-mcp」（那是 D:\FCoP 的事）

   #### 5.d 本规则的违反检测

   未来 contributor 在本仓加任何文件，触发以下检查：
   - 文件路径 / 内容包含 `install-fcop` / `setup-fcop` / `bundle-fcop` → 大概率违反 #5
   - PyPI 包名占用 `fcop` 或 `fcop-*`（除 `fcop-pwa-companion` 等明确无歧义的） → 违反 #5
   - 任何 `MIGRATION-fcop-*.md` / `RELEASE-fcop-*.md` 类文档 → 违反 #5

   #### 5.e LEGACY 退役与本规则的关系

   §8.6 列出的 LEGACY 副本是 #5 *被发现之前* 留下的违规残留，不是 #5 *允许* 的存在。退役节奏由 §8.6 的 backlog 管理。

   ---

   **§8.0 5 条硬规则的 *配对结构*：**

   | 配对 | 防什么 |
   |---|---|
   | #1 + #2 | 防"母体仓 == 协议权威"的认知错位 |
   | #3 + #4 | 防外（schema fork） |
   | **#5** | **防内（本仓自己 ship 定义类内容）** |

### 8.1 仓库现状（v1 时代结构）

`codeflow-pwa` 是一个 **多子项目共仓** 的产品仓，原本承载 v1 = "Cursor 外挂"形态的全部代码：

```text
codeflow-pwa/  (origin: github.com/joinwell52-AI/codeflow-pwa)
├── codeflow-desktop/      ← Python 桌面 EXE（v1 patrol 引擎所在 ⚠️）
├── codeflow-plugin/       ← Cursor MCP 插件 + role brief templates  ⚠️ 已瘦身（5/9 删除 plugin 部分，保留 role briefs / templates / hooks）
├── fcop-mcp/              ← ⛔ 已删除（5/9，硬规则 #5；本仓 pip install fcop-mcp）
├── web/pwa/               ← PWA 源码（HTML/JS, 无构建步骤）
├── server/relay/          ← WebSocket 中继（开发联调用）
├── scripts/               ← 部署脚本
├── docs/                  ← 双语文档
├── promotion/             ← 推广素材
├── index.html / sw.js / config.js / manifest.json   ← PWA 部署根
└── README.md / README.en.md / README.zh.md

# 独立姊妹仓（不在本工作树内）：
D:\FCoP/  (origin: github.com/joinwell52-AI/FCoP)
├── fcop / fcop-mcp（PyPI 双包）  ← 协议规范权威 + Python 实现
└── 协议 spec + Essays
```

**v1 仓库特点：**
- Python 占 56%（desktop + fcop-mcp）+ HTML 占 41%（PWA）+ 其他 2%
- 主入口是 *Desktop EXE*——围绕"PC 端外挂 Cursor"展开
- 270 commits / 19 releases / Latest = `CodeFlow Desktop v2.12.17` (2026-04-19)
- 开放 8 个 PR，2 个 stars

### 8.2 子项目在 v1 freeze + v2 新身份共生中的归属

按 §0.7（身份反转）+ §0.9（Mobile-first Governance）+ §8.0（5 条硬规则），每个子项目要么属于 v1 freeze 维护、要么属于 v2 新身份开发，**不允许同一个子项目同时承担两边新功能**——这条规则是为了避免身份混淆。

> 项目身份再确认（ADMIN 5/9 10:48 原话，作为本节"宪法级引用句"）：
>
> 「**这个项目文件就是码流的，目前项目是用 cursor 的 sdk，应用 fcop-mcp。**」
>
> 解读：
> - 「**码流的**」 = 本仓 = CodeFlow 项目（不是 fcop 项目）
> - 「**用 cursor 的 sdk**」 = v2 主线技术栈 = `@cursor/sdk`（不是 Cursor IDE 外挂、不是 OCR、不是 CDP）
> - 「**应用 fcop-mcp**」 = 角色 = *consumer/downstream*，对应 §8.0 硬规则 #5
>
> 这一句把本节所有子项目归属判断收敛到一个判据：**任何子项目，如果它做的不是上述 3 件事，就要回 §8.0 五条硬规则查它的合法性**。

| 子项目 | v1 角色（freeze） | v2 新身份下的角色 | 共生策略 |
|---|---|---|---|
| `codeflow-desktop/` | **v1 主入口**（Python EXE + patrol 引擎） | ❌ **不在 v2 主线** —— v2 完全不依赖它 | v1 freeze：仅安全 fix；不再加 UI 自动化新功能；v0.3 后评估归档到 `legacy/` |
| `codeflow-plugin/` | Cursor 插件 + role briefs | **已瘦身（5/9）** —— Cursor plugin 子部分（`src/`、`mcp.json`、`scripts/install-fcop.*`、`pyproject.toml`、`.cursor-plugin/plugin.json`、`requirements.txt`、`README.md`）按硬规则 #5 全部删除；保留资产 = `agents/` + `templates/` + `skills/` + `commands/` + `hooks/` | 把保留的 `agents/` brief 抽成 `.codeflow/briefs/` 标准格式（与 §3.2 layer 字段对齐）；剩余 `templates/`/`hooks/` 归属由 §8.6 backlog #4 处理 |
| `fcop-mcp/` | FCoP MCP server (Python) | ⛔ **已删除（5/9）** —— 按硬规则 #5 物理移除整个目录；本仓后续 `pip install fcop-mcp` 走 PyPI 版本 | 已完成 ✅，详见 §8.6 退役记录 |
| `(extern) D:\FCoP/` | （v1 期间不存在） | **协议规范权威 + 协议演进唯一合法仓库** + Python 双包源 —— v2 agent 用的 `fcop-mcp` 应来自 `pip install`（即 D:\FCoP 发布的版本），不是本仓副本 | 跨仓同步：本仓 `packages/codeflow-protocol/` 任何 schema 改动必须 *先* 在 `D:\FCoP` 仓评审通过（详见 §8.0 硬规则 #4 + §3.3.1.b 唯一合法升级路径） |
| `web/pwa/` | v1 PWA（任务发送器） | **v0.2 Mobile Governance MVP** 的承载主体（§0.9.3 4 屏） | 现有页面保留 + 增量加 4 屏 + Approval + 🛑（不重写） |
| `server/relay/` | 联调中继 | **v0.2 起 Mobile↔Runtime 通信通道**（§0.9.6 v0.2 sprint S7） | 协议升级到 v2 事件 schema，但保留 v1 兼容层 |
| `scripts/` | 部署脚本 | 保留 + 加 v2 sprint 自动化脚本 | 增量 |
| `docs/` | 双语文档 | **v2 文档主目录**（已含 `codeflow-overview.md` + `design/`） | 已迁移完成 ✅ |
| `packages/codeflow-protocol/` | （v2 新增） | **§3 Runtime Protocol 的 reference implementation** —— Sprint S1 已完成 | 新增 ✅ |
| `_ignore/spike_sdk_doorbell/` | （v2 新增） | SDK 验证 spike，证明 `Agent.create/resume` 可用 | 已完成 ✅，作为参考实现保留 |

### 8.3 是否分仓的决策

> **TL;DR：v0.x 阶段不分仓，v1.0 协议冻结后再考虑。**

#### 候选方案

| 方案 | 含义 | 优势 | 劣势 |
|---|---|---|---|
| **A. monorepo（不分）** | 全部子项目继续放在 codeflow-pwa | 演进同步、改动原子提交、不破坏 271+ commit history | 仓内 4 种语言（Python/JS/TS/HTML）混杂；release 节奏难以独立 |
| **B. 双仓（packages 抽出）** | 把 `packages/codeflow-protocol/` 抽到 `codeflow-protocol` 独立仓 | TS 包独立 release / npm 发布更干净 | 与 codeflow-pwa 的 git history 断开；contributor 需要克隆两个仓 |
| **C. 三仓（v1 与 v2 彻底分家）** | `codeflow-pwa` 保留 v1 维护，新建 `codeflow-runtime` 装 v2 全部代码 | v2 干净起步，无 v1 包袱 | v1 用户切换路径不明，可能丢失存量；fcop-mcp / web/pwa 归属混乱 |

#### v0.x 阶段的决策：**走方案 A（monorepo）**

理由：

1. **v1 user base 已经在 codeflow-pwa**：分仓会让现有 user 困惑去哪里看 release notes
2. **v2 还在 alpha**（v0.1-alpha.1）：抽包过早会增加迁移成本
3. **dogfood 协议演进**：`packages/codeflow-protocol/` 跟设计文档同步演进时，monorepo 改动原子化更安全
4. **仓内已有先例**：`fcop-mcp/` 也是另一个仓的开发副本（与 FCoP 公仓同步），说明 monorepo + 副本同步模式在本仓已经能工作

#### v1.0 之后的决策点（待 §10.6 触发）

到 §10.6 v1.0 schema freeze 时，重新评估：

| 触发条件 | 推荐分仓动作 |
|---|---|
| `packages/codeflow-protocol/` 有 ≥3 个第三方实现 | 抽到 `codeflow-protocol` 独立仓（方案 B），发 npm 公开包 |
| v2 Mobile Governance 用户 > v1 desktop EXE 用户 | 把 `codeflow-desktop/` 转 `legacy/` 子目录 |
| `D:\FCoP` 仓接收 Task-as-folder 升级（按 §3.3.1.b 唯一合法路径） | 把本仓 `fcop-mcp/` 副本下线，改为外部 `pip install` |

### 8.4 README / 仓库元数据更新清单

`codeflow-pwa` 仓的 GitHub-level 元数据（README + topics + about）目前还停留在 v1 叙事。v2 必须做的更新：

| 位置 | v1 现状 | v2 目标 | 状态 |
|---|---|---|---|
| `README.md` 顶部 | "Desktop EXE + Mobile PWA + MCP Plugin" | 加 v2 入口指引 + 保留 v1 现状 | ✅ 已加（本轮第六刀完成） |
| `README.en.md / .zh.md` | 同上 | 同上 | ✅ 已加 |
| GitHub repo "About" 描述 | "AI-powered human-AI collaboration hub" | 追加 ", Powered by CodeFlow AI Runtime (v2)" | ⏳ 待 ADMIN 在 GitHub UI 改 |
| GitHub Topics | `desktop-app, pwa, mcp, multi-agent, ...` | 加 `ai-runtime, ai-os, agent-runtime, agent-governance` | ⏳ 待 ADMIN 改 |
| Releases 命名 | `CodeFlow Desktop v2.12.17` | v0.1 起改 `@codeflow/protocol@0.1.0-alpha.1`、`CodeFlow Runtime v0.1.0` 等独立 tag | ⏳ Sprint S6 触发 |

### 8.5 完整时间表（含历史前传 + v2 演进）

```text
[ 历史前传 — 见 §8.0 ]
─────────────────────────────────────────────────────────────────────
2025      ─→ codeflow-pwa 诞生（Cursor 外挂 + Desktop EXE）
              │
              └─→ 内部沉淀出"文件名即协议"的实践

2026-Q1   ─→ 实践沉淀为 FCoP 协议规范
              │
              ├─→ FCoP + fcop / fcop-mcp 抽离到独立仓 D:\FCoP
              │   ↳ docs/integrations/fcop-standalone-zh.md 写死边界
              │
              └─→ 本仓 fcop-mcp/ 进入 LEGACY ⚠️（仅迁移期引用）

[ v2 演进 — 我们现在在这里 ]
─────────────────────────────────────────────────────────────────────
2026-Q2   ─→ ★ 第 3-6 刀写入 v2 设计文档（§0-§3 + §8 + §10）  ← 现在
              │
              ├─→ Sprint S1 完成 packages/codeflow-protocol/   ← 已完成 ✅
              │   （5 类 schema 的 TS reference implementation）
              │
              ├─→ Sprint S2 完成 packages/codeflow-runtime/ design skeleton ✅
              │
              └─→ ★ 5/9 硬规则 #5 物理落地 ✅
                  （删 fcop-mcp/ + codeflow-plugin/ 中所有 fcop 定义/分发副本——
                   原计划 v0.4 才做，实际提前 ~3 个月完成；详见 §8.6）

2026-Q3   ─→ Sprint S3-S6 完成 v0.1 Backend Kernel
              │
              ├─→ codeflow-desktop/ 进入 freeze
              └─→ packages/codeflow-protocol/ schema 演进逆向贡献到 D:\FCoP

2026-Q4   ─→ Sprint S7-S10 完成 v0.2 Mobile Governance
              │
              ├─→ web/pwa/ 增量改造为 4 屏 AI Team Console
              ├─→ server/relay/ 升级到 v2 事件 schema
              └─→ docs/integrations/fcop-standalone-zh.md 按 v2 身份重写

2027-Q1   ─→ v0.3 AI Patrol + v0.5 Review Board
              │
              ├─→ roles.yaml 启用 PATROL / SECURITY / AUDIT
              └─→ codeflow-plugin/ 剩余资产（agents/templates/hooks）
                  搬到 .codeflow/ 标准目录（§8.6 backlog #4）

2027-Q2   ─→ v1.0 Schema Freeze + 第一批外部用户
              │
              ├─→ 此时考虑分仓（§8.3 方案 B/C）
              └─→ Schema v1.0 与 D:\FCoP 双向冻结对齐

2027-Q3+  → AI OS 雏形 ↗ AI Team Operating System
```

> 📌 §8 锁住了 *仓库这一物理实体* 在 v2 演进中的角色。
>
> 任何"这段代码该写在哪个仓 / 哪个目录"的争论，都先回 §8.2 的角色分配表查。
> §8 改动 = 仓库结构改动 = 影响所有 contributor，需要 ADMIN 显式签字。

### 8.6 LEGACY 退役记录与 backlog（2026-05-09 起）

> 本节是 §8.0 硬规则 #5 的 *物理执行账本*。任何 LEGACY 副本进出本仓，必须在这里登账。
>
> 设计原则：**§8.0 5.b 表 = 规则**（什么不该 ship），**§8.6 表 = 账本**（事实上发生了什么）。
> 两表必须保持一致——账本里出现的"已删除"必须在规则表里有对应"⛔ → 已删"标记。

#### 8.6.1 触发事件

ADMIN 5/9 10:38 + 10:42 两次确认（原话见 §8.0 硬规则 #5）：

> 「我们现在这个码流项目，就是应用 fcop-mcp；不是定义 fcop！」
> 「就是删除现在项目中有关 fcop 定义的内容？」

PM-01 派 `TASK-20260509-006-PM-to-DEV.md`，DEV-01 在 ~3 分钟内完成，回执 `REPORT-20260509-006-DEV-to-PM.md`，PM 总结 `REPORT-20260509-007-PM-to-ADMIN.md`。

#### 8.6.2 已退役清单（5/9 物理删除，9 项）

| # | 路径 | 类型 | 删除理由（对位 §8.0 5.b） |
|---|---|---|---|
| 1 | `fcop-mcp/` 整个目录 | LEGACY 子项目 | fcop 包源码副本 |
| 2 | `codeflow-plugin/src/` 整个目录 | LEGACY 子项目 | fcop Python 包源码副本 + `_data/` + `server.py` + `__main__.py` |
| 3 | `codeflow-plugin/mcp.json` | 单文件 | fcop-mcp 在 Cursor 的 mcp.json 模板 |
| 4 | `codeflow-plugin/scripts/install-fcop.ps1` | 单文件 | fcop-mcp 安装脚本（Windows） |
| 5 | `codeflow-plugin/scripts/install-fcop.sh` | 单文件 | fcop-mcp 安装脚本（Unix） |
| 6 | `codeflow-plugin/pyproject.toml` | 单文件 | 占着 PyPI 包名 `fcop` |
| 7 | `codeflow-plugin/.cursor-plugin/plugin.json` | 单文件 | Cursor plugin 占着名字 `fcop` |
| 8 | `codeflow-plugin/requirements.txt` | 单文件 | fcop pip 依赖声明 |
| 9 | `codeflow-plugin/README.md` | 单文件 | "如何安装 fcop MCP" 教程（v1 内容） |

**验收**：
- `Test-Path` 9 × False ✅（5/9 10:46 验证）
- 保留资产 6 × True ✅（`agents/` / `templates/` / `skills/` / `commands/` / `hooks/` / `docs/integrations/fcop-standalone-zh.md`）
- `npm test --silent` (in `packages/codeflow-protocol`) 8/8 PASS ✅（5 valid + 3 expected-invalid）
- 全程未触碰 `D:\FCoP` 上游仓 ✅

#### 8.6.3 剩余 backlog（按优先级，PM-01 自行排）

| # | 项 | 优先级 | 责任方 | 触发节点 |
|---|---|---|---|---|
| 1 | `docs/design/codeflow-v2-on-fcop-sdk.md` §8.0 加硬规则 #5 + §0.0 嵌入宪法块 | P0 | PM | ✅ 已完成（5/9 本轮） |
| 2 | 同文档 §8.2 表 + §8.5 时间表更新事实 | P0 | PM | ✅ 已完成（5/9 本轮） |
| 3 | 新增 §8.6 LEGACY 退役账本 | P0 | PM | ✅ 已完成（5/9 本轮） |
| 4 | `docs/integrations/fcop-standalone-zh.md` 措辞按 v2 身份重写 | P1 | PM 派 DEV | v0.2 sprint 期间 |
| 5 | `codeflow-plugin/` 剩余资产（`agents/`/`templates/`/`hooks/`/`commands/`/`skills/`）搬到 `.codeflow/` 标准目录 | P2 | PM 派 DEV | 与 §3.2 `brief_dir` 标准化同步 |
| 6 | `_ignore/audit_fcop_project.{json,py}` / `audit_legacy_fcop.{json,py}` 是否清理 | P2 | DEV | 下次 housekeeping |
| 7 | `CHANGELOG.md` 添加 5/9 退役条目 | P2 | PM | 下次发版前 |
| 8 | `docs/release-process.md` 是否提及 fcop 子目录退役（更新跨仓发版流程） | P3 | PM | v0.2 mobile sprint 前 |
| 9 | README.md / .en.md / .zh.md 顶部嵌入 §0.0 宪法块的精简版 | P1 | PM | 与 §0.0 同步生效 |
| 10 | `codeflow-overview.md` / `.en.md` 顶部嵌入精简版宪法块 | P1 | PM | 同上 |

#### 8.6.4 未来 LEGACY 退役应走的流程

任何后续要从本仓删除/迁移的 LEGACY 副本，必须按以下 4 步：

1. **派单**：PM-01 写 `TASK-*-PM-to-DEV.md`，列删除清单 + 保留清单 + 验收标准
2. **执行**：DEV-01 物理操作 + 回归测试（至少 `@codeflow/protocol` test 必过）
3. **回执**：DEV-01 写 `REPORT-*-DEV-to-PM.md`，含 `Test-Path` 验证 + 影响评估
4. **登账**：PM-01 在 §8.6.2 表追加新行，并在 §8.0 5.b 表对应类目把 `⛔` 状态升为 `⛔ → 已删`

> 📌 §8.6 是 §8 的 *动态末梢*：所有未来变化都在这里登账。其他章节（§8.0–§8.5）保持稳定。

---

## 10. 实施路线图（Roadmap & Sprint Plan）

> §10 把前面所有"愿景 / scope / 协议"翻译成"下一周 / 下一个月做什么"。
> 任何"v0.x 是否完成"的争论，在这一节找答案。

### 10.1 总览：v0.1 → v1.0 五个里程碑

| 里程碑 | 时间窗（estimate） | 核心目标 | 验收门槛 |
|---|---|---|---|
| **v0.1 Backend Kernel** | 第 1-6 周（6 sprint） | PM→DEV→REVIEW→DONE 文件化闭环跑通 | §10.2 Demo 脚本通过 |
| **v0.2 Mobile Governance MVP** | 第 7-10 周（4 sprint） | 4 屏只读 + Approval + 🛑 Emergency Stop | §10.3 Mobile demo 通过 |
| **v0.3 AI Patrol** | 第 11-13 周（3 sprint） | PATROL-01 巡检 5 类异常 | §10.4 注入故障能被 Patrol 抓到 |
| **v0.5 Review Board** | 第 14-17 周（4 sprint） | REVIEW + SECURITY + AUDIT 三角共识 | §10.5 高风险 Task 走 board，单点 reviewer 卡不住 |
| **v1.0 Schema Freeze** | 第 18-26 周（9 周窗口） | §3 协议 90 天无 breaking change + 1 个外部实现 | §10.6 §3.8 v1.0 判定标准 4 选 3 通过 |

**总周期**：约 6 个月（26 周）。每个里程碑都有 *显式不做* 列表，防止 scope creep。

### 10.2 v0.1 Backend Kernel（6 sprint，每 sprint 1 周）

**v0.1 唯一目标（再次重申 §0.8.2）**：
> 一个 Runtime 能稳定驱动 4 状态 Agent 流水线（PM→DEV→REVIEW→DONE），
> 全程文件化、可追溯、可恢复、可审计，**不依赖任何 UI**。

| Sprint | 主题 | 关键交付 | 兑现 §0.8.2 哪条硬约束 |
|---|---|---|---|
| **S1** | Skeleton + 协议 freeze | TS 包结构 + §3 五类 schema 的 JSON Schema 文件 + 校验工具 | （所有约束的前置） |
| **S2** | Agent Registry + Session Manager | `Agent.create/resume` 包装 + `agents.json` 持久化 + 进程崩溃后能 resume | #3 进程能恢复 |
| **S3** | Task Scheduler (doorbell) | chokidar 监听 inbox + Task → agent.send + state_history 自动追加 | #1 零 UI / #2 状态全文件化 |
| **S4** | Review Engine（最关键⭐） | REVIEW agent 路由 + Review Schema 落地 + needs_human 转 Mobile（v0.1 转 stdout） | #4 每步有 reviewer |
| **S5** | Skill Runtime + fcop 强依赖校验 | 启动时 roles.yaml 校验缺 fcop 拒绝加载 + per-role MCP 注入 | #6 fcop-mcp 强依赖 |
| **S6** | E2E 验收 + 文档 | 跑通 §0.8.3 的 Hello World demo + 写 README + 写 v0.1 release notes | 全部 6 条 + #5 全本地 |

**v0.1 显式不做**（违反则砍掉，往 v0.2+ 移）：
- ❌ 任何 GUI / Mobile / Web Dashboard
- ❌ 云端 cloud agent（only local SDK runtime）
- ❌ Skill marketplace / 第三方 Skill 注册
- ❌ AI Patrol / Review Board / 多角色共识
- ❌ 计费 / SLA / 多租户 / 权限矩阵
- ❌ 任何 review-required Task 之外的"自动决策"逻辑

**v0.1 验收脚本**：复用 §0.8.3。跑通 = 完成。跑不通 = 不完成，**绝对不动 v0.2**。

### 10.3 v0.2 Mobile Governance MVP（4 sprint）

**v0.2 唯一目标**：让 ADMIN 在沙发上能完成 *看 + 审 + 急停* 三件事。

| Sprint | 主题 | 关键交付 |
|---|---|---|
| **S7** | PWA 骨架 + WebSocket 中继 | 复用现有 `web/pwa` + 中继协议升级到 v2 事件 schema |
| **S8** | 4 屏只读视图 | §0.9.3 的 Task Flow / Agent 状态 / Audit / Approval 4 个 tab，**只读** |
| **S9** | Approval 双向通道 | needs_human Review → push to mobile → tap approve/reject → write review.md |
| **S10** | 🛑 Emergency Stop + E2E | Mobile 红按钮 → Runtime cancel all runs → EMERGENCY-*.md 落盘 |

**v0.2 验收脚本**：

```text
1. v0.1 跑起来后，往 inbox 投一个高风险 Task
   （e.g. brief 包含 "git push --force"）
2. 手机端应在 5 秒内收到 Approval 推送
3. 手机端 reject → 该 Task 应进入 cancelled 状态
4. 手机端按 🛑 → 当前所有 in_progress Task 应在 10 秒内 paused
5. 全程不开 PC 上的任何 UI（仅 runtime daemon + 手机）
```

**v0.2 显式不做**：
- ❌ Mobile 上写 Task（依然走 ADMIN 的 CLI 或文本编辑器）
- ❌ 完整的 PATROL（v0.3）
- ❌ Review Board（v0.5）
- ❌ Mobile 美化 / 主题 / 图表 dashboard

### 10.4 v0.3 AI Patrol（3 sprint）

**v0.3 唯一目标**：PATROL-01 能自动捕捉 §0.9.5.A 的 5 类异常。

| Sprint | 主题 | 关键交付 |
|---|---|---|
| **S11** | PATROL-01 角色 + Patrol Schema | 在 roles.yaml 启用 PATROL；新增 Patrol Finding Schema |
| **S12** | 5 类异常检测 | 漂移 / 卡死 / 越权 / 长期无响应 / 协议违规 |
| **S13** | Patrol → Mobile 推送 | Patrol Finding 进 §0.9.3 第 3 屏 Audit + 注入故障 E2E 测试 |

**v0.3 验收**：人为构造 5 类异常各一例，PATROL 必须 100% 抓到，且 5 分钟内推到 Mobile。

### 10.5 v0.5 Review Board（4 sprint）

**v0.5 唯一目标**：高风险 Task 走 REVIEW + SECURITY + AUDIT 三角共识，单点 reviewer 不能放行。

| Sprint | 主题 | 关键交付 |
|---|---|---|
| **S14** | SECURITY-01 + AUDIT-01 启用 | 在 roles.yaml 启用，Brief 写专业领域脚本 |
| **S15** | review_board policy 引擎 | 按 task.risk_level 选 policy + consensus 计票 |
| **S16** | 共识失败兜底 | 长期无共识自动转 needs_human + Mobile push |
| **S17** | E2E + Audit log | 高风险 Task 全链路审计可视化（Mobile 第 3 屏增强） |

**v0.5 验收**：
1. 高风险 Task 必须收齐 ≥ 2 票才能 approved
2. SECURITY-01 投反对票 → 即使其他人都同意也不能 approved（SECURITY 一票否决）
3. 24h 无共识 → 自动 needs_human

### 10.6 v1.0 Schema Freeze + 第一批外部用户（9 周窗口）

**v1.0 唯一目标**：把 §3 五类 schema 冻结到 v1.0，并落第一个外部实现以证明协议可被第三方复用。

**v1.0 判定标准（沿用 §3.8 的 4 选 3）**：

- [ ] 至少 3 个第三方 schema 实现接入（含至少 1 个非作者实现）
- [ ] schema 跑过 90 天无 breaking change
- [ ] 至少 1 篇 Essay 级文档总结协议演化经验（候选：FCoP Essay 07 - Runtime Protocol Lessons）
- [ ] 通过 schema fuzz 测试（边界值 / 缺失 / 多余字段全覆盖）

**第一个外部实现的候选**（择一即可）：

| 候选 | 作者 | 价值 |
|---|---|---|
| `fcop-mcp` 升级到 §3.3 Task Schema 全字段 | FCoP 项目自己 | 证明跨语言（Python ↔ TS）协议兼容 |
| 第三方写一个 GitHub Issue → Task 适配器 | 社区 | 证明 §3.3 能接外部 Task 来源 |
| 第三方写一个 Skill（非作者维护的 MCP server） | 社区 | 证明 §3.6 Skill Schema 可被生态采纳 |

### 10.7 风险与回退（每个里程碑的 Plan B）

| 里程碑 | 主要风险 | Plan B（回退方案） |
|---|---|---|
| v0.1 | SDK API 变更 / Agent.resume 不稳 | fallback 到 stateless mode：每次 send 都新建 agent，Session 自己管 |
| v0.2 | WebSocket 中继不稳 / 推送延迟 | fallback 到 polling 模式（mobile 每 10s 拉一次 inbox） |
| v0.3 | 漂移检测 LLM-judge 误报多 | fallback 到只检测"卡死 / 越权 / 协议违规"3 类硬指标 |
| v0.5 | 三 reviewer 模型 cost 太高 | 默认 policy 改成"REVIEW + SECURITY 二选一即可"，AUDIT 转 async 离线 |
| v1.0 | 外部实现接入慢 | 先冻 internal v1.0，对外宣布"v1.0-rc"，等满足判定标准再正式 v1.0 |

> 📌 §10 是 §0.8/§0.9 的工程兑现。
> 后续任何 PR / sprint 计划必须能映射到 §10.2-§10.6 的某个 sprint，
> 否则 = scope creep，先回 §0.8 检查是否越界。

---

## 11. Packaging & Distribution（v2 用户最终拿到什么）

> **本章决策锁定（ADMIN 5/9 14:33）**：
>
> v2 沿用 v1 的「**双击 EXE = 码流**」产品形态。技术栈从 Python + PyInstaller
> 换成 Node 22+ 官方 single-executable application（`--experimental-sea-config`）。
> 新增 `codeflow-shell/` 子项目作为 v2 的"壳子"，内嵌 `@codeflow/runtime` + 系统托盘
> + Web Panel + Mobile PWA bridge。
>
> v1 EXE 在 v2 EXE 出厂后**保留 1 个 release cycle**作为 deprecation buffer，
> v0.3 触发归档到 `legacy/`。

### 11.0 一句话锁定

| 维度 | 决策 |
|---|---|
| 用户最终拿到 | `CodeFlow-v3.0.0.exe`（Windows 单 EXE）+ 后续 macOS/Linux pkg |
| 启动方式 | 双击 → 系统托盘 + 自启 web panel `http://127.0.0.1:18765`（沿用 v1 端口） |
| 安装前置 | **零额外依赖**（不需要装 Node / Python / Cursor IDE） |
| 与 Mobile PWA 关系 | EXE = PC 执行节点入口；PWA = Governance 入口（§0.9）；两者通过 `server/relay/` 配对 |
| 与 v1 EXE 关系 | v2 EXE 出厂后给 v1 用户 **1 release cycle** 缓冲，再归档 `legacy/` |
| 实施 sprint | **Sprint S6**（v0.1 Backend Kernel 最后一刷，§10.2 末位） |

### 11.1 为什么是 EXE，而不是 npm CLI 或 Mobile-only

#### 选项空间

| 路径 | 含义 | v0.x 是否采纳 |
|---|---|---|
| **X. 去 EXE 化** | Mobile PWA 主入口 + PC 守护进程（命令行） | ❌ |
| **Y. v2 也是 EXE**（本章采纳） | v2 沿用双击形态，技术栈换 Node SEA | ✅ |
| **Z. 双形态共生** | npm CLI + EXE 两条交付链并存 | ⏸ v1.0 后再评估（§10.6 触发） |

#### 不选 X（去 EXE 化）的 4 条理由

1. **270 commits + 19 releases 已训练用户预期**：v1 用户的"码流 = 一个图标"心智不是可丢的资产
2. **零安装摩擦是产品门槛**：让 v0.1 用户先装 Node 18+ = 流失
3. **PC 上的"图标"是产品锚点**：没有图标 = 产品在用户的开始菜单 / 任务栏 / 桌面没有"位置"
4. **跟 §0.9 Mobile-first 不冲突**：Mobile 是 *Governance Plane*（治理面），EXE 是 *Worker Plane*（执行面）；§0.7.4 的"三节点"结构里两者并存

#### 不选 Z（双形态共生）的 1 条理由

v0.x 阶段维护两条交付链 = 维护成本翻倍 + release 复杂度翻倍。等 v1.0 schema freeze + 第三方实现接入（§10.6 判据）后再考虑 npm 公开包发布。

#### 选 Y 的关键判据

> 「**v2 EXE 是 v1 EXE 的下一代，不是不同物种。**」
>
> 这跟 §0.7.2 「身份反转」一致：v1 是 *外挂*，v2 是 *Runtime*——但**用户拿到的还是同一种东西的下一代**（图标、双击、托盘、Web Panel）。
> 改变的是底层引擎（Python+pyautogui → Node+SDK），**不是**改变交付形态本身。

### 11.2 工程结构：`codeflow-shell/` 子项目

#### 仓内布局（Sprint S6 创建）

```text
codeflow-pwa/
├── packages/
│   ├── codeflow-protocol/         ← Sprint S1 已完成 ✅（5 schemas）
│   └── codeflow-runtime/          ← Sprint S2-S5 在做（kernel）
│
├── codeflow-shell/                ← Sprint S6 新增 ⭐（v2 的"壳子"）
│   ├── src/
│   │   ├── main.ts                ← 入口（启动 runtime + tray + panel + bridge）
│   │   ├── tray.ts                ← 系统托盘（继承 v1 codeflow-desktop/main.py 托盘行为）
│   │   ├── web-panel.ts           ← 内嵌 Express + 复用 web/pwa/ 静态资源
│   │   ├── relay-bridge.ts        ← 与 Mobile PWA 通信（沿用 v1 server/relay/ 协议）
│   │   └── lifecycle.ts           ← 单实例互斥 + 优雅退出 + 自启注册（继承 v1 行为）
│   ├── assets/
│   │   ├── app.ico                ← 沿用 v1 panel/app.ico
│   │   └── tray-icon.png
│   ├── sea-config.json            ← Node 22+ SEA 配置
│   ├── pack.cmd                   ← Windows 打包脚本（取代 v1 codeflow-desktop/pack.cmd）
│   ├── pack.sh                    ← macOS/Linux 打包脚本
│   ├── package.json
│   └── README.md
│
├── codeflow-desktop/              ← v1 EXE（freeze + deprecation buffer）
│
└── dist/
    ├── CodeFlow-Desktop-v2.12.17.exe   ← v1（继续提供 1 个 cycle）
    └── CodeFlow-v3.0.0.exe              ← v2 ⭐（用户最终下载）
```

#### 技术栈选型对比（W1=Y 决策展开）

| 候选 | 体积 | Node 版本 | 跨平台 | 是否第三方 | 评价 |
|---|---|---|---|---|---|
| **`node --experimental-sea-config`** | ~30MB | 22+（已稳定）| Win/macOS/Linux 都支持 | ❌ Node 官方原生 | ✅ **采纳** |
| `Bun.compile` | ~50MB | n/a（Bun runtime）| Win/macOS/Linux | Bun 官方 | ⏸ 备选（如 Node SEA 出问题） |
| `@vercel/pkg` | ~40MB | 18 LTS | 都支持 | ⚠️ 已 deprecated | ❌ 不采纳 |
| `Tauri 2.0` | ~10MB | 22+ + Rust | 都支持 | Rust 工具链 | ❌ 不采纳（要 Rust 工具链 + Webview） |
| `Electron` | ~150MB | 任意 | 都支持 | Electron | ❌ 不采纳（体积过大；跟 v1 ~30MB 形成断层） |

**采纳 Node SEA 的关键理由**：
- 官方原生（Node 22 LTS 已稳定）= 跟 Cursor SDK 同栈、零第三方依赖
- 体积 ~30MB ≈ v1 PyInstaller 包，用户感知"码流没变重"
- 不带 Webview/Chromium = web panel 仍走"系统浏览器/Cursor Simple Browser"模式（沿用 v1 行为）
- 升级路径清晰：Node 23/24 LTS 时 SEA 只会更稳

### 11.3 v2 EXE 的内部架构（4 层）

```text
┌──────────────────────────────────────────────────────────────────────┐
│ CodeFlow-v3.0.0.exe (Node SEA, 内嵌 codeflow-shell/src/main.js)        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Layer 1：Shell（codeflow-shell）                                    │
│      • 单实例互斥 + 系统托盘 + lifecycle                                │
│      • Web Panel 内嵌 (Express @ 18765)                              │
│      • Relay Bridge → Mobile PWA                                     │
│                                                                      │
│   Layer 2：Runtime Kernel（@codeflow/runtime）                       │
│      • AgentRegistry / SessionManager / Task Scheduler                │
│      • PersistentStore / RuntimeBootstrap                            │
│      • 6 个内核子系统（§2.1）                                         │
│                                                                      │
│   Layer 3：Protocol（@codeflow/protocol）                            │
│      • 5 schemas + AJV validator + CLI                               │
│                                                                      │
│   Layer 4：External Adapter                                          │
│      • CursorSdkAdapter → @cursor/sdk → cursor.com                   │
│      • FcopMcpClient → fcop-mcp（pip install） → 文件系统               │
│      • RelayClient → server/relay/ → Mobile PWA                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
        │                   │                       │
        ▼                   ▼                       ▼
   系统托盘 / 桌面图标   localhost:18765       Mobile PWA / Cursor / fcop
```

层级原则：

- **Shell 不直接调 Cursor SDK**，必须经 Runtime Kernel
- **Runtime Kernel 不知道有 Shell**（kernel 自身可以脱离 EXE 跑在 Node CLI 下，作为 Z 路径的预留通道）
- **Protocol 完全独立**（既能被 Kernel 用，也能被外部 npm 包用 = §10.6 触发后）
- **Adapter 层全部走 §3.6 Skill schema 描述**——Shell 加新外接能力（如 Slack 通知）= 不动 Kernel

### 11.4 v1 EXE 的退役共生（W3=b 落档）

#### 时间线

```text
[ Sprint S6 ─ v0.1 Backend Kernel 完成 ]    Q3 2026
   │
   ├─→ codeflow-shell/ 落地 + CodeFlow-v3.0.0.exe 首次出厂
   ├─→ v1 codeflow-desktop/ 进入 freeze（按 §8.2 已规划）
   └─→ Release notes 同时公告：
         "CodeFlow v3.0.0（v2 backend kernel）已发布"
         "CodeFlow Desktop v2.12.x 进入 deprecation buffer，下个 minor cycle 后归档"

[ Sprint S7-S10 ─ v0.2 Mobile Governance MVP ]    Q4 2026
   │
   ├─→ v1 EXE 仍可下载，但 GitHub Release 标 "deprecated"
   ├─→ Update notice：v1 用户运行时弹窗提示"v3.x 已发布"
   └─→ v2 EXE 完成 §0.8.3 Hello World demo + Mobile pairing

[ v0.3 触发节点 ]    Q1 2027
   │
   └─→ codeflow-desktop/ 整目录 git mv 到 legacy/codeflow-desktop-v1/
       README 加 "v1 archived" 链接
       Release page 不再显示 v2.12.x 下载链接
```

#### deprecation buffer 期间的判据

| 判据 | v1 → v2 切换条件 | 状态触发 |
|---|---|---|
| v2 EXE 完成 §0.8.3 Hello World demo | ≥ 1 次成功跑通 PM→DEV→REVIEW→DONE | 立即 deprecate v1 |
| v2 EXE 跑过 5 个真人用户验收 | ≥ 5 真人确认"双击就能用" | 锁定 v2 主链 |
| v2 EXE 兼容 v1 的 `docs/agents/codeflow.json` | v1 用户切换不需要重选团队 | 解除"切换流失" 担忧 |
| v0.3 释放完成 | §10.4 v0.3 sprint 全部 ship | 触发 `git mv` 到 legacy/ |

任一判据未达成 = deprecation buffer 延长，不强制 v0.3 触发。

### 11.5 与路径 X（去 EXE）/ 路径 Z（双形态）的兼容关系

| 路径 | v0.x 状态 | 长期可能性 |
|---|---|---|
| **Y（本章采纳）** | ✅ v0.1 起执行 | 主线 |
| X（去 EXE） | ❌ 不采纳 | 永远不采纳——但 §0.9 Mobile-first **本身就涵盖 X 的核心精神**（手机扫码即用 + PC 退化为执行节点），所以"X 的价值"已通过 PWA 实现 |
| Z（双形态共生） | ⏸ 不采纳 | v1.0 schema freeze 后 + §10.6 第三方实现接入 ≥ 3 个 → 释放 npm 公开包：`npm install -g @codeflow/runtime` |

**关键认识**：路径 Y 不排斥 X / Z；它只锁定"v0.x 阶段用户拿到的是 EXE"。
- §11.3 Layer 2 (Runtime Kernel) 可独立脱离 Shell 运行 = Z 路径的工程预留
- §11.3 Layer 1 (Shell) 是可选层 = X 路径的工程预留（如果将来真有用户只用 Mobile PWA）

### 11.6 Sprint 归属：Sprint S6（v0.1 最后一刷）

把 §10.2 v0.1 Backend Kernel 路线图重新对照：

| Sprint | 主题 | 状态 |
|---|---|---|
| S1 | Skeleton + 协议冻结（@codeflow/protocol）| ✅ 已完成 |
| S2 | AgentRegistry + Session 设计骨架 | ✅ 已完成 |
| S3 | Task Scheduler + AgentRegistry/Session 真实实现 | 🚀 进行中 |
| S4 | Skill Runtime | ⏳ 待启动 |
| S5 | Review Engine | ⏳ 待启动 |
| **S6** | **E2E mini demo + `codeflow-shell/` 落地 + 第一个 v2 EXE 出厂** | ⏳ 待启动 |

**S6 sprint 范围扩展**（原 §10.2 仅"E2E mini demo"，本章追加 codeflow-shell/）：

```text
原 S6（§10.2 line 2245-2249）：
  - E2E mini demo：跑通 §0.8.3 Hello World
  - SDK / FCoP / Mobile bridge 集成

本章追加：
  - codeflow-shell/ 子项目创建 + main.ts/tray.ts/web-panel.ts/relay-bridge.ts
  - sea-config.json + pack.cmd + pack.sh
  - assets/app.ico 从 v1 codeflow-desktop/panel/ 继承
  - dist/CodeFlow-v3.0.0.exe 首次发布
  - GitHub Release: "CodeFlow v3.0.0 — first release on v2 backend kernel"
  - Release notes 同步公告 v1 进入 deprecation buffer
```

### 11.7 Sprint S6 acceptance（v2 EXE 出厂判据）

| # | 判据 | 验证方式 |
|---|---|---|
| 1 | EXE 在 Win10/11 干净虚拟机双击运行 | 不弹出"先装 Node"等任何依赖错误 |
| 2 | 系统托盘出现"CodeFlow v3"图标 | 视觉检查 + 右键菜单 含 "Open Panel / Quit" |
| 3 | Web Panel 自动开浏览器到 `http://127.0.0.1:18765` | 沿用 v1 端口（保证 Mobile pairing 不破） |
| 4 | 与 Mobile PWA 配对成功 | 扫二维码 → relay 双向连通 |
| 5 | 跑通 §0.8.3 Hello World Demo | 一份 TASK → DEV agent → REVIEW → DONE |
| 6 | EXE 体积 ≤ 50MB | 跟 v1 PyInstaller ~30MB 同量级（不出现 Electron 级膨胀） |
| 7 | EXE 启动时间 ≤ 3 秒 | 桌面双击 → 托盘出现 ≤ 3s |
| 8 | 跨平台 pkg 至少出 macOS arm64 + Linux x64 | 不只是 Windows |
| 9 | 与 v1 共存测试 | v1 EXE 和 v2 EXE 同时运行，不抢端口（v2 用 18765，v1 已经用 18765 → 需端口检测降级到 18766）|
| 10 | Sprint S6 acceptance 复用 §0.8.3 验收脚本 | 单一 source-of-truth |

### 11.8 风险与回退

| 风险 | 概率 | Plan B |
|---|---|---|
| Node SEA 在 Node 22 LTS 仍标 experimental（Node 24 才稳定） | 中 | fallback 到 `Bun.compile`（同样 single-executable，体积稍大但跨平台稳） |
| `@cursor/sdk` 在 SEA 内不能正常加载 native binding | 低 | 改用"EXE + sidecar Node 进程"模式（类似 Tauri） |
| Mobile PWA 配对协议在 v2 跟 v1 不兼容 | 低 | server/relay/ 加 v1/v2 兼容层，按 client_type 分发 |
| 用户拒绝从 v1 EXE 切换 | 中 | deprecation buffer 延长到 v0.5（§10.5 触发再砍） |
| Windows Defender 误报 SEA 包成"未签名"风险 | 高 | 申请 EV code-signing 证书（v0.2 起做）；同时提供"无签名版本"+ md5 校验码 |

### 11.9 与现有章节的索引

| 议题 | 锚点章节 |
|---|---|
| 为什么 v2 不再做 UI 自动化 | §0.7.2「身份反转」 |
| EXE 在三节点架构里的位置 | §0.7.4 / §1.2「三节点分布式 Runtime」 |
| EXE 与 Mobile PWA 的分工 | §0.9.1 / §0.9.2「Worker / Governance / Admin」 |
| EXE 内嵌的 6 大子系统 | §2.1「CodeFlow Runtime 6 大内核子系统」 |
| EXE 跑出第一个 demo 的脚本 | §0.8.3「Hello World Demo 验收」 |
| v1 EXE 的归档时间表 | §8.2 / §8.5 / §10.4 |
| 第三方实现接入触发 npm 包发布 | §10.6 v1.0 Schema Freeze 判据 |

> 📌 §11 是 §0.7 + §0.9 在"用户实际拿到什么"维度的工程兑现。
> 后续任何关于"码流怎么发布 / 怎么安装 / 怎么升级"的讨论，必须先回 §11.0 决策锁定 + §11.1 选项空间。

---

## 12. 附录

### 12.1 参考链接

- **对外速读版（本仓内）：[`docs/codeflow-overview.md`](../codeflow-overview.md)** —— 5 分钟读完的一页纸版本，给非技术读者 / 第一次接触 v2 的人
- [FCoP 公仓 (GitHub Pages)](https://joinwell52-ai.github.io/FCoP/)
- [FCoP Zenodo DOI](https://doi.org/10.5281/zenodo.19886036)
- [Cursor SDK (TypeScript)](https://cursor.com/docs/api/sdk/typescript)
- [Cursor 论坛 issue #158480 - Doorbell primitive](https://forum.cursor.com/t/feature-request-chat-notify-primitive-we-already-have-the-mailbox-files-we-just-need-the-doorbell/158480)
- [Spike PoC: `_ignore/spike_sdk_doorbell/`](../../_ignore/spike_sdk_doorbell/) (本仓本地，已验证)
- [Node.js Single Executable Applications](https://nodejs.org/api/single-executable-applications.html) (Node 22+ SEA, §11 关键依赖)

### 12.2 相关 Essay（FCoP 公仓）

- Essay 01 - The Natural Protocol
- Essay 02 - Filename as Protocol
- Essay 03 - Mailbox vs Doorbell
- Essay 04 - Why YAML Front-matter
- Essay 05 - Cross-language Compatibility
- Essay 06 - Patrol vs Governance Patrol（v1 → v2 灵魂转世，详见 §0.9.5.A）
- Essay 07 - Runtime Protocol Lessons（v1.0 时撰写，详见 §10.6）

### 12.3 术语表

| 术语 | 定义 | 章节 |
|---|---|---|
| **CodeFlow AI Runtime** | 项目正式名 | §0 / §0.7.5 |
| **FCoP** | File-based Coordination Protocol，本 Runtime 寄生的协议 | §0.6.2 |
| **Agent Governability** | 让概率性 LLM 可治理的能力，本 Runtime 的护城河 | §0.6.7 |
| **Runtime Engineering** | "运行时工程"——v2 切入的新学科 | §0.6.5 |
| **Governance Plane** | 治理面，对应 Mobile 节点 | §0.7.4 / §0.9 |
| **Layer (worker/governance/admin)** | 三层组织结构的 schema 化字段 | §0.9.1 / §3.2 |
| **HITL (Human-in-the-loop)** | 高风险操作的人工拍板机制 | §0.9.4 |
| **needs_human** | Review decision 的特殊枚举值，触发 Mobile 推送 | §3.4 |
| **Doorbell** | "门铃"——SDK 通过 `Agent.resume()` 唤醒长存 agent 的机制 | §0 / §2.1 #2 |
| **codeflow-shell** | v2 EXE 的"壳子"子项目（Node SEA + 托盘 + Web Panel + Relay Bridge）| §11.2 |
| **Node SEA** | Node 22+ 官方 single-executable application 机制 | §11.2 |

### 12.4 起草历史（Draft History）

| 刀次 | 范围 | 关键产物 |
|---|---|---|
| 第一刀 | §0 + §1 + §2 骨架 | 基础架构 + roles.yaml |
| 第二刀 | §0.5 + §0.6 + §3 | AI OS 雏形论 + 5 类 schema |
| 第三刀 | §0.6.7 + §0.6.8 + §0.8 + §2.1.1 | 护城河 + Docker 前夜 + scoping + Review Engine 标星 |
| 第四刀 | §0.7.4 升级 + §0.7.5 副定位 + §0.9 全章 | Mobile-first Governance |
| 第五刀 | §0.0 Executive Summary + §3 schema 兑现 §0.9 + §10 路线图 + §11 附录 | 文档闭合：愿景→协议→sprint |
| **第六刀** | §11 Packaging & Distribution（v2 EXE 路径锁定）+ §12 附录改名 + §0.0 升格"四总纲"（含第 3 句协作宇宙 + 第 4 句 ADMIN 治理三动作）+ §3.0 设计哲学节 | ADMIN 5/9「按推荐」三连：13:51 L2 协作宇宙 + 14:33 W1/W2/W3 v2 EXE + 15:17 第 4 句宪法 |

---
