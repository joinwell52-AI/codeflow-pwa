---
protocol: fcop
version: 1
sender: ADMIN
recipient: PM
thread_key: publish_codeflow_mcp_pypi_20260421
priority: P1
created_at: 2026-04-21T21:24:06+08:00
---

# 把 `codeflow-mcp` 0.2.0 发布到 PyPI，让 ADMIN 在任何一台电脑上都能一行装完

## 背景

本会话先后完成：

- **协议硬化**：FCoP v1.1（根公理 + 8 条款，`unbound_report` 保险丝扳手）。
- **工具箱清理**：删除已弃用的 `codeflow_mcp.py`（pyautogui 面板 MCP）。
- **Git 升级**：`2.30.0 → 2.54.0`，修复 `--trailer` 兼容问题。

接下来的痛点是 **安装体验**：目前新电脑想用 `codeflow`，需要——

1. `git clone` 整个仓库
2. 手写 `C:\Users\...\.cursor\mcp.json` 指向本地 `mcp_server.py` 绝对路径
3. `pip install fastmcp websockets`
4. 重启 Cursor

这一串对非开发者用户是劝退级别的障碍。ADMIN 要求把它收敛成
**`uvx codeflow-mcp`** 一条命令。

## 决策（本单已拍板，不再改）

- **PyPI 包名：`codeflow-mcp`**（纯净的 `codeflow` 已被他人占用 0.0.3）
- **首版版本号：`0.2.0`**（含 `unbound_report`，对外宣告 FCoP v1.1）
- **PyPI 账号**：已由 ADMIN 在 `%USERPROFILE%\.pypirc` 配置好 API token
  （`__token__` 方式，仓库外，不进 git）。

## 预期交付（三条安装路径）

用户侧最终可以走以下任一条：

1. **`uvx codeflow-mcp`**（推荐 · 零污染全局）—— `uv` 拉临时虚拟环境，跑完即走。
2. **`pip install codeflow-mcp`** + `codeflow-mcp`（传统 · Python 用户熟）
3. **Cursor Deeplink 按钮**（README 里贴一张 `cursor://anysphere.cursor-deeplink/mcp/install?...`
   的图标链接，点击即写 `mcp.json`）

三条都指向**同一个 PyPI 包**，体验统一。

## 约束

- **不破坏现有开发环境**：ADMIN 当前 `~\.cursor\mcp.json` 直接指向
  `D:\Bridgeflow\codeflow-plugin\scripts\mcp_server.py`，重构后这条路径必须仍能启动
  （用 shim 或保留旧入口）。
- **不升级 `fastmcp`/`websockets` 大版本**，沿用现有 `requirements.txt`
  里 `fastmcp>=3.2.0` / `websockets>=12.0`。
- **`codeflow-core.mdc` 必须打包进 wheel**——新电脑 `init_project` 时能把这份
  规则文件铺到 `.cursor/rules/`，不能让用户再手动 `git clone`。
- **token 不得写入仓库 / 不得 echo / 不得出现在 commit message**。

## 验收

- 本地 `py -3.10 -m build` 出 `codeflow_mcp-0.2.0-py3-none-any.whl` 与 `.tar.gz`。
- `uvx --from ./dist/codeflow_mcp-0.2.0-py3-none-any.whl codeflow-mcp` 能启起来。
- 从源码装：`pip install -e codeflow-plugin` 不报错，可 `python -m codeflow_mcp`。
- 发布到 PyPI 后：`uvx codeflow-mcp` 在**另一台干净机器**能启动（至少主观验证
  启动日志正常；DEV 本机可以用干净 venv 模拟）。

## 派单给 PM

按 FCoP 规则拆成 DEV / OPS 子任务：

- DEV：包结构改造 + `pyproject.toml` + `main()` 入口 + shim + 数据文件打包。
- OPS：`twine upload` 发布（ADMIN 单独放行后执行，不跟 DEV 合并到一步）。
- 发布后 DEV 再改一次 README 写三条安装说明。

回执请求：

`TASK-20260421-003-PM-to-ADMIN.md` 里说明接单时间和预计完成窗口。

— ADMIN
