# FCoP 致 ADMIN 的一封信 —— 说明书

你好，ADMIN。

我是 **FCoP**（File-based Coordination Protocol）——让你和 AI 团队
通过**文件**协作的协议。你唯一要做的事：**告诉我你这个项目是几个人、
怎么分工。**

---

## 先把身份说清楚

一张图：

```
   人类                              AI 团队
┌─────────┐                   ┌──────────────────────┐
│  ADMIN  │◄──── TASK-*.md ──►│  leader              │
│  (你)   │                   │    │                 │
└─────────┘                   │    ├──► AI 角色 2    │
                              │    ├──► AI 角色 3    │
                              │    └──► AI 角色 4    │
                              └──────────────────────┘
```

| 身份 | 谁 | 说明 |
|---|---|---|
| **真人** | 你 | 角色代码永远是 `ADMIN`，有且只有 1 个 |
| **AI 团队** | N 个 Agent | 你自己命名的 N 个"岗位"（`PM` / `MANAGER` / `ME` …） |

- `ADMIN` **不写进 `fcop.json.roles`**，它是 FCoP 的保留角色。
- 你的指令只发给 **leader**；leader 自己决定要不要派给其他 AI（Rule 4）。
- Solo 模式下"团队"里只有 1 个 AI，但它仍然不是你——它是你的 AI 助手。

---

## 三种起手方式（按常用度排序）

### A. 只有你一个（Solo，最常用）

一句话交给 Agent：

> **"用 Solo 模式初始化项目，角色代码叫 `ME`。"**

对应工具：

```
init_solo(role_code="ME", role_label="我自己", lang="zh")
```

Solo = 一人多角色。你（`ADMIN`）和这个 AI（`ME`）直接对话，不走多级派单。
但 **Rule 0.b 仍然适用**：AI 会先写提案文件 → 动手 → 再读回自己的提案
做自审，用文件把"提案者"和"审查者"劈开。

### B. 用一套预设班子

> **"用预设团队 `dev-team` 初始化项目。"**

| 模板 | 适用 | AI 角色 | leader |
|---|---|---|---|
| `dev-team` | 软件开发 | `PM` · `DEV` · `QA` · `OPS` | `PM` |
| `media-team` | 内容创作 | `PUBLISHER` · `COLLECTOR` · `WRITER` · `EDITOR` | `PUBLISHER` |
| `mvp-team` | 创业 MVP | `MARKETER` · `RESEARCHER` · `DESIGNER` · `BUILDER` | `MARKETER` |
| `qa-team` | 专项测试 | `LEAD-QA` · `TESTER` · `AUTO-TESTER` · `PERF-TESTER` | `LEAD-QA` |

对应工具：`init_project(team="dev-team", lang="zh")`

**预设会带上职责说明书**（0.5.0 起）：每个预设都自带
每个角色的中英职责 `.md` 文件，init 时会一起落到
`docs/agents/shared/roles/` 下。Agent 被指派后可以直接读自己的
那一份，不用你再抄一遍职责。

### C. 自己搭角色

**标准句式：**

> **"我要组一个 AI 团队：4 个 AI 角色——`MANAGER` 做 leader，加上
> `CODER`、`TESTER`、`ARTIST`；团队名叫'我的设计工作室'，中文界面。"**

对应工具：

```
create_custom_team(
  team_name="我的设计工作室",
  roles="MANAGER,CODER,TESTER,ARTIST",
  leader="MANAGER",
  lang="zh"
)
```

**自建队不自带职责书，但可以抄样本**：自建完后，FCoP 会
告诉 Agent "去 `fcop://teams/<team>` 参考 4 份现成样本"
（dev-team / media-team / mvp-team / qa-team 各有一套中英
职责+协作链路）。Agent 自然会先读样本再帮你起草
`shared/TEAM-ROLES.md` 和 `shared/TEAM-OPERATING-RULES.md`，
不至于从零拍脑袋。你随口补一句 **"参考 media-team 的分工"**
就能把方向定了。

---

## 角色 ≠ Agent 窗口：你实际要开几个？

**这是 ADMIN 最常踩的坑**——看到 `dev-team` 写着 4 个角色
（`PM / DEV / QA / OPS`），以为"我得开 4 个 Cursor 窗口"。

不是这样的。

| 概念 | 在哪里 | 说明 |
|---|---|---|
| **角色（role）** | `fcop.json` / 任务文件名 | 协议里的**名分**，谁能给谁派活、谁收谁的回执 |
| **Agent（窗口）** | 你打开的每个 Cursor 聊天窗口 | 一个窗口承担**一个**角色，靠你发 `你是 {ROLE}，在 {team}` 指派 |

