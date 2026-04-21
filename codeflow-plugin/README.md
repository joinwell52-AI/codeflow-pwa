# fcop — MCP toolbox for FCoP

**FCoP · File-based Coordination Protocol** —— 文件驱动的多 AI Agent 协作协议。
`fcop` 是该协议的参考实现 MCP 工具箱，让 Cursor / Claude / CLI 里的多个 Agent 像一个真团队一样协作。

> FCoP 是**协议**（规则、术语、文件约定）；`fcop` 是**工具**（MCP 服务）。
> 协议不依赖工具 —— 只要能读写文件，任何宿主都能跑 FCoP。

## 为什么要它

一句话：**AI 角色之间不能只在脑子里说话，必须落成文件。**

多个 Agent 在同一个项目里各干各的，彼此不知道对方在做什么，交接全靠人复述 —— 这是 Cursor 多 Agent 的常态痛点。
FCoP 把每一次派单、每一次交接、每一次回执都**强制变成一个磁盘文件**，走 Git，可回放、可审计、可二次分配。
装上 `fcop` MCP 的那一刻，**FCoP 协议**（`.cursor/rules/fcop-rules.mdc` 协议规则 + `.cursor/rules/fcop-protocol.mdc` 协议解释，均 `alwaysApply: true`）就注入到每一个 Agent 的系统提示里，它们从此自动遵守同一套规则。协议的目的只有一件事：**让 Agent 通过 FCoP 与团队协同工作**。

## 三套预设团队（+ 无限自定义）

| 模板 | leader | 其他角色 | 适合场景 |
|------|--------|----------|----------|
| **dev-team**   | PM        | DEV + QA + OPS                        | 软件开发 |
| **media-team** | PUBLISHER | COLLECTOR + WRITER + EDITOR           | 自媒体内容 |
| **mvp-team**   | MARKETER  | RESEARCHER + DESIGNER + BUILDER       | 创业 MVP |
| **solo**       | 你自己起名 | （单角色）                            | 一个人也要走文件自审 |
| **custom**     | 你指定    | 你指定（`create_custom_team` 工具）   | 任意工种组合 |

按 FCoP Rule 4（角色链路），`ADMIN ↔ leader` 是唯一对外接口；其他角色只从 leader 接收任务、只向 leader 回执。

## 安装

### 方式 A · `uvx`（推荐，零占用）

前置：装 [`uv`](https://docs.astral.sh/uv/)

- **Windows**
  ```powershell
  winget install -e --id astral-sh.uv --accept-package-agreements --accept-source-agreements
  ```
- **macOS / Linux**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

在 `~/.cursor/mcp.json`（Windows：`%USERPROFILE%\.cursor\mcp.json`）里加：

```json
{
  "mcpServers": {
    "fcop": {
      "command": "uvx",
      "args": ["fcop"]
    }
  }
}
```

重启 Cursor，第一次调用时 `uvx` 会自动从 PyPI 拉 `fcop` 并缓存。

### 方式 B · Cursor Deeplink 一键安装

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-light.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=fcop&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmY29wIl19)

### 方式 C · 让 Cursor Agent 自己装（最省事）

打开 Cursor → 任意项目 → 开 Agent 聊天 → 粘贴：

> 帮我装 `fcop` MCP。请在系统命令行执行下面对应平台的一条命令，跑完告诉我结果，然后提醒我重启 Cursor：
>
> **Windows（PowerShell）**
> ```
> irm https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.ps1 | iex
> ```
>
> **macOS / Linux（bash）**
> ```
> curl -fsSL https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.sh | bash
> ```

脚本会：装 `uv`（若缺）→ 把 `fcop` 合并进 `~/.cursor/mcp.json`（保留原有条目）→ 提示重启 Cursor。

### 方式 D · `pip install`

```bash
pip install fcop
```

```json
{
  "mcpServers": {
    "fcop": {
      "command": "fcop"
    }
  }
}
```

若 `fcop` 不在 PATH，用 `python -m fcop`。

### 升级

- `uvx`：`uv tool upgrade fcop`
- `pip`：`pip install -U fcop`

### 本地开发

```bash
pip install -e codeflow-plugin
```

`~/.cursor/mcp.json`：
```json
{
  "mcpServers": {
    "fcop": {
      "command": "python",
      "args": ["-m", "fcop"]
    }
  }
}
```

## 快速开始

1. 装好 `fcop` MCP 并重启 Cursor
2. 打开项目目录，开一个 Agent 聊天
3. 三选一告诉 Agent（按常用度排）：
   - **Solo（一人，最常用）**："用 Solo 模式初始化项目，角色代码叫 `ME`"
     → `init_solo(role_code="ME", lang="zh")`
   - **预设四人班子**："用预设团队 `dev-team` 初始化项目"
     → `init_project(team="dev-team", lang="zh")`
   - **自建角色**："我要组一个 AI 团队：4 个 AI 角色——`MANAGER` 做 leader，加上 `CODER`、`TESTER`、`ARTIST`；团队名叫'我的设计工作室'，中文界面"
     → `create_custom_team(team_name="我的设计工作室", roles="MANAGER,CODER,TESTER,ARTIST", leader="MANAGER", lang="zh")`
     → 不确定合不合法可以先跑 `validate_team_config(roles, leader)` 干跑校验
