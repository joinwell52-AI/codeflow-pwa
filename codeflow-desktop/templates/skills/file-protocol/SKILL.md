---
name: file-protocol
description: "CodeFlow file-driven collaboration protocol — read tasks, write reports, manage issues. 文件驱动协作协议——读任务、写报告、管理问题。"
---

# CodeFlow File Protocol / 码流（CodeFlow）文件驱动协议

## Overview / 概述

**CodeFlow (码流)** uses files as the communication protocol between agents. All collaboration happens through reading and writing Markdown files in `docs/agents/`.

**码流（CodeFlow）** 使用文件作为 Agent 间的通信协议。所有协作通过读写 `docs/agents/` 下的 Markdown 文件完成。

## Directory Layout / 目录结构

| Directory | Purpose | Writer | Reader |
|-----------|---------|--------|--------|
| `tasks/` | Task assignments / 任务单 | Leader / External | Assigned role |
| `reports/` | Completion reports / 完成报告 | Executor | Leader |
| `issues/` | Issue records / 问题记录 | Anyone | Everyone |
| `log/` | Archives / 历史归档 | Leader | Read-only |

## Filename Parsing / 文件名解析

```
TASK-20260403-001-PM-to-DEV.md
     ^^^^^^^^ ^^^ ^^ ^^^
     date     seq sender recipient
     日期     序号 发件人  收件人
```

**Role codes are fully customizable / 角色代码完全可自定义：**

Preset teams / 预设团队：

| Dev Team / 软件开发 | Media Team / 自媒体 | MVP Team / 创业MVP |
|---------------------|--------------------|--------------------|
| PM (Project Manager / 项目经理) | PUBLISHER (审核发行) | MARKETER (增长运营) |
| DEV (Developer / 开发工程师) | COLLECTOR (素材采集) | RESEARCHER (市场调研) |
| QA (QA Engineer / 测试工程师) | WRITER (拟题提纲) | DESIGNER (产品设计) |
| OPS (DevOps / 运维工程师) | EDITOR (润色编辑) | BUILDER (快速原型) |

Custom roles / 自定义角色：use `create_custom_team` tool.
Example: `BOSS, CODER, TESTER, ARTIST`

## Task Frontmatter / 任务单元数据

```yaml
---
task_id: TASK-20260403-001
sender: PM
recipient: DEV
created_at: 2026-04-03 10:00:00
priority: normal | urgent | low
type: feature | bugfix | review | deploy | research | content
---
```

## Report Format / 报告格式

```markdown
---
task_id: TASK-20260403-001
reporter: DEV
reported_at: 2026-04-03 12:00:00
status: completed | partial | blocked
---

# Report / 完成报告

## What was done / 执行内容

## Result / 执行结果

## Evidence / 证据

## Next steps / 后续建议
```

## How-To / 操作指南

### Receive a task / 接收任务

1. Call `list_tasks(recipient="YOUR_ROLE")`
2. Call `read_task(filename)` for details
3. Execute the task

### Submit a report / 提交报告

1. Create file in `docs/agents/reports/`
2. Filename: `TASK-{same-id}-{YOUR_ROLE}-to-{sender}.md`
3. Include: what you did, results, evidence

### Record an issue / 记录问题

1. Create file in `docs/agents/issues/`
2. Filename: `ISSUE-{date}-{seq}-{summary}.md`
3. Include severity: P0 (critical) / P1 (important) / P2 (normal)
