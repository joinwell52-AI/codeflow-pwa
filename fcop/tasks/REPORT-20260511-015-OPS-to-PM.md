---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260511-015
sender: OPS
recipient: PM
priority: P1
thread_key: codeflow-fcop-layout-migration-docs-agents-to-fcop
references:
  - TASK-20260511-015-PM-to-OPS
  - TASK-20260511-014-PM-to-OPS
  - REPORT-20260511-014-OPS-to-PM
layer: worker
risk_level: high
---

# REPORT-20260511-015：docs/agents → fcop layout migration 回执

## 一句话结论

OPS-015 已完成并推送：layout migration commit `c650c39` 已将 CodeFlow 协作 workspace 对齐到 fcop@1.1.0 默认布局 `fcop/`，`origin/main` 与 `backup/main` 均 MATCH。本次未打 tag、未推 tag、未动 `gitee`。

## 一、Commit 验证

```text
c650c39a424148a0576ded2f82dd849f57e2d91a
feat(layout-migration): align CodeFlow workspace to fcop@1.1.0 default layout (docs/agents -> fcop/)
```

提交规模：

```text
258 files changed, 6273 insertions(+), 229 deletions(-)
```

主要范围：

```text
docs/agents/*              -> fcop/*
docs/agents/tasks/*        -> fcop/tasks/*
docs/internal/*            -> fcop/internal/*
codeflow-shell/runtime/docs/rules/templates path references updated
```

未纳入：

```text
scripts/append-day3-report.py
scripts/append-day4-report.py
```

## 二、物理验证

```text
Test-Path fcop/tasks        -> True
Test-Path docs/agents       -> False
Test-Path fcop/internal     -> True
Test-Path docs/internal     -> False
git ls-files fcop           -> 197
git ls-files docs/agents    -> 0
```

说明：`fcop` 计数为 197，高于 PM 预估的约 172，是因为本次一并纳入了 P4 sprint 期间尚未归档的 task/report/draft 文件，以及 `fcop/internal/emergence-log.md`。

## 三、代码与路径替换报告

已更新：

- `codeflow-shell/src/main.ts` 删除 `workspaceDir` override，改用 fcop default auto-detect。
- `packages/codeflow-runtime/src/Runtime.ts`、`InboxWatcher.ts` 注释/默认说明改为 `fcop/tasks/`。
- `codeflow-plugin/hooks/hooks.json` matcher 改为 `fcop/**/*.md`。
- `.cursor/rules/*.mdc`、desktop templates、plugin skills、公开 docs、runtime docs、release notes 等路径示例改为 `fcop/`。
- `fcop/tasks/` 历史 task/report 正文未批量改写，保持历史语义。

残留 `docs/agents` 命中只在历史记录中：

```text
CHANGELOG.md
.fcop/proposals/20260421-171851.md
```

这两类为历史 changelog/proposal 语境，未作为当前 runtime/config 路径处理。

## 四、Safety HARD GATE 10 项

| # | 检查 | 结果 |
|---|---|---|
| 1 | Cursor key `crsr_[0-9a-f]{16,}` | 0 match |
| 2 | ck_ key `ck_[0-9a-f]{16,}` | 0 match |
| 3 | sk- key `sk-[A-Za-z0-9]{20,}` | 0 match |
| 4 | GitHub token `(ghp_\|gho_\|ghs_)[A-Za-z0-9]{36,}` | 0 match |
| 5 | AWS key `AKIA[0-9A-Z]{16}` | 0 match |
| 6 | physical: `fcop/tasks` exists, `docs/agents` absent | pass |
| 7 | physical: `git ls-files fcop` / `docs/agents` count | `197` / `0` |
| 8 | runtime tests | pass 141 / fail 0 |
| 9 | TypeScript 3 workspaces | all exit 0 |
| 10 | smoke 2 modes | both pass |

额外 forbidden staged check：

