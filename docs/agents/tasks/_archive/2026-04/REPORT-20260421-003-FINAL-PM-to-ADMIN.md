---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: pypi_publish_fcop_20260421
priority: P1
status: closed
---

# 总回执：`fcop` 0.2.1 已上架 PyPI，交付闭环

## 1. 结论

**任务 `TASK-20260421-003` 全部完成，交付关闭。**

新电脑用 Cursor 现在可以用三种方式装 `fcop` MCP，最短路径 = 一条 deeplink。

## 2. 交付物清单

| 类型 | 产物 | 状态 |
|---|---|---|
| PyPI 包 | [`fcop 0.2.1`](https://pypi.org/project/fcop/) | ✅ 已上架 |
| Console script | `fcop`（`pip install fcop` 后直接可用） | ✅ 已注册 |
| Python 模块 | `python -m codeflow_mcp` | ✅ 可用 |
| 冷启动验证 | `uvx --from fcop python -c "import codeflow_mcp ..."` → `0.2.1 / server module OK` | ✅ 通过（88s 冷启动） |
| 向后兼容 | `codeflow-plugin/scripts/mcp_server.py` shim | ✅ 本仓库开发者 `mcp.json` 无需改 |
| 规则自动释放 | `init_project` 自动把 `codeflow-core.mdc` 展开到 `<project>/.cursor/rules/` | ✅ 已实现 |
| 安装文档 | `codeflow-plugin/README.md` 三路安装章节（uvx / deeplink / pip） | ✅ 已更新 |

## 3. 新电脑 Cursor 安装路径（写给 ADMIN 记在手上）

**推荐 · 方式 A：uvx（零配置、自动升级）**

1. `winget install --id=astral-sh.uv`
2. 编辑 `%USERPROFILE%\.cursor\mcp.json`，加：

   ```json
   {
     "mcpServers": {
       "fcop": {
         "command": "uvx",
         "args": ["fcop"]
       }
     }
   }
   ```

3. 重启 Cursor，第一次调用自动拉包。

**更省事 · 方式 B：Deeplink 一键**

浏览器打开（或让 ADMIN 发给队友）：

```
cursor://anysphere.cursor-deeplink/mcp/install?name=fcop&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmY29wIl19
```

Cursor 弹窗点确认即装好。

**兜底 · 方式 C：pip**

`pip install fcop` → `mcp.json` 里 `"command": "fcop"`。

## 4. 走弯路记录（留档供将来复盘）

| # | 动作 | 教训 |
|---|---|---|
| 1 | 先发了 `codeflow-mcp` 名字被我自己否 | 协议层名字应该和协议对齐 |
| 2 | 然后发了 `fcop-mcp 0.2.0 / 0.2.1` | 没先在 PyPI 搜 `fcop`，带个 `-mcp` 后缀其实没必要 |
| 3 | ADMIN 发现 `fcop` 名字可用，改名 | **正式名：`fcop`，版本从 `0.2.1` 起** |
| 4 | ADMIN 已手动 yank `fcop-mcp 0.2.0 / 0.2.1` | ✅ 污染已清理 |

详细时间线见 `TASK-20260421-003-OPS-to-PM.md`。

## 5. 遗留与建议（非阻塞）

- **小清理**：0.2.2 版本可以消掉冷启动时 FastMCP 的两条 `Component already exists` 告警（server 模块被 import 两次）。
- **建议**：下次发版前把 PyPI API Token 轮换一次（上次在对话里用过裸 token）。
- **后续**：等稳定后再考虑 PyPI Trusted Publishers（OIDC + GitHub Actions），避免再用长期 token。

## 6. 引用

- `TASK-20260421-003-ADMIN-to-PM.md` — 原始发布请求
- `TASK-20260421-003-PM-to-ADMIN.md` — 接单回执
- `TASK-20260421-003-PM-to-DEV.md` — 派发 DEV
- `TASK-20260421-003-DEV-to-PM.md` — DEV 完工回执
- `REPORT-20260421-003-PM-to-ADMIN.md` — 阶段回执（等放行上传）
- `TASK-20260421-003-OPS-to-PM.md` — OPS 发布回执（含走弯路）
- **本文件** — 总回执（交付关闭）

---
**签名**：PM-01  
**日期**：2026-04-21  
**任务状态**：`CLOSED`
