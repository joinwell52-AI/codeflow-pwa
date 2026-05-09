---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260509-007
sender: DEV
recipient: PM
priority: P0
thread_key: pre-s3-housekeeping
references:
  - TASK-20260509-007-PM-to-DEV
layer: worker
---

# Sprint S3 启动前 housekeeping — 完成报告

## 执行摘要

| 项 | 结果 |
|---|---|
| A1 — fcop-standalone-zh.md 加贡献者接入指引片段 | ✅ 完成 |
| B1 — 写 docs/agents/CURRENT-ROLES.md | ✅ 完成（236 行）|
| C1 — git mv 33 文件到 _archive/2026-04/ + TASK-005 加 SUPERSEDED 旗 + 归档 README | ✅ 完成 |
| 10 项验收 | 9/10 命中（第 1 项 grep 命中 1 是预期）|
| ReadLints | 0 错误 |
| 时间消耗 | 约 35 分钟（预算 ≤ 60）|

## 三件改动清单

### A1（1 改动）

`docs/integrations/fcop-standalone-zh.md` 末尾追加 1 节「本仓 contributor 如何在自己机器上接 fcop-mcp」（约 60 行），含：

- 一句话说明本仓不再 ship fcop 安装素材（链到硬规则 #5）
- 推荐路径：上游 README → PyPI 安装 → `~/.cursor/mcp.json` 用户级配置 → 重启 Cursor → 验证
- 故障排查表（3 行）
- 设计理由（隔离 contributor 选择 / 不再违反 #5 / 解耦升级）
- IDE 外验证方式
- 提示该节是 v2 身份下的"第一刀小修"，全文重写留 v0.2

**关键合规检查**：grep "pip install fcop-mcp" 命中 1 处 — 是"一般是 `pip install fcop-mcp` 或 `uvx fcop-mcp`，请以上游 README 为准"这种**指向上游**的措辞，不是步骤教程。✅ 不违反硬规则 #5。

### B1（1 改动）

`docs/agents/CURRENT-ROLES.md` 新建（236 行），结构：

1. 顶部宪法引用块（与 README 一致）
2. 当前活跃团队声明（dev-team 活跃 / media/mvp/qa-team 模板）
3. dev-team 5 角色三源对照表（`.cursor/rules` × `docs/agents` × `codeflow-plugin/agents`）
4. 跨角色协议（codeflow-project rule + collaboration brief + agents/README.md）
5. 协议元数据头模板
6. 三源关系图（ASCII，含冲突时谁赢）
7. 未来演进路径（链向设计文档 §3.2 + §8.6 backlog）
8. 本文件的职责边界（"不做"清单避免抢跑）

**关键不做事项验证**：
- ✅ 没创建 `.codeflow/` 任何子目录
- ✅ 没创建 `roles.yaml`
- ✅ 没改任何 source of truth（`.cursor/rules/` / `docs/agents/{ROLE}-01.md` / `codeflow-plugin/agents/`）
- ✅ 没引入 `Agent.layer` 等 FCoP Issue #2 待评审字段

### C1（35 改动 = 33 mv + 1 superseded 旗 + 1 README）

**git mv 实际命令**（一行 PowerShell 串联 33 个 `git mv`）：

```powershell
New-Item -ItemType Directory -Force -Path 'docs\agents\tasks\_archive\2026-04' | Out-Null
Get-ChildItem 'docs\agents\tasks' -File -Filter '*.md' |
  Where-Object { $_.Name -match '^(TASK|REPORT)-2026(0403|0408|0420|0421|0422|0423|0425)' } |
  ForEach-Object {
    git mv "docs\agents\tasks\$($_.Name)" "docs\agents\tasks\_archive\2026-04\$($_.Name)"
  }
```

**归档清单**（33 个文件）：
- 2026-04-03: 1 个 (`TASK-001-SYSTEM-to-PM`)
- 2026-04-08: 1 个 (`TASK-001-PM01-to-ADMIN01`)
- 2026-04-20: 4 个 (`TASK-001-{ADMIN-to-PM, DEV-to-PM, PM-to-ADMIN, PM-to-DEV}`)
- 2026-04-21: 16 个（12 TASK + 4 REPORT，跨 4 个 thread_key）
- 2026-04-22: 1 个 (`TASK-001-PM-to-ADMIN`)
- 2026-04-23: 7 个 (`TASK-001-007-PM-to-ADMIN`)
- 2026-04-25: 3 个（2 TASK + 1 REPORT「FCoP 与 Bridgeflow 分仓总结」）

**TASK-005 SUPERSEDED 旗**：
- frontmatter 加 `status: SUPERSEDED` + `superseded_by: TASK-20260509-006` + `superseded_at: 2026-05-09T10:42+08:00`
- 内容顶部加 `> ⚠️ SUPERSEDED — 不要执行本任务` 引用块（含原由 + 链向 TASK-006 + 链向 §8.6）
- 文件保留在 root（不归档）— 因为它的"被取代"故事跟 5/9 thread 紧绑

**`_archive/README.md`** 新建（约 70 行），含：归档原则 4 条 + 结构示意 + 引用稳定性说明 + SOP（PowerShell 脚本）+ 不归档判定表 + 当前归档状态表

## 10 项验收逐项确认

