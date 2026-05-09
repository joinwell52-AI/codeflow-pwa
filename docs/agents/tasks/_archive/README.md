# tasks/ 归档区（_archive）

> 本目录是 `docs/agents/tasks/` 的**已闭环 thread 归档区**。
> 当 `tasks/` 根目录下的文件累积到一定规模、且 thread 已确认闭环、且距今足够久（≥ 7 天），就会被搬到这里。

## 归档原则

文件被归档的 4 个条件（**全部满足才归档**）：

1. **thread 已闭环** —— 最后一封 `XX-to-ADMIN` 报告已发出，ADMIN 已默认或明示接受
2. **距今 ≥ 7 天** —— 给 contributor 留时间在 root 层引用
3. **没有跨 thread 引用** —— 不被任何 active thread 通过 `references:` 字段引用
4. **不是 README.md 之类的"目录说明"文件**

## 归档结构

```
docs/agents/tasks/_archive/
├── README.md                  # 本文件
├── 2026-04/                   # 按月归档
│   ├── TASK-20260403-001-*.md
│   ├── TASK-20260420-*.md
│   ├── TASK-20260421-*.md
│   ├── ...
│   └── REPORT-20260425-*.md
├── 2026-05/                   # 当前月（5 月底归档时启用）
└── ...
```

按月分目录的好处：
- 一目了然
- `git log -- _archive/2026-04/` 直接拉出当月所有 thread 历史
- 跨年时再加一层 `2026/`、`2027/` 隔离

## 引用稳定性

文件被归档（`git mv`）后路径变化，但：
- ✅ Git history 完整保留（`git log --follow <file>` 仍能跟踪）
- ✅ Markdown 链接如果用相对路径，归档后大概率失效——但归档前我们已确保 thread 闭环，不再被外部引用
- ⚠️ 设计文档（`docs/design/codeflow-v2-on-fcop-sdk.md`）若有引用归档文件，应先在归档前更新链接

## 归档操作 SOP（PM 执行）

```powershell
# 1. 确认待归档文件清单（按月份过滤）
Get-ChildItem 'docs\agents\tasks' -File -Filter '*.md' | Where-Object { $_.Name -match '^(TASK|REPORT)-2026MM' }

# 2. 创建月份目录
New-Item -ItemType Directory -Force -Path 'docs\agents\tasks\_archive\2026-MM'

# 3. git mv 一次性搬移
Get-ChildItem 'docs\agents\tasks' -File -Filter '*.md' | Where-Object { $_.Name -match '^(TASK|REPORT)-2026MM' } | ForEach-Object { git mv "docs\agents\tasks\$($_.Name)" "docs\agents\tasks\_archive\2026-MM\$($_.Name)" }

# 4. 单独 commit，message: "chore(archive): archive 2026-MM thread (N files)"
```

## 不归档的判定

下列情况**不**归档（留在 `tasks/` root）：

| 情况 | 处理 |
|---|---|
| `README.md` | 永远留 root |
| `TASK-005` 这类 SUPERSEDED 但有重要历史价值的（被同月 thread 取代）| 留 root，加 `status: SUPERSEDED + superseded_by:` 旗 |
| `references:` 字段被某个 active thread 引用 | 跟引用方一起处理（要么取消引用，要么一起归档）|
| ADMIN 显式打招呼"先别归档" | 听 ADMIN 的 |

## 当前归档状态（2026-05-09 起）

| 归档月 | 文件数 | 涉及 thread 数 | 触发任务 | 备注 |
|---|---|---|---|---|
| 2026-04/ | 33 | ~14 个 thread（covers 2026-04-03 ~ 04-25 全部 v1 时代 task）| `TASK-20260509-007-PM-to-DEV` | Sprint S3 启动前清理 |

> 📌 本目录由 PM-01 维护。任何 contributor 想归档新一批文件，请先开 PM-to-ADMIN 报告说明，得到回应后再 `git mv`。
