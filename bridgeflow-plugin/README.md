# BridgeFlow — Multi-AI Agent Collaboration Plugin

让多个 Cursor Agent 像团队一样协作。

## 这是什么？

BridgeFlow 是一个 Cursor 插件，解决一个核心问题：**Cursor 里开多个 Agent，它们各干各的，互相不知道对方在干什么。**

安装插件后，Agent 自动获得：
- 角色身份（知道自己是谁）
- 协作协议（知道怎么交接任务）
- 自动巡检（知道去哪接任务）

## 三套预设团队

| 模板 | 角色 | 适合场景 |
|------|------|----------|
| **dev-team** | PM + DEV + QA + OPS | 软件开发 |
| **media-team** | PUBLISHER + COLLECTOR + WRITER + EDITOR | 自媒体内容 |
| **mvp-team** | MARKETER + RESEARCHER + DESIGNER + BUILDER | 创业 MVP |

## 安装

### 本地安装（开发测试）

```bash
# 克隆到 Cursor 插件目录
git clone https://github.com/joinwell52/BridgeFlow.git
# Windows
mklink /D "%USERPROFILE%\.cursor\plugins\local\bridgeflow" "path\to\bridgeflow-plugin"
# macOS/Linux
ln -s /path/to/bridgeflow-plugin ~/.cursor/plugins/local/bridgeflow
```

重启 Cursor 即可。

### Marketplace 安装

搜索 "BridgeFlow"，一键安装。（审核通过后可用）

## 快速开始

1. 安装插件
2. 打开项目，在 Agent 中说：`初始化 BridgeFlow 开发团队`
3. 插件自动创建 `docs/agents/` 目录和角色配置
4. 开 4 个 Agent 窗口，每个分配一个角色
5. 对主控角色说"开始工作"

## MCP Tools

| 工具 | 功能 |
|------|------|
| `init_project` | 初始化项目协作空间 |
| `get_team_status` | 查看团队状态 |
| `list_tasks` | 列出任务 |
| `read_task` | 读取任务详情 |
| `write_task` | 创建新任务 |
| `list_reports` | 列出报告 |
| `read_report` | 读取报告详情 |
| `list_issues` | 列出问题 |
| `archive_task` | 归档已完成任务 |
| `get_available_teams` | 查看可用团队模板 |

## 文件协议

Agent 之间通过 Markdown 文件通信：

```
docs/agents/
├── tasks/     ← 任务单
├── reports/   ← 完成报告
├── issues/    ← 问题记录
└── log/       ← 历史归档
```

文件名编码了发件人和收件人：
`TASK-20260403-001-PM-to-DEV.md`

## 中继桥接（Phase 2）

未设置 `BRIDGEFLOW_ROOM_KEY` 时，MCP 仅操作本地 `docs/agents/`，不连中继。

要与手机端 PWA 同步，请在 MCP 配置（如 `~/.cursor/mcp.json`）的 `env` 中设置：

| 变量 | 说明 |
|------|------|
| `BRIDGEFLOW_PROJECT_DIR` | 项目根目录（含 `docs/agents/`），建议设为当前工作区绝对路径 |
| `BRIDGEFLOW_ROOM_KEY` | 非空即启用后台线程：连接中继、轮询 `docs/agents/**/*.md`、推送 `file_change` |
| `BRIDGEFLOW_RELAY_WS_URL` | 中继 WebSocket，默认 `ws://127.0.0.1:5252` |
| `BRIDGEFLOW_DEVICE_ID` | 本机 MCP 设备 ID（手机端 `command_from_admin` 定向投递用），默认 `bridgeflow-mcp` |
| `BRIDGEFLOW_RELAY_POLL_SEC` | 文件轮询间隔（秒），默认 `2` |

本地联调中继：`python server/relay/server.py`（仓库根目录，需已安装 `websockets`）。

手机指令经中继投递到 MCP 时，正文写入 `docs/agents/inbox/admin-*.md`。

依赖：`pip install -r bridgeflow-plugin/requirements.txt`（含 `websockets`）。

## License

MIT
