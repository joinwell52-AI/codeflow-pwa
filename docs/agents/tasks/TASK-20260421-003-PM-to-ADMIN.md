---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: publish_codeflow_mcp_pypi_20260421
priority: P1
created_at: 2026-04-21T21:25:00+08:00
---

# 接单：`codeflow-mcp` 0.2.0 发布到 PyPI

## 接单确认

- **是否接单**：是
- **线程键**：`publish_codeflow_mcp_pypi_20260421`
- **执行者**：PM（本会话），将 DEV/OPS 角色在单一会话内串行执行（ADMIN 已授权）
- **预计窗口**：本次会话内完成 DEV 产物（打包 + 自测）；OPS 的 `twine upload`
  等 ADMIN 最终放行后再执行。

## 拆解计划

### DEV 子任务 → `TASK-20260421-003-PM-to-DEV.md`

- 新增 `codeflow-plugin/pyproject.toml`（hatchling 后端，项目元数据 + 入口 + 打包数据）。
- 把 `codeflow-plugin/scripts/mcp_server.py` 的实际代码迁到
  `codeflow-plugin/src/codeflow_mcp/server.py`，并加 `__init__.py` / `__main__.py`。
- 添加 `def main()` 入口，`[project.scripts]` 声明 `codeflow-mcp = "codeflow_mcp.server:main"`。
- 把 `codeflow-plugin/rules/codeflow-core.mdc` 同步到
  `src/codeflow_mcp/_data/codeflow-core.mdc`（package data），
  并用 `importlib.resources` 在运行时读取；`_core_mdc_hash()` 的候选路径增加 resource 回退。
- 把 `init_project` 扩展为：创建项目后若项目 `.cursor/rules/codeflow-core.mdc`
  不存在，则从 package data 解包过去。
- 在 `codeflow-plugin/scripts/mcp_server.py` 留向后兼容 shim，只做 `sys.path`
  注入 + `from codeflow_mcp.server import main; main()`，保证 ADMIN 现有 `mcp.json`
  不用改也能继续跑。
- 本地 `py -3.10 -m build` 出包 + `pip install -e codeflow-plugin` 自测通过。
- 回执 `TASK-20260421-003-DEV-to-PM.md`，列影响范围 / 自测日志 / 文件清单。

### OPS 子任务（ADMIN 放行后执行）

- `py -3.10 -m pip install --upgrade build twine`（如未装）
- `py -3.10 -m build`（确认产物）
- `py -3.10 -m twine check dist/*`
- `py -3.10 -m twine upload dist/*`（自动读 `%USERPROFILE%\.pypirc`）
- 从另一个干净 venv 验证 `uvx codeflow-mcp`（或 `pip install codeflow-mcp` + `codeflow-mcp`）
  能启动、`unbound_report` 可调。
- 回执 `TASK-20260421-003-OPS-to-PM.md`，附 `twine upload` 输出 + `pip show codeflow-mcp` 输出。

### DEV 收尾（OPS 完成后）

- 改 `codeflow-plugin/README.md`：把"安装"一节重写成 **uvx / pip / deeplink** 三条路径。
- 生成 Cursor Deeplink URL 并贴一张 "Add to Cursor" 按钮。
- 回执 `TASK-20260421-003-DEV-to-PM.md`（v2，追加在同一线程）。

## 风险 & 缓解

| 风险 | 缓解 |
|---|---|
| 迁移后现有 `mcp.json` 指向旧路径会崩 | 保留 `scripts/mcp_server.py` shim，保持绝对路径不变 |
| `codeflow-core.mdc` 在 wheel 里找不到 | `importlib.resources.files("codeflow_mcp") / "_data" / "codeflow-core.mdc"` 三段式回退 |
| PyPI 版本号一旦上传无法撤回 | 先本地 `twine check` + `wheel unpack` 核对后再上传；必要时先推 TestPyPI |
| token 泄漏 | 已落位 `%USERPROFILE%\.pypirc`，不进仓库，不进 commit 消息；发布后建议 revoke 重建 |

## 本单对 ADMIN 的请求

- DEV 产物完成后会立刻写 `DEV-to-PM` 回执；
- OPS 的 `twine upload` 属于**首发、公开、不可撤回**操作，**等你一声"发"**才动手。

— PM
