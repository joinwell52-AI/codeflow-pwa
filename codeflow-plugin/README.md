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

## 安装 MCP

PyPI 包名：**`fcop`**（0.2.1+）。

### 🤖 方式 0：告诉 Cursor Agent 自己装（最省事，推荐）

新电脑已经装了 Cursor？打开任意项目 → 开个 Agent 聊天 → 把下面这段**整段**发给它：

> 帮我装 `fcop` MCP。在 PowerShell（Windows）或 bash（macOS/Linux）里执行下面对应的一条命令，跑完告诉我结果，然后提醒我重启 Cursor：
>
> **Windows：**
> ```powershell
> irm https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.ps1 | iex
> ```
>
> **macOS / Linux：**
> ```bash
> curl -fsSL https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.sh | bash
> ```

Agent 会用自带的 shell 工具跑完，脚本做的事：

1. `uv` 没装就装上（Windows 走 winget，macOS/Linux 走官方脚本）
2. 创建 / 合并 `~/.cursor/mcp.json` —— **保留你原有的其他 MCP 不动**，只追加 `fcop` 一项
3. 打印"装完了，重启 Cursor"

整个流程你只输入一次那段提示词，其余交给 Agent。

### 方式 A：`uvx` 一键（手动，零配置）

前置：装 [`uv`](https://docs.astral.sh/uv/)（Windows：`winget install --id=astral-sh.uv`）。

在 Cursor 的 `mcp.json` 里加这一段（Windows 路径：`%USERPROFILE%\.cursor\mcp.json`）：

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

重启 Cursor，第一次调用时 `uvx` 会自动从 PyPI 下载 `fcop` 并跑起来，之后走缓存，不用手动升级。

### 方式 B：Cursor Deeplink 一键安装

点下面按钮，Cursor 弹窗确认即可把配置自动写进 `mcp.json`：

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-light.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=fcop&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmY29wIl19)

（等价于方式 A，只是省去手动编辑 `mcp.json`。）

### 方式 C：`pip install`（不想装 uv）

```bash
pip install fcop
```

然后 `mcp.json`：

```json
{
  "mcpServers": {
    "fcop": {
      "command": "fcop"
    }
  }
}
```

若 `fcop` 不在 PATH，把 `command` 换成 `python`，`args` 换成 `["-m", "codeflow_mcp"]`。

### 升级

- `uvx`：`uv tool upgrade fcop`（或删除 `~/.cache/uv/tools/fcop` 让它自动重拉）
- `pip`：`pip install -U fcop`

### 本地开发（改源码）

指向仓库内 shim，代码改了立即生效：

```json
{
  "mcpServers": {
    "fcop": {
      "command": "python",
      "args": ["D:\\Bridgeflow\\codeflow-plugin\\scripts\\mcp_server.py"]
    }
  }
}
```

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

## 打开本机控制面板（`http://127.0.0.1:18765/`）

想在 Cursor 内嵌一个面板视图，请使用仓库内 **`codeflow-desktop/cursor-extension/`** 下的 VSIX 扩展 `codeflow-panel-launcher`（命令：`CodeFlow: 打开控制面板` / `codeflow.openPanel`）。它走 VS Code 扩展 API，无需 Python、不模拟键盘、不抢焦点。

前置：已运行 **CodeFlow-Desktop.exe**，`127.0.0.1:18765` 可访问。

## License

MIT
