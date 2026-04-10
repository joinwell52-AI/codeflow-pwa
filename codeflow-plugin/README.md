# 码流（CodeFlow）— Multi-AI Agent Collaboration Plugin

让多个 Cursor Agent 像团队一样协作。

## 这是什么？

**码流（CodeFlow）** 是一个 Cursor 插件，解决一个核心问题：**Cursor 里开多个 Agent，它们各干各的，互相不知道对方在干什么。**

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
# 克隆本仓库后，将插件目录链到 Cursor 插件目录（示例）
# Windows
mklink /D "%USERPROFILE%\.cursor\plugins\local\codeflow" "D:\\CodeFlow\\codeflow-plugin"
# macOS/Linux
ln -s /path/to/codeflow-plugin ~/.cursor/plugins/local/codeflow
```

重启 Cursor 即可。`mcp.json` 中 **`args`** 请指向本机 **`codeflow-plugin\scripts\mcp_server.py`** 的绝对路径。

### Marketplace 安装

搜索 **CodeFlow** 或 **码流**（审核通过后可用）。

## 快速开始

1. 安装插件  
2. 打开项目，在 Agent 中说：`初始化码流开发团队`（或按 MCP 工具说明调用 `init_project`）  
3. 插件自动创建 `docs/agents/` 目录和角色配置  
4. 开多个 Agent 窗口，每个分配一个角色  
5. 对主控角色说「开始工作」  

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

团队配置优先写入 **`docs/agents/codeflow.json`**（兼容旧版 **`CodeFlow.json`**）。

## 中继桥接（Phase 2）

未设置 `CODEFLOW_ROOM_KEY`（或旧名 `CODEFLOW_ROOM_KEY`）时，MCP 仅操作本地 `docs/agents/`，不连中继。

要与手机端 PWA 同步，请在 MCP 配置的 `env` 中设置：

| 变量 | 说明 |
|------|------|
| `CODEFLOW_PROJECT_DIR` 或 `CODEFLOW_PROJECT_DIR` | 项目根目录（含 `docs/agents/`） |
| `CODEFLOW_ROOM_KEY` 或 `CODEFLOW_ROOM_KEY` | 非空即启用后台线程连接中继 |
| `CODEFLOW_RELAY_WS_URL` 或 `CODEFLOW_RELAY_WS_URL` | 中继 WebSocket，默认 `ws://127.0.0.1:5252` |
| `CODEFLOW_DEVICE_ID` 或 `CODEFLOW_DEVICE_ID` | 本机 MCP 设备 ID，默认 `codeflow-mcp` |

依赖：`pip install -r codeflow-plugin/requirements.txt`（含 `websockets`）。

## 可选：轻量 MCP「只打开本机控制面板」（`http://127.0.0.1:18765/`）

与主服务 `scripts/mcp_server.py` **分开** 的独立脚本：`scripts/codeflow_mcp.py`。  
**实现原理**：MCP 工具被调用后，用 **pyautogui** 激活标题含 `Cursor` 的窗口 → **Ctrl+Shift+P**（macOS 为 **⌘⇧P**）→ 输入 `Simple Browser` → 回车 → 输入面板 URL → 回车。与你在聊天里手动操作一致，**不依赖**未文档化的 ACP JSON-RPC 端口。

**依赖**（单独安装即可）：

```bash
cd codeflow-plugin
pip install -r requirements-codeflow-mcp.txt
```

**Cursor `mcp.json` 示例**（`args` 改为本机绝对路径）：

```json
{
  "mcpServers": {
    "codeflow-panel": {
      "command": "python",
      "args": ["D:/CodeFlow/codeflow-plugin/scripts/codeflow_mcp.py"],
      "env": {}
    }
  }
}
```

保存后重启 Cursor。Agent 中可描述「打开 CodeFlow 面板」「刷新 CodeFlow 面板」等，对应工具名：`open_codeflow_panel`、`refresh_codeflow_panel`。

**注意**：须先运行 **CodeFlow-Desktop.exe**，保证 `127.0.0.1:18765` 已监听；命令面板语言为英文时，`Simple Browser` 命令名与 Cursor 内置一致。若焦点被其它窗口抢走，请先手动点一下 Cursor 再试。

## License

MIT
