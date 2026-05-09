---
protocol: fcop
version: 1
sender: DEV
recipient: PM
thread_key: fcop_independent_bridgeflow_docs_20260425
priority: P2
status: done
---

# 报告：FCoP 独立与 Bridgeflow 工具线边界（总结）

## 1. 结论

**FCoP**（协议 + PyPI 双包 `fcop` / `fcop-mcp`）与 **GitHub 独立仓**已作为唯一权威；**Bridgeflow 本仓**在文档中已明确定位为「CodeFlow 工具项目」，与 FCoP 源码与发版**分家**，避免把同一工作树当作两套主工程来用。

---

## 2. 背景与目标

- 此前 FCoP 相关实现与 CodeFlow/Bridgeflow 业务代码同仓混放，易与「工具产品」边界混淆。
- 目标：在**本机**有独立 FCoP 工作区、**GitHub** 有独立 FCoP 仓的前提下，在 **Bridgeflow 文档**中写清分工，并保留可追溯的说明入口。

---

## 3. 已落地事项

### 3.1 独立工作区 `D:\FCoP`（与 GitHub 对齐）

| 项 | 说明 |
|----|------|
| 来源 | 自 `D:\Bridgeflow\private\fcop-repo` 全量同步（与 [joinwell52-AI/FCoP](https://github.com/joinwell52-AI/FCoP) 同构，含 `.git`） |
| `fcop-mcp` 源码 | 自 `D:\Bridgeflow\fcop-mcp\fcop_mcp\` 覆盖到 FCoP 仓内 **`mcp\src\fcop_mcp\`** 规范布局，与 `fcop-mcp` 0.6.x 开发线对齐 |
| 验证 | 本机 `pip install -e .` + `pip install -e mcp` 可导入；`pytest` 全量 **491 passed**（执行时测） |
| 说明文件 | FCoP 侧：`D:\FCoP\docs\worktree-本机-Bridgeflow-同步说明.md` |

### 3.2 Bridgeflow 仓库内文档（本报告所在仓）

| 文件 | 作用 |
|------|------|
| [README.zh.md](../../../README.zh.md) | 首屏后增加 **「本仓与 FCoP 的关系」** 对比表；文末「协议与田野报告」改为指向独立仓，避免旧表述 |
| [README.en.md](../../../README.en.md) | 增加 **This repo vs FCoP** 英文明示 |
| [README.md](../../../README.md) | 增加 **Scope：FCoP vs 本工具仓** 与链接 |
| [docs/integrations/fcop-standalone-zh.md](../../integrations/fcop-standalone-zh.md) | 分工、双包、发版对照表、小结（中文主说明页） |
| [docs/release-process.md](../../release-process.md) | 文首 **适用范围**：仅 CodeFlow 工具发版；**不含** FCoP PyPI 发版，并指回 FCoP 仓与上页 |

---

## 4. 当前边界（写死，防再混）

| 维度 | FCoP | Bridgeflow / CodeFlow（本仓） |
|------|------|------------------------------|
| **Git 主仓** | [joinwell52-AI/FCoP](https://github.com/joinwell52-AI/FCoP) | 本工作区（与 codeflow-pwa 等工具线） |
| **交付物** | 协议规范、随笔、`fcop` 与 `fcop-mcp` | Desktop、PWA、中继、产品联调等 |
| **发版** | 见 FCoP 仓内 `docs/release-process.md` | 见本仓 [docs/release-process.md](../../release-process.md)（仅工具线） |
| **本机开发根** | 以 `D:\FCoP` 为权威（或 clone FCoP 到任意盘） | 以本仓业务目录为准 |

**未强制删除**本仓内历史目录 `codeflow-plugin/`、`fcop-mcp/`：避免一次性破坏现有脚本与贡献者习惯；**新规范与新包**以 FCoP 仓与 `D:\FCoP` 为准。后续若要把重复目录收束为子模块 / 仅 PyPI 依赖，可单独立项。

---

## 5. 建议后续（非阻塞）

1. 若需 **单一源码真相**：评估将 `codeflow-plugin` 从本仓移出或改为 `git submodule` 指向 FCoP，并更新 `CONTRIBUTING.md` 与 CI。  
2. 在 **CHANGELOG** 或某次发版说明中可一笔带过「文档已明确 FCoP 分仓」，便于对外读者。  
3. 贡献者新手指南中增加 **fcop-standalone-zh** 的链接（若 `CONTRIBUTING.md` 尚未链到）。

---

## 6. 关键路径索引（本仓）

- 分工长文（中文）：[docs/integrations/fcop-standalone-zh.md](../../integrations/fcop-standalone-zh.md)  
- CodeFlow Desktop 发版（**不含** FCoP 双包）：[docs/release-process.md](../../release-process.md)  
- 入口 README：[README.md](../../../README.md) · [README.zh.md](../../../README.zh.md) · [README.en.md](../../../README.en.md)  

**FCoP 仓**（非本树）：<https://github.com/joinwell52-AI/FCoP>  

---

*本报告为 Bridgeflow 工作区内对「FCoP 独立 + 本仓工具线」的阶段性总结，便于 PM/OPS/新成员对齐认知。*
