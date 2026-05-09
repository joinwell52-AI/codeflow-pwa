---
protocol: fcop
version: 1
kind: task
task_id: TASK-20260423-006
sender: PM
recipient: ADMIN
priority: P2
thread_key: fcop-0.6.0rc1
references:
  - TASK-20260423-005-PM-to-ADMIN
---

# ADR-0005 Accepted + RC1 就绪，等你一句话

## 背景

本轮 ADMIN 敲下三条协议级决议：

1. **严格派**：0.6 开始严格，0.5.x 老文件**不走"读宽写严"**（方案 C'）
2. **心智模型**：人视角（`ls` / `git` 永远可见）≠ Agent 视角（`list_*` / `read_*` 只认合规文件）
3. **Agent 产出物分层**（起因于 ADMIN 举例 `.runtime-qa-*.json`）：起 ADR-0005 把归宿一次性定死

全部按 Y 方案落地：**只改协议和文档，零代码改动**，不阻塞 RC1。

## 本轮交付清单

### 1. 文档：`MIGRATION-0.6.md` 三处校正

- 新增 **§0 心智模型**：人视角 ≠ Agent 视角，把"0.6 看不见 = 设计、不是 bug"讲清楚
- **§4 Grandfather 条款**由"全部老文件都能读"校正为三档：
  - §4.1 Task（宽容，0.5 老 task 基本都能读 + WARN）
  - §4.2 Report（严格，`reports/TASK-*.md` 这种在 agent 视角下消失）
  - §4.3 Issue（严格，缺 `protocol/version/kind` 或用 `P0-P3` severity 的在 agent 视角下消失）
  - §4.4 心态段 + §4.5 Agent 运行时归宿（对接 ADR-0005）
- **FAQ Q6**："issue 没 created_at 会报错吗？"答案由"不会"改正为"agent 视角看不见，人视角完全保留"
- **TL;DR** 表格补两行提示老 report / 老 issue 的 agent 视角行为

### 2. 新 ADR：ADR-0005 Agent 产出物分层

文件：`adr/ADR-0005-agent-output-layering.md`（Accepted, 2026-04-23, Deciders: ADMIN）

**核心决议**：所有 agent 产出物归入**唯一一档**，新 feature 必须落位：

| 档 | 名称 | 位置 | 入 git? | 跨 agent? |
|---|---|---|---|---|
| A | 瞬时诊断 | 不落盘（MCP 返回值） | — | 调用方 |
| B | 巡检痕迹 | `docs/agents/log/` | ✅ 建议 | ✅ |
| C | 协议级问题 | `docs/agents/issues/`（走 `write_issue`）| ✅ 必须 | ✅ |
| D | Agent 私有运行时 | **`docs/agents/.runtime/{AGENT_CODE}/`**（新）| 🟡 项目自决 | ❌ |
| E | 人的一次性 | `_ignore/` | ❌ | ❌ |

**实施节奏**：

- **0.6.0rc1（本次）**：协议层决议、零代码改动
- **0.6.1**：库端 helper：`Project.agent_runtime_dir(code)` / `list_logs` / `write_log`（additive，符合 ADR-0003）
- **0.7.0**：对应 MCP tool + 锁入 `test_tool_surface.py`

### 3. `adr/README.md` 索引更新

加入 ADR-0004、ADR-0005 两行。

### 4. `CHANGELOG.md [Unreleased]`

追加 ADR-0005 条目，说明"0.6.0 只定协议，0.6.1 才加 helper API"。

## 回归验证

- `pytest tests/` → **486 passed / 0 failed**（0.6 严格立场和 ADR-0004 落地均未打破任何测试）
- `git status`：改动范围 = CHANGELOG + adr/README + docs/MIGRATION-0.6 + 新增 ADR-0005。`src/fcop/project.py` 的改动**仅限 ADR-0004 的 write_issue**（上轮已报）

## 当前状态

0.6.0rc1 所需文档全部齐全：

| 项 | 状态 |
|---|---|
| ADR-0001 Library API | Proposed（不阻塞 RC1）|
| ADR-0002 Package Split | Accepted |
| ADR-0003 Stability Charter | Accepted |
| ADR-0004 Time Is Filesystem | Accepted |
| ADR-0005 Agent Output Layering | Accepted |
| MIGRATION-0.6.md | 完整、校正、含 §0 心智模型 |
| docs/release-process.md | 完整 |
| CHANGELOG.md [Unreleased] | 全部条目已写 |
| public_surface.json / tool_surface.json | 冻结未变 |
| fcop tests / fcop-mcp tests | 486/486 + 43/43 |

## 等你拍板

就一句话的事：

- **"发 rc1"** → 我按 `docs/release-process.md` 流程走：bump version → build → TestPyPI 验证 → PyPI → git tag → GitHub Release
- **"还要改 XXX"** → 列给我，我改完再问

如果没别的，我默认一小时内开干。

---
*PM-01*
