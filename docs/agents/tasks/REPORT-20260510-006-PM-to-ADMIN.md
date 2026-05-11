---
protocol: fcop
version: 1
kind: report
report_id: REPORT-20260510-006
sender: PM
recipient: ADMIN
priority: P0
thread_key: codeflow-v0.2.0-beta-1-real-sdk-blocked-by-bug-sdk-002-and-beta-2-hotfix-launched
references:
  - REPORT-20260510-005-PM-to-ADMIN
  - REPORT-20260510-011-OPS-to-PM
  - REPORT-20260510-011-QA-to-PM
  - TASK-20260510-012-PM-to-DEV
layer: governance
---

# REPORT-20260510-006：v0.2.0-beta.1 落地 + BUG-SDK-002 + 派 v0.2.0-beta.2 hotfix

## §一 一句话结论

**OPS-011 + QA-011 双双完工**：v0.2.0-beta.1 tag 已落（10 min）、QA 跑真 SDK 验收（25 min）。**但 QA 揭示 BUG-SDK-002**（`agent already has active run`，与 BUG-SDK-001 同样阻塞 real SDK）。PM 与 BUG-SDK-001 处理一致 — **升 P0 hotfix**，已派 [TASK-20260510-012-PM-to-DEV](TASK-20260510-012-PM-to-DEV.md)，目标 `v0.2.0-beta.2`，SLA ≤ 120 min。**真 SDK 完整闭环离 ADMIN ≤ 165 min**（DEV 120 + OPS 10 + QA 35）。

---

## §二 ✅ 已完成（10 min OPS + 25 min QA = 35 min 双线）

### §2.1 OPS-011（22:00 派 → 22:09 完工，9 min ⚡）

| | |
|---|---|
| Commit A | `cd6fb28 fix(s6-v0.2-sprint0-mt1-hotfix)` (8 文件 / 386+ 28-) |
| Commit B | `ee3207e docs(s6-v0.2-sprint0-mt1-archive)` (6 文件 / 1297+) |
| 本地 tag | ✅ `v0.2.0-beta.1`（不推 origin/backup tag）|
| 三仓 main | origin/backup ✅ 同步；gitee 仍 G3 ✅ |
| Runtime tests | 104/104 0 fail |
| 安全 HARD GATE | ✅ stage 前 0 / ✅ stage 后 0 / ✅ `.env*` 0 stage |

### §2.2 QA-011（22:00 派 → 22:35 完工，35 min）

| 验收点 | 结果 |
|---|---|
| Safety HARD GATE | ✅ 5/5 |
| A-07（banner live + model）| ✅（验证 MT-1 wire-through：banner 显示 `defaultModel="claude-sonnet-4"`）|
| A-09（UUID sdk_id）| ✅（2 次独立测试，2 个 UUID）|
| **A-08（真 verdict）** | ❌ FAIL — **新错误**：BUG-SDK-002 |
| **A-10（transcript）** | ❌ FAIL — 依赖 A-08 |
| **BUG-SDK-001 状态** | 根因（model wire）✅ 修复，但**保持 P1** — 因下游 BUG-SDK-002 阻断功能验证 |

---

## §三 🚨 BUG-SDK-002（新 P1，与 001 同样阻塞 real SDK）

### §3.1 错误信号

```text
agent.send failed for sdk_agent_id="agent-f07388df-...":
  Agent agent-f07388df-... already has active run (code=undefined, isRetryable=false)
```

### §3.2 与 BUG-SDK-001 对比

| | BUG-SDK-001（QA-009）| BUG-SDK-002（QA-011 新）|
|---|---|---|
| 错误信息 | `Local SDK agents require an explicit model` | `Agent already has active run` |
| MT-1 fix 后 | ✅ 消除 | 新错误浮现 |
| 根因层级 | model 参数缺失 | SDK run lifecycle 误用 |
| 复现 | 100%（QA-009 单测）| 100%（QA-011 双测）|

### §3.3 QA 推测根因 + 修复方向（PM 接受）

`Agent.create({ local: { cwd } })` 在 local mode 自动启动一个 run；`CursorSdkAdapter.send()` 紧跟着尝试启动第 2 个 run → SDK 拒绝。

修复方向（DEV 自选 A/B/C/D，TASK-012 §四 详述）：
- A：让 `Agent.create()` 不自动启 run
- B：`send()` 复用 create 启动的 run
- C：`create()` 不传 prompt + `send()` 显式启 run
- D：cloud mode（fallback only）

PM 倾向 A → B → C → D。

---

## §四 PM 决策与 BUG-SDK-001 一致 — P0 hotfix

| 选项 | 性质 | PM 选择 |
|---|---|---|
| A. 升 P0 hotfix（v0.2.0-beta.2）| 与 BUG-SDK-001 处理一致 | ⭐ |
| B. 合并到 P3 (relay-bridge) | QA §七 「有条件通过」推荐 | ❌ |
| C. 推到 v1.0 final | 拖 2 周 | ❌ |

**PM 选 A 理由**：
1. BUG-SDK-002 与 BUG-SDK-001 性质相同（real SDK 完全阻塞），处理一致性
2. 已投 2 次 hotfix（α→β / β→β.1），再投 1 次（β.1→β.2）= 把 v0.2-sprint-0「连续 hotfix 暴露+清零」节奏继续走
3. ADMIN 期待 real verdict 真试用 — v0.2.0-beta.1 仍标「待 QA-011」，QA-011 ❌ → 不能宣告 trial-ready
4. 修复估 90-120 min，**比让 ADMIN 等 P3 完工（5/12 EOD）快 1.5 天**
5. P3 (relay-bridge) 时让 SDK 路径已 trial-ready，不混一坨

