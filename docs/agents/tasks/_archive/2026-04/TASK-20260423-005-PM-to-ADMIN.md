---
protocol: fcop
version: 1
kind: task
task_id: TASK-20260423-005
sender: PM
recipient: ADMIN
priority: P2
thread_key: fcop-0.6.0rc1
references:
  - TASK-20260423-003-PM-to-ADMIN
  - TASK-20260423-004-PM-to-ADMIN
  - ISSUE-20260422-001
---

# 0.6.0rc1 文档批次完工 + 合规审计结论，等 ADMIN 验收后拍 RC

## 背景

ADMIN 决议（四拍）：

1. RC 时机：**B** —— 等文档齐再拍 rc1
2. ADR-0004（时间由文件系统提供）：**立刻落地**
3. 0.5.x 老文件处理：**Grandfather 条款**（只读不改）
4. 合规审计优先级：**RC 前必须产出**

本轮按该计划全部完成。下面是交付清单 + 审计结论 + 剩余拍板项。

---

## 一、合规审计结论（扫 `docs/agents/tasks/` 共 27 份文件）

| 分类 | 数量 | 说明 |
|---|---|---|
| **完全合规**（0.6 标准）| **1** | 只有 `REPORT-20260421-003-PM-to-ADMIN.md`（带软警告）|
| **文件名违规** | 0 | 0.5.x 的文件名语法和 0.6 完全兼容，无一例外 |
| **frontmatter 违规** | 26 | 大多数是缺 `kind:` 字段（0.5.x 根本不写）|
| **"软警告"**`created_at` 存在 | 11 | 含 PM 本尊最近 4 份报告 |

### 主要违规模式

| 违规类型 | 样本数 | 示例 |
|---|---|---|
| 缺 `kind:` 字段 | 26 | 所有 0.5 文件 |
| `protocol: agent_bridge`（老协议名）| 4 | `TASK-20260420-001-*` 系列 |
| `protocol: FCoP` 大小写错 | 2 | `TASK-20260423-003/004`（我自己写错）|
| 版本号非规范 `"1.0"` / `1.1` / `1.4.0` | 4 | 散见 |
| sender/recipient 与文件名不一致（`PM` vs `PM-01`）| 3 | 最近几份 PM-to-ADMIN |

### 结论

Grandfather 条款**完全吃得下**——0.6 工具（`read_task`/`list_tasks`/`inspect_task`）对所有 27 个文件都能正常处理，只是 `inspect_task` 会 WARN。**不需要动任何老文件**，也不需要开一次性迁移 commit。

审计产物：

- `_ignore/audit_legacy_fcop.py` — 一次性审计脚本
- `_ignore/audit_legacy_fcop.json` — 机读格式审计结果（供未来 `Project.audit_legacy()` 参考）

---

## 二、本轮交付清单

### 2.1 ADR

| 文件 | 状态 | 说明 |
|---|---|---|
| `adr/ADR-0004-time-is-filesystem.md` | **Accepted** | 新增，确立"时间由文件系统提供"原则 |
| `adr/README.md` | updated | 索引表加 0003/0004 两行 |

### 2.2 代码改动（additive，非破坏性）

| 位置 | 改动 | 测试 |
|---|---|---|
| `src/fcop/project.py` / `write_issue` | 写入 `status: open` + `created_at` | 17 个 issue 测试全绿 |
| `src/fcop/project.py` / `_assemble_issue_file` | canonical 字段顺序包含 `status` / `created_at` / `closed_*` / `resolution`（`closed_*` 是 0.6.1 预留位）| - |

### 2.3 文档

| 文件 | 性质 | 篇幅 |
|---|---|---|
| `docs/MIGRATION-0.6.md` | 新增 | 面向终端用户，3 步迁移流程 + 6 条 FAQ |
| `docs/release-process.md` | 新增 | 面向维护者，双包发布 checklist + 分阶段流程 |
| `CHANGELOG.md` | 更新 | `[Unreleased]` 加 ADR-0004 条目 + `write_issue` 变化 |

### 2.4 质量门

- `fcop` 库测试：**443/443 绿**
- `fcop-mcp` 测试：**43/43 绿**
- Public API snapshot：**未变**（确认无 breaking）
- Tool contract snapshot：**未变**
- `ruff` / `mypy`：**All checks passed**

---

## 三、0.6.0rc1 范围收窄说明

ADR-0004 原本想把 Issue 状态机（`close_issue` / `reopen_issue` / `Issue.status` 字段等）全部打包进 RC1。审查后发现会带来：

- 新的 public 方法签名（`close_issue(...)`）
- `Issue` dataclass 新字段（`status` / `closed_at` / `closed_by` / `resolution`）
- 新的 inspect 规则（closed 状态时字段必填）

这些会**首次触碰 ADR-0003 稳定性宪章的"只进不出"承诺**——一旦 RC1 冻结，这些名字和字段就锁死了。

**决定**：RC1 只落地 `write_issue` 加 `created_at` / `status: open`（最小侵入），完整状态机放 **0.6.1**。这样：

- RC1 把「时间语义原则」锁死，核心哲学层面到位
- 0.6.1 再细化"状态机"实现，API 名字留出设计空间

ADR-0004 §Implementation Timeline 里写清楚了这个二阶段节奏。

---

## 四、剩余等 ADMIN 拍板项

### 4.1 RC 执行

文档和代码已齐。现在差 ADMIN 一声令下就可以：

1. 版本号 bump：`_version.py` 改 `"0.6.0.dev0"` → `"0.6.0rc1"`（两个包同步）
2. CHANGELOG：`[Unreleased]` → `[0.6.0rc1] - 2026-04-23`
3. 本地 build + 干净 venv 冒烟
4. 打 tag `v0.6.0rc1`
5. （可选）上传 TestPyPI 验证
6. （可选）上传 PyPI 真发

等 ADMIN 回执「同意 RC」或「先不发」。**上传 PyPI 是单向操作**（版本号永久占坑），所以需要你显式点头。

### 4.2 `plugin_utils_migration`（低优先）

从 `codeflow-plugin/src/fcop/server.py` 迁移剩余纯工具函数到 `fcop/core/`。这是长尾技术债，不阻塞 RC1。建议 0.6.1 随手做。

### 4.3 自测建议（你可选可不选）

如果你想在 RC1 前再自测一次「用 `fcop-mcp` 写一条新 task 看看长什么样」，步骤：

```powershell
cd D:\Bridgeflow\private\fcop-repo
py -3.10 -m venv .venv-rc
.\.venv-rc\Scripts\activate
pip install -e . -e .\mcp
# 设置 FCOP_PROJECT_DIR 指向你想测试的目录
$env:FCOP_PROJECT_DIR = "D:\path\to\test\project"
fcop-mcp --help
```

---

## 五、触发动作请求

请 ADMIN 在下一份 `TASK-*-ADMIN-to-PM.md` 里明示以下任一：

- [ ] **同意 RC**：我立刻 bump 版本号 → build → TestPyPI → 等你再点头才真发 PyPI
- [ ] **先复核**：指出 MIGRATION / release-process / ADR-0004 任一文档需要改的地方
- [ ] **先合 main**：先 git commit + push，RC 后面再说
- [ ] **其它**：写出你想让我做的下一步

无其它指令的话，我就停在这里等你。**代码本地可运行、测试全绿**，这是最后一次"发布前安全窗口"。

— PM