**协议不强制角色数 = 窗口数**。FCoP 是文件协议——你只开了 `PM` 一个
窗口，PM 派给 `DEV/QA/OPS` 的任务文件会**安静地躺在 `tasks/` 排队**，
等你开下一个窗口指派对应角色，它就自动接单。

### 最省事的开法（推荐）

| 开几个 | 怎么配 | 适用 |
|---|---|---|
| **1 个** | 当前会话就当 PM | 起手常规选择。PM 接你的单、写派单文件、排队等。真派到 DEV 时再开第 2 个 |
| **2 个** | PM + DEV | 纯写代码、没测试/部署需求 |
| **3 个** | PM + DEV + QA | 需要自测的场景 |
| **4 个** | PM + DEV + QA + OPS | 要实际部署时才值得开满 |

**大多数人从 1 个 PM 开始就够了**。不用一上来就开满 4 个——空转的
窗口只是在吃你的 token。

### ⚠️ 只开 1 个 PM ≠ Solo 模式

这两件事完全不同，别混：

| | `mode: "solo"` | `mode: "team"` + 先开 1 个 PM |
|---|---|---|
| 角色数 | 1（`ME`） | 4（`PM/DEV/QA/OPS`） |
| 能派活吗 | 不能（没有下级） | 能——PM 可以写 `TASK-...-to-DEV.md`，文件堆在 `tasks/` |
| 要切团队怎么办 | 重新 `init_project()` | 开下一个 Cursor 窗口，发指派句就行 |

说人话：**Solo 是"我就一个人干到底"；团队模式开 1 个 PM 是"我先开
PM，班子其他人随叫随到"**。

### 标准起手句

当前窗口说：

> **"你是 PM，在 dev-team"**

第二天要 DEV 了，开新窗口说：

> **"你是 DEV，在 dev-team"**（可选加线程名：`，线程 feature_login`）

两个窗口**不互相通话**，靠 `docs/agents/tasks/` 下的文件做中转。

---

## 自建角色的硬规则

角色代码会直接拼进文件名（`TASK-20260417-001-MANAGER-to-CODER.md`），
所以规矩来自文件名：

| 项 | 要求 | 对 ✅ | 错 ❌ |
|---|---|---|---|
| 角色代码 | 大写英文字母开头，用 `A-Z` `0-9` `_` `-`；`-` 不能开头/结尾/连续 | `MANAGER` `QA1` `CODER_A` `LEAD-QA` `AUTO-TESTER` | `程序员` `-QA` `PM--QA` `QA.1` `my boss` |
| 角色个数 | ≥ 2（只想一个人走 Solo） | `MANAGER,CODER` | 只有 `MANAGER` |
| Leader | 必须在角色名单里 | leader=`MANAGER` | leader=`CEO`（不在名单里） |
| 保留字 | 不能用 `ADMIN` `SYSTEM` 当角色代码 | `MANAGER` | `ADMIN` `SYSTEM` |
| 团队名 | 随便写，中英皆可（只用来显示） | "我的设计工作室" | —— |
| 语言 | `zh` 或 `en` | `zh` | `中文` `Chinese` |

**命名建议**（避免歧义）：

- ✅ 用**职能词**：`MANAGER` / `CODER` / `WRITER` / `EDITOR` / `PM` / `DEV` / `QA`
- ✅ 用**全大写拼音**：`JINGLI`（经理）/ `CHENGXU`（程序）/ `CESHI`（测试）
- ❌ 避开**权威词**：`BOSS` / `CHIEF` / `MASTER` / `OWNER` / `CEO` / `KING`
  —— 真正的"老板"是你（ADMIN），AI 不该戴这顶帽子。
- ❌ **禁止中文**：文件名规则硬性要求 ASCII。

## 主动校验：你随口说，FCoP 自动拦

**你不用读上面的规矩**。以下三种情况 FCoP 都会**在落盘前拦住**并
给出中英双语的具体原因——不是"失败/成功"，是**哪个字段哪个字符坏了、怎么改**。