```text
scripts/append-day3-report.py -> not staged
scripts/append-day4-report.py -> not staged
_ignore/_tmp/.smoke/node_modules/.env/package files -> not staged
```

## 五、测试与 smoke

### 5.1 TypeScript

```text
packages/codeflow-runtime: npx tsc --noEmit -> exit 0
codeflow-shell: npx tsc --noEmit -> exit 0
packages/codeflow-protocol: npx tsc --noEmit -> exit 0
```

### 5.2 Runtime tests

```text
@codeflow/runtime@0.2.0-beta.3 test
tests 141
suites 12
pass 141
fail 0
cancelled 0
skipped 0
todo 0
```

### 5.3 Smoke A：yaml fallback

```text
CODEFLOW_SKIP_FCOP_PROBE=1 npm start

fcop bridge    : (skipped — CODEFLOW_SKIP_FCOP_PROBE=1 in env)
Task parser    : yaml fallback (no fcop client)
Review writer  : ReviewWriter=yaml (no fcop client)
Inbox watcher  : InboxWatcher=Day-1 pass-through (no fcop client)
Status         : running. Drop TASK-*-XXX-to-AGENT.md to inbox.
```

### 5.4 Smoke B：real fcop

```text
PYTHON_BIN=__REPLACE_WITH_YOUR_PYTHON_312_PATH__ npm start

fcop bridge    : fcop 1.1.0 via pythonia
Task parser    : TaskParser=fcop
Review writer  : ReviewWriter=fcop + NeedsHumanGate fcop audit wired
Inbox watcher  : InboxWatcher=fcop schema-gating (onValidationFail=dispatch_anyway)
Status         : running. Drop TASK-*-XXX-to-AGENT.md to inbox.
```

## 六、origin/backup hash 对账

```text
local : c650c39a424148a0576ded2f82dd849f57e2d91a
origin: c650c39a424148a0576ded2f82dd849f57e2d91a
origin MATCH

backup: c650c39a424148a0576ded2f82dd849f57e2d91a
backup MATCH
```

Push 输出：

```text
origin main: 9506a91..c650c39
backup main: 9506a91..c650c39
```

## 七、gitee / tag 策略

gitee 仍 G3：

```text
62532a7d32779bbd0ec09c7e0fbcb6cc6541b4fe refs/heads/main
```

未创建 / 未推送 `v0.3*` tag：

```text
git tag --list "v0.3*"
no output

git ls-remote --tags origin "v0.3*"
no output

git ls-remote --tags backup "v0.3*"
no output
```

## 八、post-push 状态

写本 REPORT 前：

```text
?? scripts/append-day3-report.py
?? scripts/append-day4-report.py
```

写本 REPORT 后预期新增：

```text
?? fcop/tasks/REPORT-20260511-015-OPS-to-PM.md
```

## 九、观察与风险记录

1. 最初 `git mv docs/agents fcop` 目录级 rename 在 Windows 上返回 `Permission denied`。OPS 改为逐项 `git mv` top-level 文件/`tasks/` 子目录，成功完成迁移。
2. 批量路径替换脚本第一次遇到 PowerShell `python -c` 换行转义失败，第二次遇到本机 Python `Path.write_text(newline=...)` 兼容问题；最终改为 stdin Python + `open(..., newline=...)`，符合项目 UTF-8 规则。
3. `bridgeflow-nudger/` 为 ignored 目录，曾被路径替换脚本触及但未 stage、未强行 `git add -f`。
4. GitHub push 仍提示 `joinwell52-AI/codeflow-pwa` default branch 有 12 个 Dependabot vulnerabilities（8 high, 3 moderate, 1 low）。本任务不处理。

## 十、结论

OPS-015 完成。`main` 当前稳定在 `c650c39`，CodeFlow workspace 已迁移到 `fcop/` 默认布局，可继续 Day 5/Day 6 收官；`v0.3.0-alpha` tag 仍应等 Day 6 EOD 后处理。
