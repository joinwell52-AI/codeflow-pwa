---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: fcop_0_6_library_split
priority: P1
created_at: 2026-04-23T15:20:00+08:00
---

# FCoP 0.6 库拆分 · D3 + D4 阶段性交付报告

## 背景

本会话延续 `feat/0.6-library-split` 分支，目标是把 `fcop` 拆成
**纯 Python 库**（`fcop`）+ **MCP 薄壳**（`fcop-mcp`）。
D1 + D2（骨架 + core 基础模块）已合入前序提交；本轮集中完成
D3（Project 门面 + 任务 CRUD + 初始化 + 归档 / 巡检）和 D4
（Report / Issue CRUD）。

## 交付清单

### D3 — Project 门面（已在早些时候推送）

1. **D3-c1** · `Project` 身份层
   - `config_path` / `config` / `is_initialized()` / `status()`
   - `fcop.core.config` 解析器（兼容旧版 `"mode": "team"` / dict roles）
2. **D3-c2** · 任务 CRUD
   - `write_task` · 原子占位（`O_EXCL` + 重试）
   - `list_tasks` · sender / recipient / status / date 过滤，宽容跳过坏文件
   - `read_task` · 支持全名或 `TASK-YYYYMMDD-NNN` 前缀
3. **D3-c3** · 项目初始化
   - `init` / `init_solo` / `init_custom` / 静态 `validate_team`
   - `fcop.teams` 内置 4 个预设团队元数据（dev / media / mvp / qa）
4. **D3-c4** · 归档与巡检
   - `archive_task` · 级联归档引用该任务的 reports
   - `inspect_task` · 不抛异常，返回 `ValidationIssue` 列表

### D4 — Report / Issue CRUD（本次推送）

5. **D4-c1** · Report CRUD（commit `db016d2`）
   - `write_report` · 强制 **Rule 5**（只能由任务 recipient 回执）
   - `status` ∈ {done, blocked, in_progress}，写入 top-level YAML
   - `list_reports` · reporter / task_id 过滤，支持 open / archived / all 三种范围
   - `read_report` · 全名或 `REPORT-YYYYMMDD-NNN` 前缀解析
6. **D4-c2** · Issue CRUD（commit `cc99bd5`）
   - Issues 为广播，无 recipient；`summary` / `severity` 为顶层字段
   - 独立的 frontmatter 解析器（不复用 `TaskFrontmatter`，避免字段错配）
   - `write_issue` / `list_issues` / `read_issue` + severity 别名归一化

## 质量数据

| 指标 | 数值 |
|---|---|
| 测试用例 | **392** 全绿 |
| `ruff check` | 0 warning / error |
| 新增代码 | 约 1350 行（含测试） |
| 纯工具无 I/O 层 | `core/schema.py` / `core/filename.py` / `core/frontmatter.py` / `core/config.py` |
| 唯一 I/O 入口 | `Project` 门面 |

## 影响范围

- **只影响 0.6 预发布线**（`feat/0.6-library-split` 分支），未触碰
  `main` 或 `codeflow-plugin/` 下的运行时。
- `fcop` 库暂不具备运行时依赖外的功能（`deploy_role_templates`
  / `drop_suggestion` / `fcop.rules` 仍是 `NotImplementedError` 桩），
  不能作为生产库直接使用，当前只支持 **在本仓库内跑测试**。
- 运行时新增依赖：`pyyaml>=6.0,<7.0`（已在前序会话中经 ADMIN 确认）。

## 下一步计划（按优先级）

1. **D5** · 团队模板 + `fcop.rules` + `deploy_role_templates`
   + `drop_suggestion`（把老版本内置的模板文本搬过来）
2. **MIGRATION-0.6.md** 初稿（0.4 / 0.5 用户的迁移指南）
3. **docs/release-process.md**（双包发布流程 · `fcop` + `fcop-mcp`）
4. 从 `codeflow-plugin/src/fcop/server.py` 摘 ~500 行纯工具函数
   并迁到 `fcop/core/`（工具代码最后一公里复用）
5. 配 GitHub `test-fcop` / `test-fcop-mcp` workflow，开 branch
   protection

## 需要 ADMIN 决策的点

- **暂无阻塞项**。D5 可以直接开工；如希望我先写 MIGRATION-0.6 让
  早期 0.5 用户能提前看到升级路径，请指一下。

## 是否建议继续

建议继续。D4 完成后已经是一个自洽的「只读 + CRUD」库，D5 完成
后可以发 `0.6.0rc1` 让你试装。

— PM-01
