---
protocol: fcop
version: 1
kind: task
task_id: TASK-20260425-002
sender: ADMIN
recipient: PM
priority: P1
thread_key: fcop_mcp_fcop_protocol_compliance_20260425
parent: TASK-20260425-001
---

# 发版与协作文档须经 PM 落任务单

## 背景

- 有会话在**未先落** `docs/agents/tasks/` 派单前，在聊天中处理 **PyPI、版本号、用户级 mcp 配置** → 违反 `fcop-rules.mdc` **Rule 0.a、Rule 2**（见该文件；协作指令须落成 `TASK-*`）。
- 使用**未经发布**的版本号串（如 0.6.3/0.6.4 叙事与事实不符）→ 违反 **Rule 0.c**（落到文件里须为真、可引出处）。

## 要求

1. **自此刻起**，凡 **PyPI / 其它公网制品发布、版本号确定**，均先经 **PM 拆解**并落 **`TASK-PM-to-OPS`（或经 PM 同意的等效单）** 再执行。依据 **Rule 7**（`fcop-rules.mdc`）：“发布到公网制品仓库”为破坏性操作，须在任务中声明、有回滚、按任务要求取得 **ADMIN 确认**（若本任务与后续 PM 所立任务已覆盖该确认链，以 PM 写法为准）。
2. 同一类文档/安装类修订，**一版一版本号**由 **PM/任务** 声明，**不**在对话里自造连号。

## 验收

- **PM** 以 **`REPORT-*` 或 `TASK-PM-to-ADMIN`** 回此 `thread_key`：发版/协作文档的**实际流程**与谁执行（**OPS/ DEV** 分工）如何落地。

**依据**：`codeflow-plugin/src/fcop/_data/fcop-rules.mdc`（Rule 0/2/5/6/7）及 `fcop-protocol.mdc` 任务单格式、ADMIN→PM 路由图。
