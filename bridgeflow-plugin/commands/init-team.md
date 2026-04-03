---
name: init-team
description: Initialize BridgeFlow collaboration workspace with a team template
---

# 初始化 BridgeFlow 团队

使用 BridgeFlow MCP Server 的 `init_project` 工具来初始化项目协作空间。

## 步骤

1. 调用 `init_project` 工具，传入团队模板参数
2. 可选模板：
   - `dev-team` — 软件开发团队（PM, DEV, QA, OPS）
   - `media-team` — 自媒体团队（PUBLISHER, COLLECTOR, WRITER, EDITOR）
   - `mvp-team` — 创业MVP团队（MARKETER, RESEARCHER, DESIGNER, BUILDER）
3. 工具会自动创建 `docs/agents/` 目录结构和欢迎任务

## 示例

```
请帮我初始化一个软件开发团队的协作空间
```

等价于调用：`init_project(team="dev-team")`