| 你随口说 | Agent 会试着调 | FCoP 拦截，原因 |
|---|---|---|
| "组一个 4 人团队：`BOSS` `程序员` `测试` `设计师`" | `create_custom_team(roles="BOSS,程序员,...")` | ❌ 角色代码 `'程序员'` 非法：不允许中文 |
| "角色叫 `DEV-TEAM` 和 `QA-1`" | `create_custom_team(roles="DEV-TEAM,QA-1,...")` | ❌ 角色代码 `'DEV-TEAM'` 非法：不允许 `-`（会把文件名分隔符搞乱） |
| "角色叫 `my boss`" | `create_custom_team(roles="my boss,...")` | ❌ 角色代码 `'my boss'` 非法：不允许空格，必须大写开头 |
| "角色叫 `QA.1`" | `create_custom_team(roles="QA.1,...")` | ❌ 角色代码 `'QA.1'` 非法：不允许 `.` |
| "把 `ADMIN` 也加进团队" | `create_custom_team(roles="ADMIN,CODER,...")` | ❌ `'ADMIN'` 是 FCoP 保留字，真人用，不能给 AI 戴 |
| "就一个角色 `MANAGER`" | `create_custom_team(roles="MANAGER", ...)` | ❌ 至少需要 2 个角色；想单人请用 `init_solo(...)` |
| "leader 是 `CEO`，角色是 `MANAGER, CODER`" | `create_custom_team(roles="MANAGER,CODER", leader="CEO")` | ❌ `leader 'CEO'` 必须在角色列表里（当前：`MANAGER, CODER`） |
| "`CODER`, `CODER`, `QA`" | `create_custom_team(roles="CODER,CODER,QA", ...)` | ❌ 角色代码 `'CODER'` 重复 |

> **0.4.6 起错误消息会"手把手教你改"**：比如你说 `DEV-TEAM`，FCoP 会
> 直接回：`建议改为 DEV_TEAM（已自动修正大小写/分隔符）`。你说
> `my boss` → `建议改为 MY_BOSS`。你把 `leader` 大小写搞错 →
> `看起来你可能想选 'MANAGER'？`（did-you-mean）。建议**只是提示**，
> 最终名字永远是你定。

**一共 9 条校验项**（都跑在 `create_custom_team` / `init_solo` 里，你调了就自动过）：

1. 角色代码非空
2. 必须匹配 `^[A-Z][A-Z0-9_]*$`（大写字母开头，只能用 `A-Z` / `0-9` / `_`）
3. 禁止中文、`-`、`.`、空格
4. 不能是 `ADMIN`（真人保留）
5. 不能是 `SYSTEM`（FCoP 内部保留）
6. 非 Solo 模式下至少 2 个角色（只想单人 → 让 Agent 改用 `init_solo`）
7. 角色列表不允许重复
8. `leader` 必须是角色列表里的一员
9. 每个错误都返回**可读错误信息**（中英双语），不是布尔值

**想在动手前先验一下？** 让 Agent 调：

```
validate_team_config(roles="MANAGER,CODER,TESTER,ARTIST", leader="MANAGER")
```

不写任何文件，合法返回 `OK`，不合法直接告诉你坏在哪。适合你口述
一堆角色但不确定有没有非法字符时，让 Agent 先跑一遍。

**重点：你不用记规则。** 直接跟 Agent 自然语言说你想要啥团队，它调
`create_custom_team` 就自动过这 9 条校验，过不了会**拿着具体原因回来问你**。

---

## 起完之后会落下这些东西

```
项目根/
├── docs/agents/             ← 协作元数据（谁在做什么）
│   ├── fcop.json            ← 项目身份（mode / roles / leader）
│   ├── tasks/               ← 派发中的任务
│   ├── reports/             ← 回执
│   ├── issues/              ← 问题单
│   ├── shared/              ← 共享文档（看板、术语表…）
│   ├── log/                 ← 归档
│   └── LETTER-TO-ADMIN.md   ← 这封信本身，留个底
├── workspace/               ← ★ 产物家（代码、脚本、数据）★
│   └── README.md            ← 约定说明
└── .cursor/rules/
    ├── fcop-rules.mdc       ← 协议规则（Cursor 下每个 Agent 自动读）
    └── fcop-protocol.mdc    ← 协议解释
```

你以后的每一句话都会变成一份文件：

```
TASK-20260417-001-ADMIN-to-MANAGER.md    ← 你的指令
TASK-20260417-001-MANAGER-to-ADMIN.md    ← MANAGER 的回执
```

**这就是 FCoP 的全部。**

---

## 产物放哪：`workspace/<slug>/` 约定

这是一个很多人第一天不会意识到、第二天就翻车的问题——

**你让 Agent 做 CSDN 搜索工具，它把 `app.py`、`pyproject.toml`、
`*.bat` 全扔到项目根。第二天你让它做小游戏，`pyproject.toml` 打架，
`app.py` 被覆盖，`*.bat` 混在一起分不清是哪个的。**

