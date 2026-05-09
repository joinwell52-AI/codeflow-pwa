---
protocol: fcop
version: 1
kind: task
task_id: TASK-20260423-007
sender: PM
recipient: ADMIN
priority: P1
thread_key: fcop-0.6.0-postrelease
references:
  - TASK-20260423-006-PM-to-ADMIN
---

# 0.6.0 一条龙文档已补齐 + 老用户破坏面已定方案，等 ADMIN 拍 0.6.1 发版

## 背景

ADMIN 上一条指令：

> "你先完善文档，把这个 fcop 的发版本记录下来，fcop 一条龙；对了，现在的 fcop 怎么办？mcp 改 fcop-mcp 了；"

两个问题：
1. 0.6.0 的一条龙发版档案
2. 0.5.x 老用户 `uvx fcop` / `pip install fcop` 在升级后会 **command not found** —— 要不要管、怎么管

两个都已处理。

---

## 第一件：一条龙发版档案

### 新文件

**`docs/releases/0.6.0.md`**（fcop-repo，约 190 行）—— 本次 0.6.0 的完整档案，分 8 章：

| 章 | 内容 |
|---|---|
| 1 | 一句话结论 |
| 2 | Shipping scope（包结构 / 公共 API surface / MCP tool 合同 / 协议决议 / 代码改动 / 文档改动）|
| 3 | 质量 gate 结果（8 项全绿，含跨平台 CI）|
| 4 | 发布执行步骤（本地路径 = 本次实际用的；自动化路径 = 0.6.1 起启用）|
| 5 | 发布后观测（PyPI 验证 + **下游已知破坏点 6 行表** + 0.6.1 修正计划）|
| 6 | 后续 roadmap（6 项，带目标版本）|
| 7 | 鸣谢 / 决策链（引用 ADMIN 原话 + ADR 索引）|
| 8 | 本文的归宿（按 ADR-0005 的定位说明）|

第 5 章是最关键的——把 0.5.4 → 0.6.0 升级后 6 种场景（`pip install fcop` / `uvx fcop` / MCP 配置 / `from fcop.server import` / 老 task 文件 / MCP tool 调用）的实际变化一张表列清，其中 3 处是 ⚠️ 破坏，3 处是 ✅ 兼容。

### README 同步

两份 README（`README.md` / `README.zh.md`）各加了一节 **"Python SDK & MCP server (optional)"**，插在 30-second quickstart 之后、Design principles 之前：

- 双包对比表（装哪个、做什么、依赖啥）
- 库用法（`from fcop import Project`）
- MCP 服务器 `mcp.json` 配置
- ADR-0003 稳定性承诺链接
- **显眼的 0.5.x → 0.6 升级提示框**，指向 MIGRATION-0.6.md 和 releases/0.6.0.md

原 "Reference implementation" 章节也同步改成 "Reference implementations"（复数），明确列出 `fcop` / `fcop-mcp` 和 CodeFlow Desktop 两套官方实现。

---

## 第二件：老 `fcop` 用户破坏面

### 现状诊断

PyPI 历史：`fcop 0.4.7` → `0.5.4`（MCP 服务器）→ `0.6.0`（纯库）。

**0.6.0 的 `fcop` 包没有任何 `[project.scripts]`**。意味着：

| 用户行为 | 0.5.4 时 | 0.6.0 升级后 |
|---|---|---|
| `pip install --upgrade fcop && fcop` | MCP 服务器启动 | **command not found**（静默无提示） |
| `uvx fcop` | MCP 服务器启动 | **fresh uvx 缓存下直接报错**（旧缓存可能短期苟延残喘） |
| Cursor/Claude MCP 配置 `{"command":"uvx","args":["fcop"]}` | 能连 | 连接失败 |

对 0.5.x 用户来说这是一个没有过渡带的硬断点。

### 方案

**0.6.1 compat shim**（已实现，未发版）：

- `src/fcop/_compat_cli.py`（70 行）—— 一个 CLI 入口，**不启动服务器**，而是往 stderr 打印清晰的迁移指引并 `exit(1)`：

  ```
  fcop 0.6+ is a pure Python library. The MCP server moved to a separate
  package called fcop-mcp.

  To get the MCP server back, run one of:

      pip install fcop-mcp          # then: fcop-mcp
      uvx fcop-mcp                  # or zero-install via uv

  Cursor / Claude Desktop MCP config (update your old entry):

      "fcop": {
        "command": "uvx",
        "args": ["fcop-mcp"]
      }

  Migration guide:
      https://github.com/joinwell52-AI/FCoP/blob/main/docs/MIGRATION-0.6.md
  ```

