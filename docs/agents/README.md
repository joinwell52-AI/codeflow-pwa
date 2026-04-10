# 码流（CodeFlow）Agent 文件结构

**码流（CodeFlow）** 的第一阶段不是做“手机聊天软件”，而是做“人类角色进入团队协议”的文件系统骨架。

因此 `docs/agents/` 是这个项目的核心协作目录。

## 目录结构

```text
docs/agents/
├── README.md                  # 本文件：说明 agent 文件结构
├── ADMIN-01.md                # 真人角色 ADMIN01 的职责说明
├── PM-01.md                   # 预留：PM01 角色说明
├── DEV-01.md                  # 预留：DEV01 角色说明
├── OPS-01.md                  # 预留：OPS01 角色说明
├── QA-01.md                   # 预留：QA01 角色说明
├── E2E-01.md                  # 端到端测试专员：全链路 UI/集成测试
├── tasks/                     # 任务文件
├── reports/                   # 回执/报告文件
├── log/                       # 通知与归档摘要
└── issues/                    # 问题记录
```

## 文件协议

### 任务文件

命名格式：

```text
TASK-YYYYMMDD-序号-发送方-to-接收方.md
```

例如：

- `TASK-20260401-001-ADMIN01-to-PM01.md`
- `TASK-20260401-002-PM01-to-ADMIN01.md`
- `TASK-20260401-003-PM01-to-DEV01.md`

### 规则

- 一条消息 = 一条文件
- 手机端发给 PM 的文本，必须落成 `TASK-*-ADMIN01-to-PM01.md`
- PM 回给 ADMIN 的文本，必须落成 `TASK-*-PM01-to-ADMIN01.md`
- DEV/OPS/QA 若直接回人，也必须走 `XX01-to-ADMIN01`
- 不允许引入第二套“仅聊天、不落文件”的协议

### 标准写入方式

为了避免手工写 Markdown 出现字段遗漏，当前建议优先使用 CLI 生成标准文件：

```powershell
CodeFlow write-admin-task --text "请 PM 帮我安排下一步任务"
CodeFlow write-reply --sender PM01 --text "已接单，开始拆解任务" --thread-key "demo-thread-001"
```

其中：

- `write-admin-task` 默认写入 `tasks/`
- `write-reply` 默认写入 `reports/`
- 两者都会自动带上 `agent_bridge` 元数据头

### 协议元数据

从当前版本开始，`TASK` Markdown 文件头部会携带一段轻量元数据：

```text
---
protocol: agent_bridge
version: 1
kind: task
sender: ADMIN01
recipient: PM01
priority: P1
source: ADMIN01-mobile
thread_key: 20260401-123000-ADMIN01-to-PM01
created_at: 2026-04-01 12:30:00
attachments_count: 0
---
```

这段元数据的作用是：

- 让桌面桥接器稳定解析 `sender`、`recipient`、`thread_key`
- 让手机端能基于 `thread_key` 聚合同一线程
- 兼容后续接入更多角色适配器，而不依赖纯文本正则猜测

## 团队模板说明

`codeflow-desktop/templates/agents/` 下包含多套预置团队模板，按场景选用：

| 团队目录 | 适用场景 | 核心角色 |
|----------|----------|----------|
| `dev-team/` | 软件研发团队 | PM-01, DEV-01, OPS-01, QA-01, ADMIN-01 |
| `mvp-team/` | 快速 MVP 验证 | BUILDER, DESIGNER, MARKETER, RESEARCHER |
| `media-team/` | 自媒体内容团队 | PUBLISHER, COLLECTOR, WRITER, EDITOR |
| `qa-team/` | 专项测试 / 质量团队 | LEAD-QA, TESTER, AUTO-TESTER, PERF-TESTER |

### qa-team 角色说明

| 角色 | 职责 | 接收任务来源 |
|------|------|-------------|
| LEAD-QA | 测试负责人，统筹测试策略，汇总结论回报 PM-01 | PM-01 |
| TESTER | 功能测试，编写并执行功能用例 | LEAD-QA |
| AUTO-TESTER | 自动化测试，维护测试脚本和 CI 集成 | LEAD-QA |
| PERF-TESTER | 性能测试，压力/负载测试和瓶颈分析 | LEAD-QA |

---

## 第一阶段角色定位

### ADMIN01

- 代表真实人类用户
- 默认由手机端 PWA 使用
- 负责发需求、追问进度、接收回复

### PM01

- 负责接收 `ADMIN01` 的任务
- 把需求拆给 DEV / OPS / QA
- 再把结果回给 `ADMIN01`

### DEV01 / OPS01 / QA01 / E2E01

- 作为团队内部执行角色
- 第一阶段不要求手机端直接与这四者沟通
- `E2E-01` 专注全链路端到端测试，覆盖 PWA / 中继 / 桌面端 / 文件协议 / AI角色协作流

## 为什么要这样设计

因为如果手机端只是“看消息”，而不落文件，会出现两套体系：

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