FCoP 0.4.7 把答案内建到了初始化流程里：**项目根只放协作元数据，
具体产物全部进 `workspace/<slug>/`。一个"要做的事"一个 slug，互不打扰。**

```
codeflow-3/
├── .cursor/ docs/ fcop.json LETTER-TO-ADMIN.md   ← 协作骨架，永不混
└── workspace/
    ├── csdn-search/         ← 今天：CSDN 文章搜索
    │   ├── app.py
    │   ├── templates/
    │   ├── *.bat
    │   └── pyproject.toml
    └── mini-game/           ← 明天：小游戏（独立笼子，和 csdn-search 完全隔离）
        ├── game.py
        └── assets/
```

### 怎么开一个新笼子

两种方式，都合法：

1. **让 Agent 调工具**（推荐）：

    ```
    new_workspace(slug="csdn-search", title="CSDN 文章搜索工具")
    ```

    FCoP 自动建目录、写一份最小 README、落一个 `.workspace.json` 元
    数据文件。

2. **你自己 `mkdir`**：直接在 `workspace/` 下新建文件夹，Agent 一样
    认账，`list_workspaces()` 也能看见。

### slug 命名规则（FCoP 自动校验）

| ✅ 合法 | ❌ 不合法 | 为什么 |
|---|---|---|
| `csdn-search` | `CSDN-Search` | 必须小写 |
| `mini-game` | `mini_game` | 只能用 `-` 做分隔符（和角色代码反过来） |
| `weekly-report-2026w17` | `周报` | 不允许中文 |
| `api-v2` | `my game` | 不允许空格 |
| `search` | `tmp` / `shared` / `archive` | 保留字 |

和角色代码一样，输错了会拿到"建议改为 `xxx`"的友好修复提示，最长 40 个字符。

### 一键查看

想知道项目里有几个笼子、分别是啥，让 Agent 调：

```
list_workspaces()
```

输出每个 slug 的 title 和创建时间。`get_team_status()` 也会顺便
告诉你工作区数量。

### 硬规矩

- ❌ Agent **不得往项目根写业务代码**（`app.py` / `pyproject.toml` 这类）
- ❌ 不同 slug 之间不共享文件
- ✅ 需要在多个笼子之间共享的东西，自己开 `workspace/shared/`
  （FCoP 给这个 slug 留了保留字）

---

## 你怎么用 FCoP：只说人话

**先把最重要的说清楚**：FCoP 有 19 个工具——**全是给 Agent 用的，
不是给你用的**。你从头到尾只说人话，Agent 负责翻译成工具调用。

```
你（ADMIN）        Agent（AI）           FCoP 工具箱
  说人话   ────→   听懂意图   ────→   调对应工具
                                           ↓
                                    落文件 / 建目录 / 查状态
```

你不用背任何工具名。下表是"**你说这句话，Agent 会做什么**"的常见映射
——只是让你知道"Agent 该做什么、没做就能看出来"，不是让你去记。

### 项目起手阶段

| 你说的话 | Agent 会调 | 结果 |
|---|---|---|
| （新会话开口第一句） | `unbound_report()` | Agent 先汇报项目状态，没初始化/没指派角色都会告诉你 |
| "初始化 Solo 项目" / "一个人做" | `init_solo(role_code="ME")` | 落 `fcop.json`、建目录、部署规则和信、建 `workspace/` |
| "初始化开发团队" / "我要个 4 人团队" | `init_project("dev-team")` 或 `create_custom_team(...)` | 同上，但是多角色 |
| "MCP 目录绑错了" / `unbound_report` 里看到 `C:\Users\xxx` | `set_project_dir("E:\\你的项目")` | 运行时重绑，不用改配置也不用重启 |
| "你是 PM" / "你是 ME" | （不调工具，Agent 记下身份） | 进入 Phase 3，可以开始干活 |

### 日常干活

| 你说的话 | Agent 会调 | 结果 |
|---|---|---|
| "做个 CSDN 搜索工具" / "新开一个做 XXX" | `new_workspace(slug="csdn-search", title="...")` | 建 `workspace/csdn-search/` 笼子，产物全进去 |
| "派个任务给 CODER" / "让 XXX 做 YYY" | `write_task(recipient="CODER", body="...")` | 落一份 `TASK-*-to-CODER.md` |
| "看看现在项目什么状态" | `get_team_status()` | 任务/回执/问题/工作区数量 + 最近活跃 |
| "有几个工作区？" / "做过几个东西了？" | `list_workspaces()` | 列所有 `workspace/<slug>/` 和创建时间 |
| "还有哪些任务没做？" | `list_tasks()` | 列 `tasks/` 下未归档任务 |
| "xxx 任务说了什么？" | `read_task("TASK-...")` | 读正文 |
| "问题单有啥" | `list_issues()` | 列 `issues/` |
| "xxx 任务做完了归档吧" | `archive_task("TASK-...")` | 移到 `log/` |
| "看看完成回执" | `list_reports()` / `read_report(...)` | 查 `reports/` |

