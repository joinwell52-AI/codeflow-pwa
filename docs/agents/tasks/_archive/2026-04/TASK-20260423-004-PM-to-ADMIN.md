---
protocol: FCoP
version: 1.1
sender: PM-01
recipient: ADMIN-01
priority: P1
thread_key: fcop-0.6-pre1.0-charter
subject: D7 完成：fcop-mcp 24 tools + 10 resources + 合同测试 + CI 全落地
references:
  - TASK-20260423-003-PM-to-ADMIN.md
  - adr/ADR-0002-package-split-and-migration.md
  - adr/ADR-0003-stability-charter.md
---

# 回执：D7（fcop-mcp 薄壳）全部完成

## ADMIN 的指令

> 直接按这个往下走

按 003 回执承诺的五个子任务 D7-a → D7-e 一次性做完，全部已 commit +
push 到 `feat/0.6-library-split`。**0.6 pre-release 的代码基本就位**。

## 已完成

### D7-a：`mcp/` 子包骨架（commit `9a32976`）

| 项 | 内容 |
|---|---|
| 包结构 | `mcp/src/fcop_mcp/{__init__,__main__,server,_version,py.typed}` |
| 构建 | `mcp/pyproject.toml`（hatchling；dynamic version；`fcop>=0.6,<0.7`） |
| 入口 | `fcop-mcp` console script → `fcop_mcp.__main__:main` |
| README | 安装、Cursor/Claude Desktop 配置样例、版本锁说明 |
| 路径解析 | 还原 0.5.4 级联：session pin → `FCOP_PROJECT_DIR` → 旧 `CODEFLOW_PROJECT_DIR`（带 deprecation warning）→ 自动探测标记 → cwd |

### D7-b：核心 tool 薄壳（commit `5a261e4`）

13 个 tool：`set_project_dir` / `init_project` / `init_solo` /
`create_custom_team` / `validate_team_config` / `write_task` /
`read_task` / `list_tasks` / `inspect_task` / `archive_task` /
`write_report` / `list_reports` / `read_report` / `write_issue` /
`list_issues` / `drop_suggestion`。全部走 `fcop.Project` 接口，薄壳
只做输入解析 + 异常映射 + 文本格式化。

### D7-c：团队/部署/工作区 tool（commit `4071b3f`）

5 个 tool：`get_available_teams`、`get_team_status`、
`deploy_role_templates`、`new_workspace`、`list_workspaces`。
workspace 是 UX 层的软约定（`workspace/<slug>/` + 元数据 JSON），
没进 `fcop` 库 core，保持库只管协议原语。

### D7-d：meta tool + resources（commit `704b336`）

- `unbound_report(lang)`：FCoP v1.1 Rule 0 自救报告
- `check_update(lang)`：查 PyPI，**只读**
- `upgrade_fcop(lang)`：按 uvx / pipx / pip 返回升级命令，**绝不自己 pip install**
- 10 个 `fcop://` resource（7 静态 + 3 模板）：
  `status`, `config`, `rules`, `protocol`, `letter/{zh,en}`,
  `teams`, `teams/{team}`, `teams/{team}/{role}`,
  `teams/{team}/{role}/en`

### D7-e：合同测试 + CI workflow（commit `e2f368a`，本次）

这是兑现 ADR-0003 commitment #2 的关键一步 —— 之前宪章是「写在纸上」，
这次把它变成 PR 合入前的**硬门槛**。

| 文件 | 作用 |
|---|---|
| `tests/test_fcop_mcp/test_tool_surface.py` | 把 24 tool + 10 resource 的外契约（name/param/required/URI/mime）快照到 JSON，漂移就红 |
| `tests/test_fcop_mcp/snapshots/tool_surface.json` | 锁定基线；更新必须显式 `--snapshot-update` + CHANGELOG |
| `tests/test_fcop_mcp/test_server.py` | 39 个冒烟测试，走 `mcp.call_tool` / `mcp.read_resource`，跟 Cursor 一致 |
| `tests/test_fcop_mcp/conftest.py` | 清 `FCOP_*`/`CODEFLOW_*` 环境变量、重置 session pin、提供初始化好的 tmp project |
| `.github/workflows/test-fcop-mcp.yml` | 3×4 矩阵 + `tool-surface` PR gate + clean-venv 打包冒烟 |
| `.github/workflows/test-fcop.yml`（修改） | 作用域缩到 `tests/test_fcop/`，库 / MCP 红绿独立 |

