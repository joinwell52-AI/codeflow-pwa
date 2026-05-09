# 码流 — 当前角色配置一览（CURRENT-ROLES）

> ### 📜 项目宪法（ADMIN 5/9 双总纲句）
>
> 1. ADMIN 5/9 10:48 — 「**这个项目文件就是码流的，目前项目是用 cursor 的 sdk，应用 fcop-mcp。**」
> 2. ADMIN 5/9 10:51 — 「**码流是做成一个 CodeFlow 的真正定位：一个面向多 Agent 协作开发的轻量级 AI Runtime / AI OS。**」
>
> 完整解读：[设计文档 §0.0](../design/codeflow-v2-on-fcop-sdk.md)

> 📌 **本文件是 Sprint S3 启动前的"角色配置当前快照"**。
>
> 它**不创建**任何新格式（如 `roles.yaml` / `.codeflow/`）；只把当前已经分散在 3 个地方的角色信息，归集成一张方便查阅的对照表。
>
> 真正的 v2 角色注册表（按 [设计文档 §3.2](../design/codeflow-v2-on-fcop-sdk.md) 格式的 `roles.yaml`）要等 [FCoP Issue #2](https://github.com/joinwell52-AI/FCoP/issues/2)（`Agent.layer` 字段）评审通过 + Sprint S3 启动后再建。详见 [§8.6 backlog #5](../design/codeflow-v2-on-fcop-sdk.md)。

---

## 一、当前活跃团队

| 团队 | 状态 | 说明 |
|---|---|---|
| **dev-team** | ✅ **活跃** | PM / DEV / QA / OPS + ADMIN（人）；当前所有 v2 工作都跑在这个团队下 |
| media-team | ⏸️ 模板素材 | 4 角色 brief 仍在 `codeflow-plugin/agents/media-team/`，未启用 |
| mvp-team | ⏸️ 模板素材 | 同上 |
| qa-team | ⏸️ 模板素材 | LEAD-QA / TESTER / AUTO-TESTER / PERF-TESTER 4 角色 brief 在 `.cursor/rules/qa-team-*.mdc`（rule 已就位）+ `codeflow-plugin/agents/`（brief 素材待迁移），未启用 |

> ⚠️ 启用 media/mvp/qa-team 任意一个团队都属于"v2 范围扩展"，不在当前 sprint scope，需要 ADMIN 显式授权。

## 二、dev-team 五角色 — 三源对照表

> 当前 dev-team 的角色信息**同时**存在 3 个来源（互相不同步）。本表把它们对齐一张表，便于查阅。
>
> 🔥 **强制（source of truth）** = `.cursor/rules/*-bridge.mdc` —— Cursor agent 自动应用，违反会被 rule 系统拦
> 🟡 **说明性** = `docs/agents/{ROLE}-01.md` —— 角色定位 + 职责，给人和 agent 阅读
> 🟢 **brief 素材**（v1 时代位置，等迁移）= `codeflow-plugin/agents/dev-team/{role}.md`

| 角色 | `.cursor/rules/` 强约束 🔥 | `docs/agents/` 说明文档 🟡 | `codeflow-plugin/agents/dev-team/` v1 brief 🟢 | 接收源（按规则）|
|---|---|---|---|---|
| **ADMIN** | [`admin-human-bridge.mdc`](../../.cursor/rules/admin-human-bridge.mdc) + `.en.mdc` | [`ADMIN-01.md`](./ADMIN-01.md) + `.en.md` | （无 — admin 是真人，无 brief） | 真人，唯一 boss |
| **PM** | [`pm-bridge.mdc`](../../.cursor/rules/pm-bridge.mdc) + `.en.mdc` | [`PM-01.md`](./PM-01.md) + `.en.md` | [`pm.md`](../../codeflow-plugin/agents/dev-team/pm.md) | 只接 `TASK-*-ADMIN-to-PM.md` |
| **DEV** | [`dev-bridge.mdc`](../../.cursor/rules/dev-bridge.mdc) + `.en.mdc` | [`DEV-01.md`](./DEV-01.md) + `.en.md` | [`dev.md`](../../codeflow-plugin/agents/dev-team/dev.md) | 只接 `TASK-*-PM-to-DEV.md` |
| **QA** | [`qa-bridge.mdc`](../../.cursor/rules/qa-bridge.mdc) + `.en.mdc` | [`QA-01.md`](./QA-01.md) + `.en.md` | [`qa.md`](../../codeflow-plugin/agents/dev-team/qa.md) | 只接 `TASK-*-PM-to-QA.md` |
| **OPS** | [`ops-bridge.mdc`](../../.cursor/rules/ops-bridge.mdc) + `.en.mdc` | [`OPS-01.md`](./OPS-01.md) + `.en.md` | [`ops.md`](../../codeflow-plugin/agents/dev-team/ops.md) | 只接 `TASK-*-PM-to-OPS.md` |

## 三、跨角色协议（共享）

| 文件 | 作用 |
|---|---|
| [`.cursor/rules/codeflow-project.mdc`](../../.cursor/rules/codeflow-project.mdc) + `.en.mdc` | 项目级总纲（命名约定 / YAML 元数据头 / 中继事件 / 文件编辑规范）|
| [`codeflow-plugin/agents/_shared/collaboration.md`](../../codeflow-plugin/agents/_shared/collaboration.md) | 跨角色协作规范（v1 brief 素材，等迁移）|
| [`docs/agents/README.md`](./README.md) | 角色文件结构说明（命名规范 + 团队模板说明）|

## 四、协议元数据头（每个 task/report 文件必带）

```yaml
---
protocol: fcop
version: 1
kind: task            # 或 report
sender: ADMIN         # 或 PM/DEV/QA/OPS
recipient: PM
priority: P0|P1|P2|P3
thread_key: 一组相关文件共用的 key
---
```

来源：[`docs/agents/README.md` §协议元数据](./README.md#协议元数据)

## 五、3 源之间是什么关系？

```
┌────────────────────────────────────────────────────────┐
│  .cursor/rules/{role}-bridge.mdc  ← source of truth 🔥│   Cursor 自动应用，最强制
│       │                                                 │
│       ├─ 接收源、回执格式、技术约束、严禁事项                │
│       └─ 改这里 = 改全队规则                                │
└────────────────────────────────────────────────────────┘
              │
              │ 引用 / 解释
              ▼
┌────────────────────────────────────────────────────────┐
│  docs/agents/{ROLE}-01.md  ← 说明性文档 🟡              │   人和 agent 都读
│       │                                                 │
│       └─ 角色定位 + 职责说明 + 历史背景                     │
└────────────────────────────────────────────────────────┘
              │
              │ 一致性核对
              ▼
┌────────────────────────────────────────────────────────┐
│  codeflow-plugin/agents/dev-team/{role}.md  ← brief    │   v1 plugin 时代位置
│       │                                                 │   等 §8.6 backlog #5 迁移
│       └─ agent 启动时的初始上下文（brief，可被 §3.2       │   到 .codeflow/briefs/
│         设想中的 brief_dir 字段引用）                     │
└────────────────────────────────────────────────────────┘
```

**冲突时谁赢**：
1. `.cursor/rules/` 与 `docs/agents/` 矛盾 → 以 `.cursor/rules/` 为准（rule 是强制的，docs 改一下就齐）
2. `codeflow-plugin/agents/` 与 `.cursor/rules/` 矛盾 → 以 `.cursor/rules/` 为准（v1 brief 没强制力，只是 brief 素材）
3. 任何位置都没说的事 → 回 `.cursor/rules/codeflow-project.mdc` 项目级总纲

## 六、未来演进（不在本文件 scope）

| 演进项 | 何时做 | 触发条件 |
|---|---|---|
| 创建 `.codeflow/config/roles.yaml` | Sprint S3 | FCoP Issue #2 (`Agent.layer` 字段) 评审通过 |
| 把 `codeflow-plugin/agents/dev-team/*.md` 物理迁移到 `.codeflow/briefs/` | Sprint S3 末 | `roles.yaml` 已建 + `brief_dir` 字段就绪 |
| `.cursor/rules/qa-team-*.mdc` 是否启用为 active 团队 | TBD | ADMIN 显式授权 |
| 把 `codeflow-plugin/agents/{media,mvp}-team/*` 与 `.cursor/rules/` 对齐 | TBD | media/mvp-team 启用时 |

详见 [设计文档 §3.2 + §8.6 backlog](../design/codeflow-v2-on-fcop-sdk.md)。

## 七、本文件的职责边界

✅ 本文件做：
- 把 *现状* 归集成一张表
- 提示 *冲突时谁赢*
- 链向 *源文件*（不复制内容）

❌ 本文件**不做**：
- 不创建任何新格式（如 `roles.yaml`）
- 不修改任何 source of truth（`.cursor/rules/` / `docs/agents/{ROLE}-01.md` / `codeflow-plugin/agents/`）
- 不引入 `Agent.layer` 等待评审字段（避免抢跑 FCoP Issue #2）
- 不替代设计文档 §3.2 角色注册表

> 📌 当任何 source 改动时，本文件应被同步更新（手动维护，规模很小）。下一个 sprint 应考虑用脚本自动生成本表，避免手动 drift。