4. `fcop` 自动生成：
   - `docs/agents/{tasks,reports,issues,shared,log}/` 五个目录
   - `docs/agents/fcop.json` —— 项目身份配置（`mode` + 团队模板 + 角色表 + leader + 语言）
   - `docs/agents/LETTER-TO-ADMIN.md` —— 给 ADMIN 的**用户手册**（自建角色硬规则、命名建议、起手三选一）
   - `.cursor/rules/fcop-rules.mdc` —— **FCoP 协议规则**（9 条，Rule 0–8，`alwaysApply`，每次对话注入）
   - `.cursor/rules/fcop-protocol.mdc` —— **FCoP 协议解释**（规则在具体场景怎么落：文件命名、YAML、目录、巡检触发、0.c 引用格式，同 `alwaysApply`）
   - 一条欢迎任务给 leader（比如 PM / ME / MANAGER）
5. 新开 Cursor Agent 窗口，第一句话告诉它：**"你是 {ROLE}，在 {team}"**（例如"你是 PM，在 dev-team"）—— Rule 1 禁止它自己认角色
6. 对 leader 说"开始工作"，流程跑起来

> **身份澄清**：`ADMIN` 永远是你（真人，**不在 `fcop.json.roles` 里**）；
> 团队里的角色（`PM` / `ME` / `MANAGER` …）都是 AI。即便 Solo 模式下那唯一
> 一个角色也是 AI，不是你自己。

## MCP 工具清单（16 个）

**起手式**

| 工具 | 功能 |
|------|------|
| `unbound_report` | **新会话必调的第一个工具**（FCoP Rule 1）—— 输出项目客观状态，等待 ADMIN 指派身份 |

**项目初始化（三条路）**

| 工具 | 功能 |
|------|------|
| `init_solo` | Solo 模式（单 AI 角色，直接对 ADMIN） |
| `init_project` | 预设团队（`dev-team` / `media-team` / `mvp-team`） |
| `create_custom_team` | 自定义角色的团队 |
| `validate_team_config` | 落盘前干跑校验角色代码 / leader（不写文件） |
| `get_available_teams` | 查看全部模板（含 Solo + 三套预设） |

**日常协作**

| 工具 | 功能 |
|------|------|
| `get_team_status` | 当前任务/报告/问题计数 + 最近活动 |
| `list_tasks` / `read_task` / `write_task` | 任务流 |
| `inspect_task` | 校验任务文件的 schema 与文件名↔frontmatter 一致性 |
| `list_reports` / `read_report` | 报告流 |
| `list_issues` | 问题流 |
| `archive_task` | 归档已完成任务 |

**泄压阀**

| 工具 | 功能 |
|------|------|
| `drop_suggestion` | 对协议不满时的泄压阀 —— 落一份到 `.fcop/proposals/`，**不要自己改规则文件** |

## MCP 资源（URI，6 个）

| URI | 内容 |
|-----|------|
| `fcop://status` | 当前团队状态 |
| `fcop://config` | `docs/agents/fcop.json` 原文 |
| `fcop://rules` | `.cursor/rules/fcop-rules.mdc` 原文（协议规则） |
| `fcop://protocol` | `.cursor/rules/fcop-protocol.mdc` 原文（协议解释） |
| `fcop://letter/zh` | 《FCoP 致 ADMIN 的一封信》中文说明书 |
| `fcop://letter/en` | Letter to ADMIN — English user manual |

## 环境变量

| 变量 | 作用 | 默认值 |
|------|------|--------|
| `FCOP_PROJECT_DIR`  | 项目根目录（含 `docs/agents/`） | `.`（当前工作目录） |
| `FCOP_ROOM_KEY`     | 非空即启用后台线程连接中继（仅桥接模式用） | 空（本地模式） |
| `FCOP_RELAY_WS_URL` | 中继 WebSocket URL | `ws://127.0.0.1:5252` |
| `FCOP_DEVICE_ID`    | 本机 MCP 设备 ID | `fcop-mcp` |

## 文件协议速览

Agent 之间通过 Markdown 文件通信，`docs/agents/` 目录下：

```
docs/agents/
├── fcop.json          ← 项目身份配置（唯一权威源）
├── tasks/             ← 任务单（TASK-YYYYMMDD-NNN-{sender}-to-{recipient}.md）
├── reports/           ← 完成报告（同名，不同目录）
├── issues/            ← 问题记录（ISSUE-YYYYMMDD-NNN-summary.md）
├── shared/            ← 团队共享知识（DASHBOARD / SPRINT / GLOSSARY ...，允许原地更新）
└── log/               ← 历史归档
```

文件首部必须有 YAML frontmatter，至少 `protocol: fcop`、`version: 1`、`sender`、`recipient`。
详细语法见部署后的 `.cursor/rules/fcop-protocol.mdc`（协议解释），规则本身见 `.cursor/rules/fcop-rules.mdc`（协议规则）。

## License

MIT
