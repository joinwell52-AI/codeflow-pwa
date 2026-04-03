---
name: switch-team
description: Switch BridgeFlow team template without losing existing data
---

# 切换团队模板

切换团队模板会更新角色配置，但不会删除已有的任务和报告文件。

## 步骤

1. 查看可用模板：调用 `get_available_teams` 工具
2. 重新初始化：调用 `init_project(team="新模板名")`
3. 旧的任务文件会保留，新的角色配置会覆盖 `bridgeflow.json`

## 注意

- 切换模板后，旧的任务单中的角色代码不会自动更新
- 建议先将旧任务归档（`archive_task`），再切换模板
- 切换后需要重新为各 Agent 窗口分配对应的角色
