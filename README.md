# 码流（CodeFlow）

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PWA](https://img.shields.io/badge/PWA-GitHub%20Pages-green)](https://joinwell52-ai.github.io/codeflow-pwa/)
[![GitHub](https://img.shields.io/badge/GitHub-codeflow--pwa-black)](https://github.com/joinwell52-AI/codeflow-pwa)

本仓库在 GitHub 上为 **`joinwell52-AI/codeflow-pwa`**（曾用仓库名 `CodeFlow-pwa`，已重命名；克隆地址请用当前名）。**GitHub Pages：** [joinwell52-ai.github.io/codeflow-pwa](https://joinwell52-ai.github.io/codeflow-pwa/)。版本与变更见 [CHANGELOG.md](CHANGELOG.md)。

### GitHub 网页「About」设置（复制即用）

在仓库页右侧 **About** 点 **⚙**，或 **Settings → General**：

| 项 | 填写内容 |
|----|----------|
| **Description** | `CodeFlow / 码流 — Multi-agent collaboration via file-driven TASK protocol; mobile PWA + PC desktop.` |
| **Website** | `https://joinwell52-ai.github.io/codeflow-pwa/` |
| **Topics**（可选） | `codeflow`, `pwa`, `cursor`, `mcp`, `websocket`, `multi-agent`, `collaboration`, `task-protocol` |

若希望描述以中文为主，可改用：**`码流（CodeFlow）— 文件驱动多角色协作；手机 PWA + PC 桌面端，TASK 文件名即协议。`**（与上表二选一即可。）

更细的步骤与备用英文句见 **[docs/github-repo-about.md](docs/github-repo-about.md)**。

**多人协作 / 分支约定**（**只使用 `main` 作为主分支**）：见 **[docs/repo-collaboration.md](docs/repo-collaboration.md)**。

**码流（CodeFlow）**——AI 驱动的人机协作中枢，用手机轻松驾驭 AI，让指令高效流转、直达团队。

- **主标语**：指令成流，智能随行  
- **副标语**：手机驭 AI，指令达团队  

手机是主控台，PC 是执行机（**码流 Desktop**），中继是文本传输层。每一条消息都落成标准任务文件（`TASK-*.md`），文件名即通信协议，不形成第二套聊天系统。

---

## 产品架构

```
手机端 PWA                    中继服务（WebSocket）             PC Desktop（码流）
──────────────                ─────────────────────────       ──────────────────
扫码绑定 PC          ──────>  wss://relay-server        <──── CodeFlow Desktop
发送任务 / 控制巡检            转发 JSON 事件                   写 TASK-*.md
查看任务清单          <──────  双向推送                  ──────> Cursor 窗口唤醒
远程桌面操作                                                   环境预检 + 自动巡检
```

**三个独立模块：**

| 模块 | 说明 | 位置 |
|------|------|------|
| **Desktop** | PC 端 EXE（Nudger 唤醒器 + Web Panel + Relay Client） | `codeflow-desktop/` |
| **Plugin** | Cursor MCP 插件（MCP Tools + 可选中继桥接） | `codeflow-plugin/` |
| **PWA** | 手机端（扫码绑定 + 任务管理 + 远程控制） | `web/pwa/`（**主源**；根目录同名文件为同步副本） |

---

## 三套预设团队

初始化时选择一套团队模板，自动生成对应的角色定义文档（中英双语）。

| 模板 | 角色 | 适合场景 |
|------|------|----------|
| **dev-team** | PM + DEV + QA + OPS | 软件开发 |
| **media-team** | PUBLISHER + COLLECTOR + WRITER + EDITOR | 自媒体内容 |
| **mvp-team** | MARKETER + RESEARCHER + DESIGNER + BUILDER | 创业 MVP |

选完后客户项目自动生成（规则文件名以模板为准；新项目可为 `codeflow-*.mdc`，旧项目可能仍为 `CodeFlow-*.mdc`）：

```
客户项目/
├── .cursor/
│   ├── rules/          ← 协作协议 + 巡检规则（.mdc）
│   └── skills/file-protocol/SKILL.md
├── docs/agents/
│   ├── codeflow.json   ← 团队配置（兼容旧名 CodeFlow.json）
│   ├── PM.md / PM.en.md
│   ├── tasks/ reports/ issues/ log/
```

---

## 快速开始（PC Desktop）

```powershell
# 方式一：运行打包好的 EXE（推荐）
codeflow-desktop\dist\CodeFlow-Desktop.exe

# 方式二：从源码运行（建议 Python 3.12）
cd codeflow-desktop
pip install -r requirements.txt
python main.py
```

可选：在项目根放置 **`codeflow-nudger.json`** 微调巡检（兼容旧名 `codeflow-nudger.json`），与 `main.py` 自动加载。

`use_file_watcher: true` 时需已 `pip install watchdog`。

启动后自动打开浏览器面板 `http://127.0.0.1:18765`（**码流（CodeFlow）控制面板**）。

- **桌面端版本**：当前 **v2.9.44**，见 **`CHANGELOG.md`**。支持自动更新（GitHub + Gitee 双线路智能下载）。

**下载地址：**
- 国内（推荐）：https://gitee.com/joinwell52/cursor-ai/releases
- GitHub：https://github.com/joinwell52-AI/codeflow-pwa/releases

---

## 手机端 PWA

**主源目录：** `web/pwa/`（`config.js` / `index.html` / `sw.js` / `manifest.json`）。

**GitHub Pages：** https://joinwell52-ai.github.io/codeflow-pwa/（由独立仓库 `joinwell52-AI/codeflow-pwa` 托管，原名 `bridgeflow-pwa`，已改名）

添加到主屏幕后，安装名显示为 **码流**，全名为 **码流（CodeFlow）工作台**。

**能力概览：**
- 扫码绑定 / 解绑 PC  
- 远程启停巡检  
- 任务清单（分类：任务单 / 报告 / 问题 / 归档）  
- 任务 MD 原文查看  
- 团队角色动态同步（从 PC `codeflow.json` 读取，支持 MVP/媒体等多种团队）  
- 团队名显示、角色卡片缩写  
- 发送任务给指定角色  
- 巡检轨迹实时展示  
- 远程桌面操作（聚焦 Cursor / 查看状态 / 开始工作）  
- 与桌面端、中继事件协议一致（`room_key` + JSON 事件）  

### PWA 发布流程

```
# 1. 修改 web/pwa/ 里的文件
# 2. 升级版本号
#    web/pwa/config.js  → appVersion
#    web/pwa/sw.js      → build 注释行（// build: YYYYMMDD-x.x.x）
# 3. 运行发布脚本
py -3 _deploy_pwa.py
```

> Token 存放在 `.github_token`（已列入 `.gitignore`，不进 git）。  
> `codeflow-pwa` 仓库只存 PWA 的 5 个文件，不含主仓库代码。

---

## 文件驱动通信协议

**文件名就是通信协议**——Nudger 看到文件名就知道该唤醒谁。

```
TASK-20260403-001-PM-to-DEV.md
```

| 目录 | 内容 |
|------|------|
| `tasks/` | 任务单 |
| `reports/` | 完成报告 |
| `issues/` | 问题记录 |
| `log/` | 历史归档 |

---

## 目录结构（节选）

```text
D:\\CodeFlow\\                          # 仓库根（文件夹名可仍为 CodeFlow）
├── README.md
├── CHANGELOG.md
├── index.html / config.js / sw.js / manifest.json   # 与 web/pwa 同步的静态副本
├── codeflow-desktop/                   # PC Desktop 源码与打包
├── codeflow-plugin/                    # Cursor MCP 插件
├── web/pwa/                            # PWA 【主源】
├── server/relay/server.py              # 本地联调中继
└── docs/                               # 文档
```

---

## 中继服务

| 环境 | 说明 |
|------|------|
| 本地联调 | `ws://127.0.0.1:5252`（`python server/relay/server.py`） |
| 公网 / 自部署 | 网关需将路径 **`/codeflow/ws/`** 转到中继进程（与 PWA、Desktop 默认 `relayUrl` 一致） |

中继只转发 JSON 文本，单条消息限制 256KB（`MAX_MESSAGE_BYTES`），WebSocket 传输帧限制 512KB（`TRANSPORT_MAX_BYTES`）。

---

## 巡检器自愈能力

| 场景 | 动作 |
|---|---|
| Cursor Connection Error | 自动 Reload Window |
| Extension Host 卡死 | 自动 Reload Window |
| Agent 任务超时卡住 | Reload Window + 催促消息 |
| Agent 等待确认 | 自动发送"继续"指令 |
| WebSocket 断连 | 自动重连（指数退避） |

---

## 核心原则

- **文件名即协议** — `TASK-...-发件人-to-收件人.md`  
- **手机只发文本与指令** — 不替代桌面端执行环境  
- **PC 负责执行** — 桥接、巡检、文件、Cursor 侧唤醒  
- **中继只传 JSON** — 单条限 256KB  

---

## 版权

© 2026 joinwell52-AI · Non-commercial use only · From real production experience

- PWA 仓库：[github.com/joinwell52-AI/codeflow-pwa](https://github.com/joinwell52-AI/codeflow-pwa)  
- 版本历史：[CHANGELOG.md](CHANGELOG.md)  