### 救场 / 特殊情况

| 你说的话 | Agent 会调 | 结果 |
|---|---|---|
| "FCoP 这个规则我觉得不合理" | `drop_suggestion("...", "...")` | 反馈落到 `.fcop/proposals/`（协议不让你自己改规则文件） |
| "创建团队前先验下角色名合法吗" | `validate_team_config("MANAGER,CODER", "MANAGER")` | 不落盘预检，出错给建议 |
| "有哪些预设团队？" | `get_available_teams()` | 列 Solo / dev-team / media-team / mvp-team |
| "再给我看一眼说明书" | 读 `fcop://letter/zh` 或打开 `docs/agents/LETTER-TO-ADMIN.md` | 重读这封信 |

### 真正"你可能直接用到"的只有 2 个工具名

- **`unbound_report`**：新会话 Agent 没自动汇报时，你说"先汇报"或直接
  说"调 `unbound_report`"催它一下。
- **`set_project_dir`**：发现 MCP 绑错目录（`unbound_report` 输出的项目
  路径是 `C:\Users\xxx` 之类），你说"绑到 `E:\你的项目`"或直接说
  "调 `set_project_dir("...")`"。

**其他 17 个你从来不用背**。Agent 自己会挑。

### Agent 为什么知道该调哪个？

因为 FCoP 在三个地方**同时**告诉了 Agent"你说话→我调工具"的映射：

1. **MCP instructions**（Agent 启动必读）：内建了"ADMIN 说 X → 调 Y"
   的映射表
2. **每个工具的 docstring**（Agent 看得到）：写了具体调用时机
3. **`fcop-rules.mdc`**（`alwaysApply: true`）：规则级别规定了 Rule 0
   等硬要求

所以你只管说人话。Agent 没按预期做（比如该开 `workspace/` 却没开、
该汇报却没汇报），把这封信翻给它看一下对应那行，立刻纠正。

### 6 个资源（Agent 按需读，你完全不用管）

| 资源 URI | 给谁读 | 装什么 |
|---|---|---|
| `fcop://rules` | Agent | `fcop-rules.mdc` 原文 |
| `fcop://protocol` | Agent | `fcop-protocol.mdc` 原文 |
| `fcop://letter/zh` 或 `/en` | Agent 回头查 | 这封信 |
| `fcop://status` | Agent | 同 `get_team_status` |
| `fcop://config` | Agent | `fcop.json` 原文 |

### ⚠️ Cursor 的"点灰"开关：两个千万别灰

打开 Cursor 的 MCP 面板能看到这 19 个工具每个旁边有个开关。点一下
变灰 = 禁用。**其中这 2 个一灰你就惨了**：

- `unbound_report` —— 灰了 Rule 0 失效，Agent 新会话没法做第一步
- `set_project_dir` —— 灰了 MCP 绑错目录时你只能改 `mcp.json` + 重启

剩下的 17 个你用不到的可以灰——不过 Agent 突然少了工具会一脸懵，
**建议全开就好**。

---

## 四条必读规则（缩略版）

| # | 规则 | 一句话 |
|---|---|---|
| 0.a | 落文件 | 聊天里的话没落成文件 = 没发生 |
| 0.b | 多角色制衡 | 不允许一个 AI 独自完成决策到执行 |
| **0.c** | **只落真话** | **不捏造、不臆断、引用必带出处** |
| 1 | UNBOUND | Agent 新会话先调 `unbound_report()`，等你指派身份 |

完整 9 条在 `.cursor/rules/fcop-rules.mdc`（Agent 会自动读）。
协议解释（命名、YAML、目录、巡检、0.c 的出处格式等）在
`.cursor/rules/fcop-protocol.mdc`。

---

## 不满意怎么办

- 想看完整规则 → 让 Agent 读 `fcop://rules` 或 `fcop://protocol`
- 对协议本身有意见 → 让 Agent 调 `drop_suggestion("...", "...")`，
  反馈落到 `.fcop/proposals/`，不污染协作目录
- 想换模板 → 一句话："用 `{team}` 重新初始化"
- 又想看这封信 → `fcop://letter/zh` 或 `docs/agents/LETTER-TO-ADMIN.md`

欢迎上岗。

— **FCoP**
