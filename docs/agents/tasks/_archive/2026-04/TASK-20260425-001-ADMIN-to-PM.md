---
protocol: fcop
version: 1
sender: ADMIN
recipient: PM
thread_key: fcop_mcp_fcop_protocol_compliance_20260425
priority: P1
---

# 任务：把「MCP/发版/版本号」工作收回 FCoP 轨道，并记档本次偏差

## 背景

近一次会话中，**编码助手在聊天里**完成 `fcop` / `fcop-mcp` 相关操作（本机
`mcp.json`、PyPI 上传意向、说明文档多次改动等），**未**通过 FCoP
要求的「派单/回执落 `docs/agents/tasks/`、经 **PM-01** 调度」流程。

另有偏差：在**无团队确认的一版发版**前提下，**擅自**为文档小改连续使用
`0.6.3` / `0.6.4` 等补丁号。此类号码**非**当时 PyPI 与仓库既定发版线，
属于「聊天里自造版本串联」，**不应再发生**。

> **FCoP 北星原则**：多角色/阶段结论**必须落成文件**；不只在脑子里或只在对
> 话里完成「就算交付」。

## 本任务要求 PM 落实的事项

1. **制度层（可写进团队约定或给 AI 的固定指令）**  
   - 凡涉及 **PyPI 发版、版本号、`fcop`/`fcop-mcp` 安装文档、本机全局
     `mcp.json`** 的变更：  
     **先** 用 `TASK-*-PM-to-DEV` / `TASK-*-PM-to-OPS`（或等价）**落文件**、
     **再** 执行；**禁止**在单一聊天线程里无任务号「顺手发版/顺手改号」。

2. **版本号**  
   - 补丁/次版本号**只**对应当前真实要发布的一包（经 build + 约定检查），
   **不**为「多改几段 README」人为连号。当前仓库对 `fcop-mcp` 的整理以
   **`0.6.2` 一版打齐**说明为准；历史已澄清的 0.6.3/0.6.4 叙述**以仓库
   CHANGELOG 与 `pyproject` 为准，不再在对话里加号**。

3. **回执**  
   - PM 阅毕本任务后，向 ADMIN 发 **`TASK-*-PM-to-ADMIN.md`**：是否采纳以上
   约束、对 DEV/OPS 的后续派发计划（如需要一条「发版前检查表」可一并写清）。

## 本文件性质

由助手按 `TASK-*-ADMIN-to-PM` 形式**代记** ADMIN 上述意图，便于
**单键线索**进 `thread_key: fcop_mcp_fcop_protocol_compliance_20260425`，
不替代 ADMIN 在需要时**亲自**再发一条的权限。

## 附：与代码状态对齐（供 PM 扫一眼）

- `fcop-mcp` 在仓库内版本号以 **`0.6.2`** 与 `CHANGELOG` 中「0.6.1 后一揽子
  文档/安装/sh 修正」条目一致。  
- `codeflow-plugin/scripts/install-fcop.sh` 中 `mcp` 的 `args` 应为
  **`fcop-mcp`**，与 0.6 迁移后一致。

---
**代记说明**：本任务正文由当次会话中的编码助手依 ADMIN 口授意图整理，格式对齐
`docs/agents/tasks/TASK-20260421-001-ADMIN-to-PM.md` 等现有范例。
