# 码流（CodeFlow）Agent 文件结构

**码流（CodeFlow）** 的第一阶段不是做"手机聊天软件"，而是做"人类角色进入团队协议"的文件系统骨架。

因此 `docs/agents/` 是这个项目的核心协作目录。

---

## 核心原则（北极星）

> **AI 角色之间不能只在脑子里说话，必须落成文件。**

这是整套 agent 协议的总则。下面所有规则（命名约定、文件协议、YAML 元数据头、
"一条消息 = 一条文件"等）都是**这条原则在不同场景下的具体落地**。

这条总则不是人类一次性设计出来的，而是来自一次"人机共同演化"——一个 Cursor agent 在 2026-04-20
执行完全无关的视频生成任务时，自发把散落在本项目 `.cursor/rules/` 里七条技术规定升华成了
一句话，我们再把它反向收编成总则。完整事件与证据档案见
[FCoP 公仓 · fcop-natural-protocol.md](https://github.com/joinwell52-AI/FCoP/blob/main/essays/fcop-natural-protocol.md)。

---

## 目录结构

```text
docs/agents/
├── README.md                  # 本文件：说明 agent 文件结构
├── ADMIN-01.md                # 真人角色 ADMIN 的职责说明
├── PM-01.md                   # PM 角色说明
├── DEV-01.md                  # DEV 角色说明
├── OPS-01.md                  # OPS 角色说明
├── QA-01.md                   # QA 角色说明
├── tasks/                     # 任务文件
├── reports/                   # 回执/报告文件
├── log/                       # 通知与归档摘要
└── issues/                    # 问题记录
```

---

## 角色命名规范

同一个角色在不同场景有不同写法，**所有四套团队统一遵循以下规则**。

### 命名规则

| 场景 | 格式 | 示例 | 说明 |
|------|------|------|------|
| **文件名 sender/recipient** | `角色名`（无连字符无序号） | `PM`、`QA`、`COLLECTOR` | 用于 `TASK-*-PM-to-QA.md` |
| **Cursor Tab 显示名** | `序号-角色名` | `01-PM`、`03-QA`、`01-COLLECTOR` | Cursor Agents 面板中 Pin 时设置 |
| **角色定义文档名** | `角色名-序号.md` | `PM-01.md`、`COLLECTOR.md` | `docs/agents/` 或 `templates/agents/` |
| **巡检器内部** | 纯角色名（自动归一化） | `PM`、`QA`、`COLLECTOR` | 代码中 `_role_key_for_task()` 自动处理 |

### dev-team 角色清单（软件研发）

| 序号 | Cursor Tab | 文件协议 | 定义文档 | 职责 |
|------|-----------|----------|----------|------|
| 01 | `01-PM` | `PM` | `PM-01.md` | 项目经理 / 任务调度 |
| 02 | `02-DEV` | `DEV` | `DEV-01.md` | 全栈开发 |
| 03 | `03-QA` | `QA` | `QA-01.md` | 测试工程师 |
| 04 | `04-OPS` | `OPS` | `OPS-01.md` | 运维部署 |
| — | — | `ADMIN` | `ADMIN-01.md` | 真人管理员（不在 Cursor 中） |

### media-team 角色清单（自媒体内容）

| 序号 | Cursor Tab | 文件协议 | 定义文档 | 职责 |
|------|-----------|----------|----------|------|
| 01 | `01-COLLECTOR` | `COLLECTOR` | `COLLECTOR.md` | 素材采集 |
| 02 | `02-WRITER` | `WRITER` | `WRITER.md` | 内容撰写 |
| 03 | `03-EDITOR` | `EDITOR` | `EDITOR.md` | 编辑审校 |
| 04 | `04-PUBLISHER` | `PUBLISHER` | `PUBLISHER.md` | 发布运营 |

### mvp-team 角色清单（快速验证）

| 序号 | Cursor Tab | 文件协议 | 定义文档 | 职责 |
|------|-----------|----------|----------|------|
| 01 | `01-BUILDER` | `BUILDER` | `BUILDER.md` | 产品构建 |
| 02 | `02-DESIGNER` | `DESIGNER` | `DESIGNER.md` | UI/UX 设计 |
| 03 | `03-MARKETER` | `MARKETER` | `MARKETER.md` | 市场推广 |
| 04 | `04-RESEARCHER` | `RESEARCHER` | `RESEARCHER.md` | 用户调研 |

### qa-team 角色清单（专项测试）

| 序号 | Cursor Tab | 文件协议 | 定义文档 | 职责 |
|------|-----------|----------|----------|------|
| 01 | `01-LEAD-QA` | `LEAD-QA` | `LEAD-QA.md` | 测试负责人 |
| 02 | `02-TESTER` | `TESTER` | `TESTER.md` | 功能测试 |
| 03 | `03-AUTO-TESTER` | `AUTO-TESTER` | `AUTO-TESTER.md` | 自动化测试 |
| 04 | `04-PERF-TESTER` | `PERF-TESTER` | `PERF-TESTER.md` | 性能测试 |

### 归一化规则

巡检器用 `_role_key_for_task()` 统一提取**纯角色名**做匹配，所有写法都能正确识别：

```
PM           → PM            去尾部数字
01-PM          → PM            去前缀数字+连字符
PM-01          → PM            去连字符+尾部数字
03-QA          → QA
QA           → QA
COLLECTOR      → COLLECTOR     已经是纯角色名
01-COLLECTOR   → COLLECTOR
AUTO-TESTER    → AUTO-TESTER   保留中间连字符
03-AUTO-TESTER → AUTO-TESTER
```

### 历史兼容

旧版文件协议使用 `PM`、`QA` 作为 sender/recipient，巡检器能正确归一化处理。
新建任务文件**建议直接用纯角色名**（`PM`、`QA`），也兼容旧格式。

---

## 文件协议

### 任务文件

命名格式：

```text
TASK-YYYYMMDD-序号-发送方-to-接收方.md
```

例如：

- `TASK-20260401-001-ADMIN-to-PM.md`
- `TASK-20260401-002-PM-to-ADMIN.md`
- `TASK-20260401-003-PM-to-DEV.md`
- `TASK-20260401-004-PM-to-COLLECTOR.md`（media-team 场景）

历史格式也兼容：`TASK-20260401-001-ADMIN-to-PM.md`

### 规则

- 一条消息 = 一条文件
- 手机端发给 PM 的文本，必须落成 `TASK-*-ADMIN-to-PM.md`
- PM 回给 ADMIN 的文本，必须落成 `TASK-*-PM-to-ADMIN.md`
- DEV/OPS/QA 若直接回人，也必须走 `XX-to-ADMIN`
- 不允许引入第二套"仅聊天、不落文件"的协议

### 标准写入方式

为了避免手工写 Markdown 出现字段遗漏，当前建议优先使用 CLI 生成标准文件：

```powershell
CodeFlow write-admin-task --text "请 PM 帮我安排下一步任务"
CodeFlow write-reply --sender PM --text "已接单，开始拆解任务" --thread-key "demo-thread-001"
```

其中：

- `write-admin-task` 默认写入 `tasks/`
- `write-reply` 默认写入 `reports/`
- 两者都会自动带上 FCoP 协议的元数据头

### 协议元数据

从当前版本开始，`TASK` Markdown 文件头部会携带一段轻量元数据：

```text
---
protocol: fcop
version: 1
kind: task
sender: ADMIN
recipient: PM
priority: P1
source: ADMIN-mobile
thread_key: 20260401-123000-ADMIN-to-PM
created_at: 2026-04-01 12:30:00
attachments_count: 0
---
```

这段元数据的作用是：

- 让桌面桥接器稳定解析 `sender`、`recipient`、`thread_key`
- 让手机端能基于 `thread_key` 聚合同一线程
- 兼容后续接入更多角色适配器，而不依赖纯文本正则猜测

#### `protocol:` 与 `version:` 字段说明

- **`protocol: fcop`** ——可移植标识符，告诉任何读者（Agent、工具、人）
  "这是 FCoP 协作文档，不是普通笔记"。规范值统一为小写 `fcop`
  （遵循 `http` / `grpc` 等 machine-identifier 惯例）；品牌名 `FCoP`
  用在文档标题、对外文章里。历史别名 `agent_bridge`（2026-04-20 之前的内部代号）
  以及 `agent-bridge` / `file-coordination` 等变体，都会被 `_parse_frontmatter`
  自动归一化为 `fcop`，存量文件无需迁移。
- **`version: 1`** ——协议版本号。**整数**，不加引号、不加小数点。
  只在协议本身发生破坏性变更（例如字段语义变更、必填字段增删）时才 +1，
  **不要**用它来记录单份文档的修订。存量写成 `1.0` / `"1.0"` 的文件也会被
  归一化成 `"1"`，无需强迫升级。

## 团队模板说明

`codeflow-desktop/templates/agents/` 下包含多套预置团队模板，按场景选用：

| 团队目录 | 适用场景 | 核心角色 |
|----------|----------|----------|
| `dev-team/` | 软件研发团队 | PM, DEV, OPS, QA, ADMIN |
| `media-team/` | 自媒体内容团队 | COLLECTOR, WRITER, EDITOR, PUBLISHER |
| `mvp-team/` | 快速 MVP 验证 | BUILDER, DESIGNER, MARKETER, RESEARCHER |
| `qa-team/` | 专项测试 / 质量团队 | LEAD-QA, TESTER, AUTO-TESTER, PERF-TESTER |

用户在 CodeFlow Desktop 初始化时选择团队模板，系统自动：
1. 复制对应的角色定义文件到 `docs/agents/`
2. 在 Cursor 中创建对应的 Agent Tab（按序号+角色名命名）
3. 巡检器自动识别所有角色并开始巡检

---

## 第一阶段角色定位

### ADMIN

- 代表真实人类用户
- 默认由手机端 PWA 使用
- 负责发需求、追问进度、接收回复

### PM

- 负责接收 `ADMIN` 的任务
- 把需求拆给 DEV / OPS / QA
- 再把结果回给 `ADMIN`

### DEV / OPS / QA

- 作为团队内部执行角色
- 第一阶段不要求手机端直接与这三者沟通

## 为什么要这样设计

因为如果手机端只是"看消息"，而不落文件，会出现两套体系：

1. 团队内部：`TASK-*.md`
2. 手机端：独立聊天记录

这会让项目归档、追责、追踪线程全部变乱。

所以 **码流（CodeFlow）** 第一阶段坚持：

**让所有文本沟通都回到文件协议。**

## 协议命名

本项目内部把这套文件协作方式命名为 `agent_bridge`：

- 应用层名字叫 **码流（CodeFlow）**（技术标识可用 `CodeFlow`）
- 落地协作协议叫 `agent_bridge`
- 协议核心仍然是 `TASK-YYYYMMDD-序号-发送方-to-接收方.md`
