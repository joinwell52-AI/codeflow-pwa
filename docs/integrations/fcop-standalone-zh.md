# FCoP 与 Bridgeflow（CodeFlow）的分工

> **写死边界**：分仓以后，**协议 + MCP = FCoP**；**手机驭 AI 工具 = 本仓（工具项目）**。两边不再混成「一个工作树里两套主工程」。

## FCoP 是什么（完全独立）

- **仓库**：[github.com/joinwell52-AI/FCoP](https://github.com/joinwell52-AI/FCoP)（独立 Git、独立发版、独立 Issue/PR）
- **内容**：
  - **协议**：文件驱动协作的规范、论文、规范性格式（如 `.mdc`、团队模板等）
  - **MCP 与双包**：
    - **`fcop`**：协议与 Python 库（`Project` / 任务与公文等 API）
    - **`fcop-mcp`**：把上述能力暴露给 Cursor / 其他 MCP 客户端
- **本机开发**：若你盘上有独立工作区（例如 `D:\FCoP`），**以 FCoP 仓为唯一权威**，与 Bridgeflow 是否还带有历史目录无关。

## Bridgeflow / CodeFlow 本仓是什么

- **定位**：**工具项目** —— CodeFlow Desktop、PWA、中继联调、产品文档与发版等，**面向「能跑、能下、能连」的交付**。
- **与 FCoP 的关系**：
  - 消费协议：在业务项目里**安装** `fcop` / `fcop-mcp`（或参考文档把规则抄进 `.cursor`），不替代 FCoP 仓的演进主线。
  - 本仓内如仍有 `codeflow-plugin/` 等历史路径，仅作**兼容/迁移期**引用；**新规范、新包版本、MCP 行为**一律以 **FCoP 仓** 为准。

## 文档与发版往哪看

| 想做的事 | 去哪 |
|----------|------|
| 改协议、改 `fcop` / `fcop-mcp`、发 PyPI、开协议相关 issue | **FCoP 仓**（及仓内 `docs/`，如 `docs/release-process.md`） |
| 发 CodeFlow Desktop / PWA、本工具链 | **本仓** [docs/release-process.md](../release-process.md)（**仅**工具线，不覆盖 FCoP 双包） |

## 小结

- **FCoP = 协议 + `fcop` + `fcop-mcp`**，**独立**。
- **Bridgeflow = 工具项目**，**独立**。
- 分开后，按上表和 README 里「本仓与 FCoP 的关系」对照，**不应再乱**。

---

## 本仓 contributor 如何在自己机器上接 fcop-mcp

> ⚠️ 本节面向 **本仓 contributor**（写码流代码的人），不是面向终端用户。终端用户的安装指引应该读 [FCoP 上游仓 README](https://github.com/joinwell52-AI/FCoP)，而不是本节。
>
> ⚠️ 按 [设计文档 §8.0 硬规则 #5](../design/codeflow-v2-on-fcop-sdk.md)（"本仓 = 应用方，不是定义方"），本仓**不再 ship** 任何 fcop 安装/分发素材（5/9 已物理删除 `fcop-mcp/` + `codeflow-plugin/mcp.json` + `install-fcop.{ps1,sh}` 等 9 项，详见 §8.6 退役账本）。本节只告诉你**到哪里去**配，不在本仓内重复定义。

### 推荐路径（PyPI 装到你自己用户级）

1. **装 fcop-mcp** ——按 [FCoP 上游仓 README](https://github.com/joinwell52-AI/FCoP#readme) 的安装章节（一般是 `pip install fcop-mcp` 或 `uvx fcop-mcp`，请以上游 README 为准，本仓不复述版本号）。
2. **挂到你自己的 Cursor** ——编辑你**用户级**的 `~/.cursor/mcp.json`（不是本仓内的任何文件），按上游 README 给的样例加一段 `fcop-mcp` server 配置。
3. **重启 Cursor** ——让 MCP servers 列表刷新。
4. **验证** ——在 Cursor 里打开任意聊天，输入 `/mcp` 或在底部状态栏查看 MCP servers，应能看到 `fcop-mcp` 在线。

### 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| Cursor 找不到 fcop-mcp | `~/.cursor/mcp.json` 没配，或 Cursor 没重启 | 按"推荐路径"重做一遍 |
| 你以前依赖本仓 `codeflow-plugin/mcp.json` | 该文件 5/9 已删（硬规则 #5） | 把对它的引用从你本地配置中删掉，改用上游 PyPI 安装的 fcop-mcp |
| 想"在本仓内"配 fcop-mcp 给所有 contributor 用 | ⛔ 不允许 | 本仓不再 ship 配置素材；每个 contributor 在自己用户级配 |

### 这样设计的理由

- **隔离 contributor 的本地选择**：不同 contributor 可能用不同 fcop-mcp 版本（PyPI 稳定版 / D:\FCoP 本地开发版），本仓不强加版本
- **避免再次违反硬规则 #5**：任何"本仓内的 mcp.json 模板"都是潜在违规
- **跟 D:\FCoP 升级解耦**：上游发新版 → contributor 各自 `pip install -U` → 本仓零改动

### 如何在 IDE/编辑器外验证 fcop-mcp 真的能用？

完全独立于 Cursor，可以走 `fcop-mcp --help` 或 `python -m fcop_mcp --help`（具体命令以上游 README 为准）。如果命令能调起来，说明 PyPI 装好了。然后再回到 Cursor 挂上。

> 💡 设计文档 §8.6 backlog 里有一项「`docs/integrations/fcop-standalone-zh.md` 措辞按 v2 身份重写」(P1, v0.2 sprint)，本节是 v2 身份下的*第一刀小修*，全文重写留给 v0.2。