## 本地验证

```
py -3.10 -m pytest tests -q
486 passed, 1 warning in 16.46s

py -3.10 -m ruff check src tests mcp/src
All checks passed!

py -3.10 -m mypy src/fcop
Success: no issues found in 12 source files

py -3.10 -m mypy --config-file mcp/pyproject.toml mcp/src/fcop_mcp tests/test_fcop_mcp
Success: no issues found in 8 source files
```

测试数字演进：443（D5 close）→ 447（+ 4 tool-surface）→ 486（+ 39 smoke）。

MCP 服务器真实启动验证过，24 tools + 10 resources 全部注册成功。

## 稳定性宪章现在是硬约束

| 想法 | 之前 | 现在 |
|---|---|---|
| 删一个 tool | 理论上禁止 | `test_tool_names_are_a_superset_of_snapshot` 直接红 |
| 把某 tool 的 optional 参数改 required | 理论上禁止 | `test_required_params_are_not_tightened` 直接红 |
| 改 `fcop://status` URI | 理论上禁止 | `test_resource_uris_are_not_removed` 直接红 |
| 加新 tool 不更新 CHANGELOG | 评审时漏掉 | `tool-surface` CI job 在 PR 上红 |
| 删 `Project.xxx()` 方法 | 评审时漏掉 | `test_project_methods_are_a_superset_of_snapshot` 直接红 |

也就是说：**ADR-0003 的 7 条承诺现在有了 5 个自动化哨兵**（库侧 3 + MCP 侧 2 + CI 社会性 1 = 实际比 5 多）。

## 当前状态

- 分支：`feat/0.6-library-split` 已推送到 `joinwell52-AI/FCoP`
- commits：`10426e3..e2f368a` 共 6 个 commit（ADR + D7-a → D7-e）
- 测试：486 passed
- 未消化的 D7 启动回执问题：

  1. **RC 策略**：`0.6.0rc1` 上 TestPyPI？还是直接 `0.6.0` 上 PyPI？
  2. **bridgeflow 处理**：旧 `bridgeflow` 包怎么收尾（deprecated 说明 / 指向 fcop-mcp / 留空包）
  3. **仓库可见性**：`joinwell52-AI/FCoP` 公开时机

这三个问题不答也能往前走，但 RC 策略不答就不能开始发包动作。

## 下一步建议（按 ADMIN 加速指令）

**优先级 A（今天就能做）**：

1. **写 `docs/MIGRATION-0.6.md` 初稿**：用户最关心的「0.5.x → 0.6.x
   怎么迁」—— 哪些命令变了、MCP client 配置怎么改、老代码怎么改。
   没这个用户上不了。
2. **写 `docs/release-process.md`**：双包发版流程（fcop → fcop-mcp
   顺序、TestPyPI rehearsal、发布后验证清单）。没这个我们自己也会
   出错。

**优先级 B（等 ADMIN 拍 RC 策略后）**：

3. 把 fcop `_version.py` 打成 `0.6.0rc1`，上 TestPyPI，跑一遍 CI 的
   `package` job 以外的真实 PyPI 安装路径（`pip install -i
   https://test.pypi.org/simple/ fcop-mcp`）。
4. Cursor / Claude Desktop 实配一次 MCP，录 screenshot 给 README。

**优先级 C（0.6.0 final 前）**：

5. `codeflow-plugin/src/fcop/server.py` 里残留的纯工具函数迁进 `fcop/core/`
   （ADR-0002 §"Migration path"）。
6. 迁移完成后归档 `codeflow-plugin/` 到 `legacy/`。

## 需要 ADMIN 回复

请按优先级选 A 继续（我会直接做），或者先回 B 那三个问题让我能开始
发包动作。不等回复的话我会先做 A 再回头开 B。

——
PM-01（2026-04-23）