| # | 验收项 | 实测 | 通过？|
|---|---|---|---|
| 1 | A1 措辞不破坏硬规则 #5 | grep `pip install fcop-mcp` = 1 处（"一般是…请以上游为准"，不是步骤）| ✅ |
| 2 | B1 文档完整 + 不创建 roles.yaml/.codeflow/ | CURRENT-ROLES.md = True；.codeflow = False；roles.yaml = False | ✅ |
| 3 | C1 - 29+ 个文件在 `_archive/2026-04/` | 33 个（≥ 29）| ✅ |
| 4 | C1 - tasks/ root 干净（≤ ~17）| 15 个（README + 12 个 5/9 active + TASK-007 + REPORT-007 已合算）| ✅ |
| 5 | C1 - TASK-005 加 SUPERSEDED 旗 | grep `SUPERSEDED` = 4 处命中 | ✅ |
| 6 | C1 - `_archive/README.md` 存在 | True | ✅ |
| 7 | ReadLints 零错误 | 0 错误（5 文件全过）| ✅ |
| 8 | 不动 `.cursor/rules/` 任何文件 | git diff --name-only HEAD -- `.cursor/rules` = 0 | ✅ |
| 9 | 不动 `codeflow-plugin/agents/` 任何文件 | git diff --name-only HEAD -- `codeflow-plugin/agents` = 0 | ✅ |
| 10 | 不删 `_ignore/audit_fcop_*` 任何文件 | Test-Path `_ignore/audit_fcop_project.py` = True | ✅ |

## 影响评估

| 维度 | 影响 |
|---|---|
| `.cursor/rules/` 强约束规则 | ❌ 0 改动 |
| `docs/agents/{ROLE}-01.md` 角色说明文档 | ❌ 0 改动 |
| `codeflow-plugin/agents/` v1 brief 素材 | ❌ 0 改动 |
| Cursor agent 现有会话 | ✅ 0 影响 — 任何 agent 的接收源 / rule 都没变 |
| `@codeflow/protocol` / `@codeflow/runtime` 工程 | ✅ 0 影响 — 没碰 packages/ |
| `D:\FCoP` 上游仓 | ✅ 0 影响 — 全程未触碰 |
| 外部 contributor 现有引用 | ⚠️ 4 月历史 task 路径变化（root → _archive/2026-04/）；通过 git follow 仍可追溯；`_archive/README.md` 已说明引用稳定性原则 |
| `tasks/` root 可读性 | ✅ 大幅提升（54 → 15 文件；只剩 active thread + TASK-005 SUPERSEDED 旗）|

## tasks/ root 现状（15 文件）

```
docs/agents/tasks/
├── README.md
├── _archive/
│   ├── README.md
│   └── 2026-04/  (33 个文件)
├── REPORT-20260509-001-DEV-to-PM.md         (sdk-spike thread)
├── REPORT-20260509-002-DEV-to-PM.md         (runtime-skeleton thread)
├── REPORT-20260509-003-PM-to-ADMIN.md       (fcop-issue-decision thread)
├── REPORT-20260509-006-DEV-to-PM.md         (rule5-purge thread)
├── REPORT-20260509-007-DEV-to-PM.md         (本文件 - pre-s3-housekeeping)
├── REPORT-20260509-007-PM-to-ADMIN.md       (rule5-purge thread)
├── REPORT-20260509-008-PM-to-ADMIN.md       (charter+§8.6 thread)
├── REPORT-20260509-009-PM-to-ADMIN.md       (charter块嵌入+Issue#2 thread)
├── REPORT-20260509-010-PM-to-ADMIN.md       (pre-s3-housekeeping thread)
├── TASK-20260509-002-PM-to-DEV.md           (runtime-skeleton thread)
├── TASK-20260509-003-ADMIN-to-PM.md         (fcop-issue-decision thread)
├── TASK-20260509-004-PM-to-ADMIN.md         (fcop-issue-decision thread)
├── TASK-20260509-005-PM-to-DEV.md           ⚠️ SUPERSEDED by TASK-006
├── TASK-20260509-006-PM-to-DEV.md           (rule5-purge thread)
└── TASK-20260509-007-PM-to-DEV.md           (本任务 派单文件)
```

**5 个活跃 thread**：sdk-spike / runtime-skeleton / fcop-issue-decision / rule5-purge / pre-s3-housekeeping  → 全部已闭环到本 REPORT 为止；下一 sprint S3 可以从干净状态启动。

## 自测

| 自测项 | 命令/方式 | 结果 |
|---|---|---|
| 改动文件 lint | `ReadLints` × 5 文件 | 0 错误 |
| `git status` 干净度 | 只显示本任务相关改动 + 1 个文件被 git tracked 但 modified（TASK-005）| ✅ |
| 验收 10 项 | 上节表 | 9/10 严格通过 + 1/10 预期命中 |
| `@codeflow/protocol` 测试 | 未跑（本任务不改代码）| N/A |

## 给 PM 的建议

1. **本任务确实做完了，可以独立 commit** — 建议 message: `chore(s3-prep): pre-Sprint-S3 housekeeping — fcop guide + roles map + tasks archive`
2. **Sprint S3 现在可以启动** — 角色配置清晰、tasks/ root 干净、fcop 接入指引就位、不抢跑 FCoP Issue #2
3. **B1 中提到的"未来用脚本自动生成 CURRENT-ROLES.md"是个好想法** — 留作 §8.6 backlog 新增条目（PM 自行决定是否加）

DEV-01 待命。