→ 已派 [TASK-20260510-012-PM-to-DEV](TASK-20260510-012-PM-to-DEV.md)，SLA ≤ 120 min，目标 v0.2.0-beta.2。

---

## §五 ADMIN 待办（按重要度）

### §5.1 ⭐ **P0** — 在 DEV cursor session 打 1 次「巡检 开工」

启动 TASK-20260510-012 BUG-SDK-002 hotfix。

### §5.2 ⭐ **P0** — 在 `codeflow-shell/.env` 加 1 行 model 配置

QA-011 §八 #2 推荐：

```bash
# 编辑（不要 cat）：
notepad codeflow-shell\.env
# 加上一行（如已有则跳过）：
CURSOR_DEFAULT_MODEL=claude-sonnet-4
```

效果：
- 消除 banner WARNING 块（QA-011 §三 现象）
- 让 QA-013 重跑 A-08/A-10 时直接拿到 model 默认值，不需 env var override
- 完全可逆 — 删除该行即恢复

PM **不**自动给 ADMIN 改 `.env` — 该文件仅 ADMIN 持有写权（PM 不读 .env 是 §SAFETY HARD GATE 同源）。

### §5.3 P1 — DEV-012 完工后，在 OPS / QA cursor session 各打 1 次「巡检 开工」

走完 OPS-013 commit + tag → QA-013 重跑 A-08/A-10。

### §5.4 P2 — 持续未决（已挂多日）

- 试用 v0.1.0-rc.1 / 拍板 issue #2 reply / 回 D4 / 提供 SSH 凭据 — 等任意空档处理

---

## §六 时间线（最终目标 — v0.2.0-beta.2 trial-ready）

```
现在 22:18 — PM 已派 TASK-012-PM-to-DEV
   ↓ ADMIN 唤醒 DEV
22:18 → 24:18 (≤120min)  DEV-012 BUG-SDK-002 hotfix
   ↓ ADMIN 唤醒 OPS
24:18 → 24:30 (~12min)   OPS-013 commit + 本地 tag v0.2.0-beta.2
   ↓ ADMIN 唤醒 QA
24:30 → 25:05 (~35min)   QA-013 重跑 A-08/A-10
   ↓
25:05  🎯 v0.2.0-beta.2 + BUG-SDK-001/002 双 closed + 真 SDK 完整闭环
       ⤴ PM 派 DEV P3 (relay-bridge) 正式单（fcop@1.0 已就位 + DEV §八 read-only 已暖机）
       ⤴ PM 写 REPORT-007-PM-to-ADMIN 终结 v0.2.0-beta 系列
```

→ **真 SDK 完整闭环离 ADMIN ≤ 165 min**（≤ 2h45min，不计 ADMIN 唤醒延迟）。

---

## §七 路线影响 — **不变**

`v1.0` 公开发布：**实际 5/24 EOD / 对外 5/27**（3 天缓冲）。

理由：
- BUG-SDK-002 hotfix 算在 v0.2 sprint-0 内（同 BUG-SDK-001 一致），不计入 P3/P4 工期
- DEV §八 自决 P3 pre-analysis 已暖机，BUG-SDK-002 修完即可无缝切 P3 实现
- fcop@1.0 已落 PyPI（5/9，提前 7 天）= P4 提前启动空间充足

**对外承诺锁定 5/27** 不动。

---

## §八 PM 自约束审计（本轮）

| 决策 | 性质 | 处置 |
|---|---|---|
| 接受 OPS-011 commit + tag | 常规推荐 | ✅ 自决 |
| 接受 QA-011 验收 + BUG-SDK-002 P1 判断 | 常规推荐 | ✅ 自决 |
| **BUG-SDK-002 升 P0 hotfix（不合并 P3）** | 与 BUG-SDK-001 一致政策 | ✅ 自决（与上轮判例同源）|
| 派 TASK-012 给 DEV，4 修复方向 + DEV 自选 | 常规推荐 | ✅ 自决（不锁死方向给 DEV 留空间）|
| `.smoke-*` gitignore 防御（顺手）| 常规推荐 | ✅ 自决（合并进 TASK-012 §5.5）|
| ADMIN 编辑 `.env` 加 model（PM 不替）| 常规推荐 + 保护 ADMIN 边界 | ✅ 自决 |
| 路线 5/27 对外不变 | 已锁定 | ✅ 自决 |

→ **0 越权 + 0 上交 ADMIN 待决**（除 ADMIN 必做的 §5.1 + §5.2 两个动作）。

---

## §九 一句话送 ADMIN

> v0.2.0-beta.1 落地（OPS 9 min ⚡）、QA 揭示 BUG-SDK-002（与 BUG-SDK-001 同病一治）、PM 升 P0 hotfix 派 v0.2.0-beta.2。
>
> **你这次只做 2 件事**：
>
> 1. `notepad codeflow-shell\.env` 加一行 `CURSOR_DEFAULT_MODEL=claude-sonnet-4`
> 2. 在 DEV cursor session 打「巡检 开工」启动 TASK-012
>
> 然后躺平 ≤ 165 min（DEV → OPS → QA），等 PM 通报「v0.2.0-beta.2 + 真 SDK 完整闭环 + 双 BUG closed」。
>
> 路线 5/27 公开发布锁定不动。

PM-01
2026-05-10 22:18 (UTC+8)
