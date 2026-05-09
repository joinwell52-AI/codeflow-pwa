---
protocol: FCoP
version: 1.1
sender: PM-01
recipient: ADMIN-01
priority: P1
thread_key: fcop-0.6-pre1.0-charter
subject: ADR-0003 稳定性宪章已落地；D7（fcop-mcp）即将启动
references:
  - TASK-20260423-002-PM-to-ADMIN.md
  - adr/ADR-0003-stability-charter.md
---

# 回执：稳定性宪章已落地，进入 D7

## 背景：ADMIN 的两条叠加指令

1. 「先让用户能用起来，加速」
2. 「在 1.0 之前都是打磨，但是系统要开始保持稳定性了」

叠在一起的诉求 = **上架要快，但上架之后不能每周打用户脸**。为此在开工 D7
（`fcop-mcp` 薄壳）之前，先用 **ADR-0003 稳定性宪章** 把合同锁死。

## 已完成（commit `10426e3`，已推送 `feat/0.6-library-split`）

### 1. ADR-0003 Pre-1.0 Stability Charter（Accepted）

见 `adr/ADR-0003-stability-charter.md`。核心条款：

| # | 承诺 | 影响面 |
|---|---|---|
| 1 | 公开 API 面**只进不出** | `fcop.__all__` / `Project` 方法 / dataclass 字段 / `teams` / `rules` |
| 2 | MCP tool 合同锁定 | `fcop-mcp` 的 22 个 tool 名/参数/返回结构 |
| 3 | 破坏性改动走 deprecation cycle | 0.6.N 打 warning → 0.7.0 才删，最短 30 天过渡 |
| 4 | 返回结构向后兼容 | dataclass 加字段允许，删/改名禁止 |
| 5 | CI 强制门槛 | 快照 diff + CHANGELOG 标红 |
| 6 | 发布节奏自律 | 同一 minor 内 patch 必须声明兼容 |
| 7 | 文档同步 | 每次 patch `MIGRATION-0.6.md` 追加一节 |

硬承诺等级：**违反任何一条 → PR 不合入**。

### 2. 快照测试：`test_public_surface.py`

`tests/test_fcop/test_public_surface.py` + `snapshots/public_surface.json`：

- 4 个 test case 锁住顶层 `__all__`、`Project` 的 19 个方法 + 8 个属性、
  9 个 dataclass 的所有字段、`teams` / `rules` 的可导出函数、10 个异常类
- `pytest --snapshot-update` 统一入口更新快照
- 签名任何漂移 → 失败，附带 unified diff 提示
- 删除/重命名走单独的 assertion（错误信息更直接）

### 3. CI 新增 `surface-check` job

`.github/workflows/test-fcop.yml`：

- 仅 PR 触发
- 若 PR 改了 `public_surface.json`，必须在 `CHANGELOG.md` 的 `[Unreleased]`
  节下有 `### Added` / `### Changed` / `### Deprecated` / `### Removed` 中
  至少一个
- 否则 CI 红灯，PR 不能 merge

### 4. CHANGELOG 同步

在 `[Unreleased]` 顶部新加一节 `### Added — project governance`，说明
ADR-0003、快照测试、CI job 三件事都落地。

## 质量

| 指标 | 数值 |
|---|---|
| 测试总数 | 443（+4） |
| ruff | 全绿 |
| mypy --strict | 全绿 |
| coverage | ≥ 90%（和 D5 收尾一致） |
| 新增文件 | 3（ADR-0003、test、快照 JSON） |
| 修改文件 | 3（conftest.py、CI workflow、CHANGELOG） |

## D7 的执行计划

现在正式启动 `fcop-mcp` 薄壳，对标 `codeflow-plugin 0.5.4` 的 22 个 tool
+ 10 个 resource，**完全按原名、原参数、原返回结构**，对外合同不动。

拆成 5 个子任务：

| ID | 内容 | 预计 |
|---|---|---|
| D7-a | `mcp/` 子目录骨架 · `mcp/pyproject.toml` · `src/fcop_mcp/__init__.py` · `__main__.py` · `server.py` 文件壳 | ~30 min |
| D7-b | 核心 tool 薄壳：`init_project` / `init_solo` / `create_custom_team` / `validate_team_config` / `write_task` / `read_task` / `list_tasks` / `inspect_task` / `archive_task` / `drop_suggestion` / `list_reports` / `read_report` / `list_issues` | ~2 h |
| D7-c | 团队 / deploy / workspace tool：`deploy_role_templates` / `get_available_teams` / `new_workspace` / `list_workspaces` / `get_team_status` / `set_project_dir` | ~1 h |
| D7-d | 协议 meta tool：`unbound_report` / `check_update` / `upgrade_fcop` + 10 个 `@mcp.resource` | ~1 h |
| D7-e | `test_fcop_mcp/` 合同测试 · `test_tool_surface.py` 快照 · `.github/workflows/test-fcop-mcp.yml` | ~1.5 h |

每个子任务完成都跑 `pytest + ruff + mypy --strict`，保持 443+ 绿灯。

## 上架目标

- D7 完成后，`fcop 0.6.0rc1` + `fcop-mcp 0.6.0rc1` 同日发 PyPI
- 用户侧升级指令：

  ```json
  // Cursor mcp.json 改一行
  - "args": ["fcop"]
  + "args": ["fcop-mcp"]
  ```

- 不用改任何 prompt、agent 角色定义、task 文件格式
- `MIGRATION-0.6.md` 随发布一起产出

## 待 ADMIN 拍板

1. **rc 策略**：是先发 `0.6.0rc1` 让自己先用一周，还是直接 `0.6.0`
   稳到 PyPI？推荐 rc1 先飞 3–5 天，期间只修 CI / 文档、不动合同；
   3–5 天后无 bug 再发 `0.6.0` final。
2. **`bridgeflow`**：ADR-0002 已决定"不处理"，此处再次确认跳过。
3. **仓库可见性**：`joinwell52-AI/FCoP` 仓库当前是 public 还是 private？
   如果 private，发 PyPI 前需切 public，否则 `pip-audit` / `uvx fcop-mcp`
   的链接跳转会 404。

无阻塞等 ADMIN 反馈，我直接推进 D7-a → D7-b → D7-c → D7-d → D7-e；若
以上三项需要调整再即时停车。

—— PM-01
