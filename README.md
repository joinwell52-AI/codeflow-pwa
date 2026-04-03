# BridgeFlow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PWA](https://img.shields.io/badge/PWA-GitHub%20Pages-green)](https://joinwell52-ai.github.io/bridgeflow-pwa/)
[![GitHub](https://img.shields.io/badge/GitHub-joinwell52--AI-black)](https://github.com/joinwell52-AI/bridgeflow-pwa)

**BridgeFlow** 是一套面向多 AI 角色团队的**人机协作桥接工具**。

手机是主控台，PC 是执行机，中继是文本传输层。
每一条消息都落成标准任务文件（`TASK-*.md`），文件名即通信协议，不形成第二套聊天系统。

---

## 产品架构

```
手机端 PWA                    中继服务（WebSocket）             PC Desktop
──────────────                ─────────────────────────       ──────────────────
扫码绑定 PC          ──────>  wss://relay-server        <──── BridgeFlow Desktop
发送任务 / 控制巡检            转发 JSON 事件                   写 TASK-*.md
查看任务清单          <──────  双向推送                  ──────> Cursor 窗口唤醒
远程桌面操作                                                   环境预检 + 自动巡检
```

**三个独立模块：**

| 模块 | 说明 | 位置 |
|------|------|------|
| **Desktop** | PC 端 EXE（Nudger 唤醒器 + Web Panel 控制面板 + Relay Client） | `bridgeflow-nudger/` |
| **Plugin** | Cursor MCP 插件（MCP Tools + 中继桥接线程） | `bridgeflow-plugin/` |
| **PWA** | 手机端（扫码绑定 + 任务管理 + 远程控制） | `web/pwa/` |

---

## 三套预设团队

初始化时选择一套团队模板，自动生成对应的角色定义文档（中英双语）。

| 模板 | 角色 | 适合场景 |
|------|------|----------|
| **dev-team** | PM（项目经理）+ DEV（开发）+ QA（测试）+ OPS（运维） | 软件开发 |
| **media-team** | PUBLISHER（审核发行）+ COLLECTOR（素材采集）+ WRITER（拟题提纲）+ EDITOR（润色编辑） | 自媒体内容 |
| **mvp-team** | MARKETER（增长运营）+ RESEARCHER（市场调研）+ DESIGNER（产品设计）+ BUILDER（快速原型） | 创业 MVP |

选完后客户项目自动生成：

```
客户项目/
├── .cursor/
│   ├── rules/
│   │   ├── bridgeflow-core.mdc         ← 协作协议
│   │   └── bridgeflow-patrol.mdc       ← 巡检规则
│   └── skills/
│       └── file-protocol/SKILL.md      ← 文件协议技能
├── docs/agents/
│   ├── bridgeflow.json                 ← 团队配置（角色 + 房间密钥 + 中继地址）
│   ├── PM.md / PM.en.md               ← 角色定义（按所选团队）
│   ├── DEV.md / DEV.en.md
│   ├── QA.md / QA.en.md
│   ├── OPS.md / OPS.en.md
│   ├── tasks/                          ← 任务单
│   ├── reports/                        ← 完成报告
│   ├── issues/                         ← 问题记录
│   └── log/                            ← 历史归档
```

---

## 快速开始（PC Desktop）

```powershell
# 方式一：运行打包好的 EXE（推荐）
bridgeflow-nudger\dist\BridgeFlow-Desktop.exe

# 方式二：从源码运行
cd bridgeflow-nudger
pip install -r requirements.txt
python main.py
```

启动后自动打开浏览器面板 `http://127.0.0.1:18765`，包含：
- **两步设置向导**（选项目文件夹 → 选团队模板）
- **环境预检 6 项**（目录 / 结构 / 配置 / 角色文件 / Cursor / 快捷键）
- **二维码**（手机扫码一键绑定）
- **巡检控制**（启动 / 停止 / 重置）
- **任务流水线 + 文件浏览 + 实时日志**
- **中英文切换**（i18n）

---

## 手机端 PWA

**访问地址：** https://joinwell52-ai.github.io/bridgeflow-pwa/

> 用手机浏览器打开，点"添加到主屏幕"即可像 App 一样使用。

**功能（v1.9.0）：**
- 扫码绑定 / 解绑 PC
- 远程启停巡检
- 查看任务清单和回复
- 发送任务给指定角色
- 远程桌面操作（聚焦 Cursor / 检查状态 / 开始工作 / 重启）
- 实时消息记录和系统日志（离线自动停止）

---

## 文件驱动通信协议

**文件名就是通信协议**——Nudger 看到文件名就知道该唤醒谁。

```
TASK-20260403-001-PM-to-DEV.md
     ^^^^^^^^ ^^^ ^^ ^^^
     日期     序号 发件人 收件人
```

| 目录 | 内容 | 谁写 | 谁读 |
|------|------|------|------|
| `tasks/` | 任务单 | 主控 / 外部 | 收件角色 |
| `reports/` | 完成报告 | 执行角色 | 主控 |
| `issues/` | 问题记录 | 任何人 | 所有人 |
| `log/` | 历史归档 | 主控 | 只读参考 |

每个文件包含标准元数据头：

```yaml
---
task_id: TASK-20260403-001
sender: PM
recipient: DEV
created_at: 2026-04-03 10:00:00
priority: normal
type: feature
---
```

---

## 目录结构

```text
BridgeFlow/
├── README.md                        # 本文件
├── CHANGELOG.md                     # 版本历史
│
├── bridgeflow-nudger/               # 【Desktop】PC 端独立 EXE
│   ├── main.py                      # 启动入口
│   ├── nudger.py                    # Nudger 唤醒器核心
│   ├── web_panel.py                 # Web Panel HTTP 服务
│   ├── config.py                    # 配置管理
│   ├── panel/                       # 面板前端（index.html + 静态资源）
│   ├── templates/                   # 初始化模板
│   │   ├── rules/                   # Cursor 规则文件
│   │   ├── skills/                  # Cursor 技能文件
│   │   └── agents/                  # 角色定义文档（3 套团队 × 中英双语）
│   │       ├── dev-team/            #   PM / DEV / QA / OPS
│   │       ├── media-team/          #   PUBLISHER / COLLECTOR / WRITER / EDITOR
│   │       └── mvp-team/            #   MARKETER / RESEARCHER / DESIGNER / BUILDER
│   ├── build.spec                   # PyInstaller 打包配置
│   └── dist/                        # 打包输出
│
├── bridgeflow-plugin/               # 【Plugin】Cursor MCP 插件
│   ├── mcp.json                     # MCP 服务定义
│   ├── commands/                    # MCP Tools 实现
│   ├── agents/                      # 角色定义源（3 套团队）
│   ├── templates/                   # 团队 README 模板
│   ├── rules/                       # Cursor 规则文件
│   └── skills/                      # Cursor 技能文件
│
├── web/pwa/                         # 【PWA】手机端
│   ├── index.html                   # 主页面（v1.9.0）
│   ├── config.js                    # 配置（中继地址 / 房间 / 版本）
│   ├── sw.js                        # Service Worker（离线缓存）
│   └── manifest.json                # PWA 清单
│
├── server/relay/
│   └── server.py                    # WebSocket 中继服务
│
├── docs/                            # 公开文档
│   ├── user-manual.md / .en.md      # 用户操作手册（中 / 英）
│   ├── config-reference.md / .en.md # 配置参数字典（中 / 英）
│   └── agents/                      # 角色定义 + 任务协作目录
│       ├── README.md / .en.md       # Agent 文件结构说明
│       ├── ADMIN-01.md / .en.md     # 管理员角色
│       ├── PM-01.md / .en.md        # 项目经理
│       ├── DEV-01.md / .en.md       # 开发工程师
│       ├── QA-01.md / .en.md        # 测试工程师
│       ├── OPS-01.md / .en.md       # 运维工程师
│       ├── tasks/ reports/ issues/ log/
│       └── bridgeflow.json          # 团队配置
│
├── .cursor/rules/                   # 本仓库的 Cursor 规则
│   ├── bridgeflow-project.en.mdc    # 项目总规范（英文）
│   ├── admin-human-bridge.en.mdc    # 管理员桥接规则
│   ├── pm-bridge.mdc / .en.mdc      # PM 巡检规则
│   ├── dev-bridge.mdc / .en.mdc     # DEV 巡检规则
│   ├── qa-bridge.mdc / .en.mdc      # QA 巡检规则
│   └── ops-bridge.mdc / .en.mdc     # OPS 巡检规则
│
├── .github/workflows/               # CI/CD
│   ├── publish.yml                  # tag → PyPI 发布
│   └── deploy-pwa.yml               # main push → GitHub Pages 部署
│
└── private/                         # 内部文档（不公开）
```

---

## 中继服务

| 环境 | 地址 |
|------|------|
| 本地联调 | `ws://127.0.0.1:5252`（运行 `server/relay/server.py`） |
| 自部署 | `wss://your-relay-server/bridgeflow/ws/` |

中继为轻量 WebSocket 服务，只转发 JSON 文本，不落盘、不执行、不传大文件。

---

## 核心原则

- **文件名即协议** — `TASK-日期-序号-发件人-to-收件人.md`，Nudger 看文件名就唤醒对应角色
- **手机只发文本** — 不碰 Cursor 窗口，不执行代码
- **PC 负责执行** — 桥接、巡检、文件生成、Cursor 窗口控制
- **中继只传 JSON** — 不落盘、不执行、不传大文件
- **角色可扩展** — 3 套预设 + 自定义角色，代码与显示名分离

---

## 版权

© 2026 joinwell52-AI · Non-commercial use only · From real production experience

- 源码：[github.com/joinwell52-AI/bridgeflow-pwa](https://github.com/joinwell52-AI/bridgeflow-pwa)
- 版本历史：[CHANGELOG.md](CHANGELOG.md)
- 用户手册：[docs/user-manual.md](docs/user-manual.md)
- 配置参考：[docs/config-reference.md](docs/config-reference.md)
