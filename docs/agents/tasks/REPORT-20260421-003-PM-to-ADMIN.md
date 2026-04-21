---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: publish_codeflow_mcp_pypi_20260421
priority: P1
created_at: 2026-04-21T21:36:00+08:00
kind: report
---

# 阶段回执：`codeflow-mcp` 0.2.0 已本地打包完成，等你一声"发"就推 PyPI

## TL;DR

- DEV 活儿干完了，`dist/codeflow_mcp-0.2.0-{whl,tar.gz}` 产出，`twine check` 过。
- `scripts/mcp_server.py` 现在是向后兼容 shim，你 Cursor 里的 `mcp.json`
  **不用动**；但需要在 MCP 面板里 **toggle 一次** 才会加载新代码。
- 剩 2 件事等你拍板，然后 OPS 一键发：
  1. **GitHub 仓库 URL 是否 `https://github.com/joinwell52/bridgeflow`？**
     （`pyproject.toml` 里我先填了这个，不对就改一下再重 build。）
  2. **一句"发"**，我就让 OPS 走 `twine upload dist/*`。

## 完整链路（方便你快速 review）

```
TASK-20260421-003-ADMIN-to-PM.md   ← 你（我代笔归档）
TASK-20260421-003-PM-to-ADMIN.md   ← PM 接单回执
TASK-20260421-003-PM-to-DEV.md     ← PM 派 DEV 活
TASK-20260421-003-DEV-to-PM.md     ← DEV 完工回执（✅ 本次新增）
REPORT-20260421-003-PM-to-ADMIN.md ← 当前这份
```

## 落地清单

| 产物 | 位置 | 状态 |
|---|---|---|
| `pyproject.toml` | `codeflow-plugin/pyproject.toml` | 已创建 |
| Python 包 | `codeflow-plugin/src/codeflow_mcp/` | 已创建 |
| 控制台入口 | `codeflow-mcp`（pip script） | 已生效 |
| 模块入口 | `python -m codeflow_mcp` | 已生效 |
| 包内规则副本 | `codeflow_mcp/_data/codeflow-core.mdc` | 已打进 wheel，三方哈希一致 |
| `init_project` 自动释放规则 | `_deploy_core_mdc_to_project()` | 已接入 |
| 旧路径向后兼容 | `scripts/mcp_server.py`（shim） | 已测试，启动成功 |
| wheel 构建 | `dist/codeflow_mcp-0.2.0-py3-none-any.whl` (31966 B) | 已出 |
| sdist 构建 | `dist/codeflow_mcp-0.2.0.tar.gz` (31817 B) | 已出 |
| `twine check` | 两个产物均 PASSED | ✅ |
| `pip install -e .` | 成功 | ✅ |
| `unbound_report()` 冒烟 | 正常输出 UNBOUND 汇报 | ✅ |

## 对你当前 Cursor 的影响

- 现在**先别 toggle**。等 OPS 发版结束、我报"发布完成"再一起 toggle，
  就能一次切到正式版。
- 即便你现在 toggle 了也不会坏——shim 会把请求转到 editable 安装的新代码，
  行为与旧 `mcp_server.py` 完全一致。

## 已知风险（DEV 回执里列得更细）

- **包名被抢注**：上传瞬间若 `codeflow-mcp` 已被他人占用，B 计划改
  `codeflow-fcop` / `bridgeflow-mcp`。改名成本极低（仅 `pyproject.toml` 两处）。
- **GitHub URL 不准**：见上方第 1 条待确认。
- **FastMCP 双注册 WARNING**：只是日志噪音，不影响功能，后续可优化。

## 我需要你回一句话

只要你回：

> GitHub URL OK（或给我正确的地址）+ 发

我就派 OPS 干活：

```powershell
cd D:\Bridgeflow\codeflow-plugin
py -3.10 -m twine upload dist/*       # 自动读 %USERPROFILE%\.pypirc
```

然后在另一个干净 venv 里验证 `uvx codeflow-mcp` 能启动，出
`TASK-20260421-003-OPS-to-PM.md`。

— PM
