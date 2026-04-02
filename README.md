# BridgeFlow

`BridgeFlow` 是一套面向多 AI 角色团队的**人机协作桥接工具**。

手机是主控台，PC 是执行机，中继是文本传输层。  
每一条消息都落成标准任务文件，不形成第二套聊天协议。

---

## 产品架构

```
手机端 PWA                  中继（WebSocket）          PC 执行机
────────────                ──────────────────         ──────────────────
发送任务文本       ──────>  wss://ai.chedian.cc  <──── bridgeflow run
查看任务清单                /bridgeflow/ws/            写 TASK-*.md
查看回复摘要       <──────  转发 JSON 事件      ──────> 扫描回执推送
扫码绑定 PC                                            Cursor 窗口控制
```

---

## 快速开始（PC 端）

```powershell
# 1. 安装
pip install bridgeflow

# 2. 初始化（生成配置 + 复制 Cursor 规则文件）
bridgeflow init

# 3. 启动（自动打开浏览器仪表盘 localhost:18765）
bridgeflow run
```

浏览器仪表盘包含：
- 环境检测（OS / Python / Cursor 安装状态）
- 连接状态（中继连接是否成功）
- **二维码**（手机扫码一键绑定）

---

## 手机端 PWA

**访问地址：** https://joinwell52-ai.github.io/bridgeflow-pwa/

页面布局（v1.6.0）：

```
┌──────────────────────────┐  ← 固定顶部 Header
│ [logo] BridgeFlow  [●][我的] │
├──────────────────────────┤
│  [今日任务] [今日回复]    │  ← 看板（4个快捷按钮）
│  [进行中]  [已完成]       │
├──────────────────────────┤  ↑ 以下整体可上下滚动
│  [PM] [DEV] [OPS] [QA]   │  ← 团队（点击切换任务列表）
├──────────────────────────┤
│  任务清单                │  ← 点任务展开详情+MD记录
├──────────────────────────┤
│  发送任务区              │  ← 人员/输入/级别/发送
└──────────────────────────┘
"我的" → 点顶部右角按钮 → 独立全屏页
```

---

## 目录结构

```text
BridgeFlow/
├── pyproject.toml               # Python 包配置（当前版本 0.1.8）
├── README.md                    # 本文件
│
├── src/bridgeflow/              # Python 包源码
│   ├── cli.py                   # CLI 入口（init / run / write-* / bind-*）
│   ├── config.py                # 配置读写
│   ├── file_protocol.py         # TASK-*.md 文件协议
│   ├── task_writer.py           # 任务文件写入器
│   ├── env_check.py             # 跨平台环境检测（Win/Mac/Linux）
│   ├── relay_client/
│   │   └── ws_client.py         # WebSocket 中继客户端
│   ├── desktop/
│   │   └── runner.py            # 桌面桥接主逻辑
│   ├── dashboard/
│   │   ├── server.py            # 本地 HTTP 仪表盘（localhost:18765）
│   │   └── index.html           # 仪表盘前端页面
│   ├── models/
│   │   └── events.py            # 中继事件数据模型
│   └── data/
│       ├── bridgeflow_config.json   # 默认配置模板
│       └── rules/
│           ├── admin-human-bridge.mdc  # ADMIN01 Cursor 规则
│           ├── pm-bridge.mdc           # PM01 Cursor 规则
│           ├── dev-bridge.mdc          # DEV01 Cursor 规则
│           ├── ops-bridge.mdc          # OPS01 Cursor 规则
│           └── qa-bridge.mdc           # QA01 Cursor 规则
│
├── web/pwa/                     # 手机端 PWA 源码
│   ├── index.html               # 主页面（v1.6.0，单页 App 布局）
│   ├── config.js                # 前端配置（中继地址/房间/版本）
│   ├── sw.js                    # Service Worker（离线缓存）
│   └── manifest.json            # PWA 清单
│
├── bridgeflow-pwa/              # GitHub Pages 部署目录（git submodule）
│   └── ...                      # 与 web/pwa/ 同步后推送
│
├── docs/
│   ├── 产品设计说明.md           # 产品定位与设计原则
│   ├── 联调启动说明.md           # 本地开发联调步骤
│   ├── BridgeFlow-PC执行机落地说明.md  # PC 端能力详解
│   ├── 公网部署说明.md           # 中继公网部署（已集成到 saige-ai）
│   ├── PyPI发布说明.md          # PyPI 发布操作
│   └── agents/
│       ├── README.md            # Agent 文件结构协议
│       ├── ADMIN-01.md          # 真人角色 ADMIN01
│       ├── PM-01.md             # 项目经理角色
│       ├── DEV-01.md            # 开发工程师角色
│       ├── OPS-01.md            # 运维工程师角色
│       ├── QA-01.md             # 测试工程师角色
│       ├── tasks/               # 任务文件目录
│       ├── reports/             # 回执文件目录
│       ├── log/                 # 日志归档
│       └── issues/              # 问题记录
│
├── server/relay/
│   └── server.py                # 独立中继服务（本地联调用）
│                                # 公网已集成到 saige-ai FastAPI 后端
├── .cursor/rules/
│   └── admin-human-bridge.mdc   # 项目级 Cursor 规则
│
├── _smoke_test/                 # 烟雾测试目录
│   └── bridgeflow_config.json
│
└── scripts/
    └── deploy_public_relay.py   # 公网中继部署脚本
```