- `pyproject.toml` 加 `[project.scripts] fcop = "fcop._compat_cli:main"`。
- `tests/test_fcop/test_compat_cli.py`（5 用例）—— 冻结合同：退出码 = 1 / 输出到 stderr / 含 "fcop-mcp" 关键词 / pip + uvx 两种用法都提到 / 含迁移指引 URL / console script 实际指向 `_compat_cli.main`。

这是 ADR-0003 允许的 **pure additive** 改动：

- 不动库 API（`Project`、`fcop.models`、`fcop.teams`、`fcop.rules` 都没碰）
- 不动 MCP tool 合同（`fcop-mcp` 根本没改）
- 只是给 `fcop` 包多一条 console script
- `test_public_surface.py` 和 `test_tool_surface.py` 两个 snapshot 均零漂移 ✅

### 本地质量 gate 结果（验收材料）

| Gate | 结果 |
|---|---|
| `pytest tests/test_fcop -q` | ✅ 447 passed, 1 skipped (entry-point 测试需 editable 安装，CI build-install 时会跑) |
| `ruff check src tests` | ✅ All checks passed（顺手修了一条遗留的 `F401`）|
| `mypy src` | ✅ Success: no issues found in 13 source files |
| Snapshot diff | ✅ `tests/test_fcop/snapshots/` 零变化 |

### CHANGELOG 状态

```
[Unreleased]
  ## Added
  - fcop 0.6.1 compat shim ...
[0.6.0] - 2026-04-23
  ...
```

所有改动在 `feat/0.6-library-split` 分支，尚未 commit（留着让 ADMIN 一次性看完整 diff）。

---

## 等 ADMIN 拍板：0.6.1 何时发

三个选项，按激进度排序：

### Option A — 立刻发 0.6.1（推荐）
- 优点：0.5.x 用户只要 `pip install --upgrade fcop` 升级一次后，再运行 `fcop` 就能看到清晰的迁移提示，而不是 "command not found"
- 优点：正好跑通 `.github/workflows/release.yml` 这个自动化发版流程（一箭双雕）
- 成本：一次 tag + push + PyPI 双包发布（自动化，≤5 min）
- 风险：极低——纯 additive，无库 API 变动；snapshot 无漂移

### Option B — 攒几个改动再发 0.6.1（稳妥）
- 把 compat shim + `Project.agent_runtime_dir()`（ADR-0005 helper）+ `close_issue` / `reopen_issue`（ADR-0004 完整实施）打包发
- 优点：发版频次低、信息密度高
- 缺点：0.5.x 老用户的破坏面继续存在数天/数周

### Option C — 不发 0.6.1，靠文档解决
- 理由：`MIGRATION-0.6.md` 已经写得很清楚，用户看到 "command not found" 自会去搜
- 缺点：新手体验差；GitHub / Cursor Forum 上大概率会冒出 "fcop 装不上了" 的 issue
- **不推荐**

---

## 委派计划

待 ADMIN 选 Option 之后：

- **Option A**：我直接 bump 版本到 0.6.1 → commit → tag `v0.6.1` → push → 观察 `release.yml` 运行结果 → PM-to-ADMIN 008 发布完成回执（预计 ≤15 分钟）
- **Option B**：我把 0.6.1 的三个子项各自列成独立 TASK，等下次启动
- **Option C**：我把 compat shim 的改动保留在分支，不合入 main，作为 0.6.1 的"随时可发"储备

Pending tasks（与此决策无关，独立排队）：
- `codeflow-plugin/src/fcop/server.py` 纯工具函数迁移到 `fcop.core`（来自 D 阶段 pending list，不阻塞）

---

## 附录：本次改动的文件清单（一条龙可见）

### fcop-repo（私有子仓，`D:\Bridgeflow\private\fcop-repo`）

```
M  CHANGELOG.md                              # 开 [Unreleased] 节写入 0.6.1 计划
M  README.md                                 # +Python SDK section + reference-impls
M  README.zh.md                              # 同步
M  pyproject.toml                            # +[project.scripts] fcop = ...
M  tests/test_fcop/test_project_suggestions.py  # 清 F401 遗留
?? docs/releases/0.6.0.md                    # 一条龙档案
?? src/fcop/_compat_cli.py                   # 老用户迁移 CLI
?? tests/test_fcop/test_compat_cli.py        # 5 用例冻结 compat 合同
```

### Bridgeflow（主仓，本文件）

```
?? docs/agents/tasks/TASK-20260423-007-PM-to-ADMIN.md    # 本报告
```

所有改动都可以直接 `git diff` 预览，确认无误后再做 0.6.1 决策。

PM-01 待命。