---

## 中继地址

| 环境 | 地址 |
|------|------|
| **公网正式** | `wss://ai.chedian.cc/bridgeflow/ws/` |
| 本地联调 | `ws://127.0.0.1:5252` |

中继已集成到 `saige-ai` FastAPI 后端，无需单独部署 Relay 进程。

---

## 默认配置

`bridgeflow init` 生成的 `bridgeflow_config.json` 默认使用：

```json
{
  "relay": {
    "url": "wss://ai.chedian.cc/bridgeflow/ws/",
    "room_key": "bridgeflow-default"
  }
}
```

生产环境建议把 `room_key` 改成自己的随机房间名，避免与其他用户共用同一房间。

---

## CLI 命令速查

```powershell
bridgeflow init                    # 初始化配置 + 复制 Cursor 规则文件
bridgeflow run                     # 启动桥接 + 打开本地仪表盘

bridgeflow write-admin-task --text "请 PM 安排下一步"
bridgeflow write-reply --sender PM01 --text "已接单" --thread-key "xxx"

bridgeflow bind-status             # 查看绑定状态
bridgeflow bind-code               # 生成绑定码（PC 端确认用）
bridgeflow approve-bind --code A1B2 --mobile-device-id mobile-xxx
bridgeflow unbind                  # 解除绑定

bridgeflow desktop-action --action focus_cursor
bridgeflow desktop-action --action inspect
bridgeflow desktop-action --action start_work
```

---

## 扫码绑定流程

1. PC 端运行 `bridgeflow run`，浏览器打开 `localhost:18765`
2. 仪表盘显示 QR 码（内含中继地址、房间、机器码）
3. 手机打开 PWA → 点顶部右角"我的" → 点"📷 扫码绑定 PC"
4. 对准 PC 仪表盘二维码，自动解析并发送绑定请求
5. PC 端确认（`approve-bind`），绑定完成

---

## Agent 文件协议

任务文件命名格式：

```text
TASK-YYYYMMDD-序号-发送方-to-接收方.md
```

示例：
- `TASK-20260401-001-ADMIN01-to-PM01.md`
- `TASK-20260401-002-PM01-to-ADMIN01.md`

每个文件包含标准元数据头：

```yaml
---
protocol: agent_bridge
version: 1
kind: task
sender: ADMIN01
recipient: PM01
priority: P1
thread_key: 20260401-123000-ADMIN01-to-PM01
created_at: 2026-04-01 12:30:00
---
```

---

## 核心原则

- 手机端只处理文本，不碰 Cursor 窗口
- PC 端负责桥接、巡检、文件生成
- 中继只传文本 JSON，不落盘、不执行、不传大文件
- 每条消息必须文件化，不形成第二套聊天协议
- 角色与显示名分离，支持后续 `PM/CTO` 等别名扩展

---

## 命名约定

| 名称 | 含义 |
|------|------|
| `BridgeFlow` | 应用名 |
| `agent_bridge` | 文件协作协议名 |
| `bridgeflow` | Python 包名 / CLI 命令 |
| `ADMIN01` | 真人操作角色（手机端） |
| `PM01/DEV01/OPS01/QA01` | AI 执行角色（PC 端） |
