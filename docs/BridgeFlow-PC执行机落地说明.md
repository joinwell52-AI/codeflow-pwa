# BridgeFlow PC 执行机落地说明

## 定位

| 端 | 角色 | 职责 |
|----|------|------|
| **手机端** | 主控台（ADMIN01） | 发任务、看状态、看 MD、扫码绑定 |
| **PC 端** | 专用执行机 | 收任务、写文件、巡检、桥接中继 |
| **中继** | 文本转发层 | 只转文本 JSON，不落盘不执行 |

AI 团队固定 4 个角色：`PM01 / DEV01 / OPS01 / QA01`

---

## 安装

```powershell
pip install bridgeflow
```

依赖：Python 3.10+、`websockets`、`segno`（服务端 QR 生成）

---

## 初始化（bridgeflow init）

```powershell
bridgeflow init
```

生成内容：

| 内容 | 说明 |
|------|------|
| `bridgeflow_config.json` | 完整配置文件 |
| `device_id` | 本机唯一设备标识（持久化到 config） |
| `machine_code` | 绑定用机器码，格式 `BF-XXXXXXXX` |
| `.bridgeflow/runtime/` | 运行态目录 |
| `.cursor/rules/*.mdc` | 5 个角色的 Cursor 规则文件 |

支持参数：

```powershell
bridgeflow init --relay-url wss://ai.chedian.cc/bridgeflow/ws/ --room-key my-room-001
bridgeflow init --force   # 强制覆盖已有配置
```

---

## 启动（bridgeflow run）

```powershell
bridgeflow run
```

启动流程：

1. 读取 `bridgeflow_config.json`
2. 执行跨平台环境检测
3. 打印启动横幅（OS / Python / Cursor 状态 / 设备 ID / 机器码 / 中继地址）
4. 启动本地 HTTP 仪表盘（`localhost:18765`）
5. 自动打开浏览器到仪表盘
6. 连接中继 WebSocket
7. 进入事件监听循环

---

## 本地仪表盘（localhost:18765）

| 区域 | 内容 |
|------|------|
| 环境检测 | OS 类型、Python 版本、Cursor 安装/运行状态 |
| 连接状态 | 中继连接是否成功 |
| 设备信息 | device_id、machine_code、room_key |
| **二维码** | 手机扫描一键绑定 |
| 任务统计 | 今日任务数、回执数 |

**二维码内容（deep link）：**

```
bridgeflow://bind?machine_code=BF-XXXX&relay=wss://ai.chedian.cc/bridgeflow/ws/&room=bridgeflow-default&device_id=tablet-xxxx-pc
```

手机 PWA 扫码后自动解析所有连接参数，无需手动配置。

**API 接口（供仪表盘轮询）：**

| 路径 | 说明 |
|------|------|
| `GET /` | 仪表盘 HTML 页面 |
| `GET /api/status` | JSON 格式当前状态 |
| `GET /api/qr` | PNG 格式二维码图片 |

---

## 跨平台环境检测（env_check.py）

`bridgeflow run` 启动时自动检测：

### Windows
- Python 版本（需 3.10+）
- 通过 `tasklist` 检测 Cursor 进程（`Cursor.exe`）
- 通过 **Windows 注册表**（`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`）查找 Cursor 安装路径
- 备用路径检测：`%LOCALAPPDATA%\Programs\cursor\`、`%APPDATA%\Cursor\`

### macOS
- 检测 `/Applications/Cursor.app`
- `pgrep -x Cursor` 检测运行状态

### Linux
- `shutil.which("cursor")` 检测可执行文件
- `pgrep -x cursor` 检测运行状态

---

## 配置文件结构

`bridgeflow_config.json` 关键字段：

```json
{
  "device": {
    "device_id": "tablet-nv7l92kq-pc",
    "machine_code": "BF-32A1CE709907",
    "device_name": "BridgeFlow PC"
  },
  "relay": {
    "url": "wss://ai.chedian.cc/bridgeflow/ws/",
    "room_key": "bridgeflow-default"
  },
  "bind": {
    "status": "unbound",
    "pending_bind_code": "",
    "pending_bind_expires_at": "",
    "pending_mobile_device_id": "",
    "bind_code_ttl_seconds": 300
  },
  "ai_team": {
    "fixed_roles": ["PM01", "DEV01", "OPS01", "QA01"]
  },
  "project": {
    "root_dir": ".",
    "tasks_dir": "docs/agents/tasks",
    "reports_dir": "docs/agents/reports",
    "issues_dir": "docs/agents/issues"
  },
  "runtime": {
    "status_dir": ".bridgeflow/runtime/status",
    "task_details_dir": ".bridgeflow/runtime/task_details"
  }
}
```

---

## 运行态目录

```text
.bridgeflow/runtime/
├── status/
│   ├── device_status.json    # 设备身份 + 绑定状态 + Cursor 探测 + 推断状态
│   ├── task_index.json       # 最近任务/回执索引
│   ├── last_activity.json    # 最近活动时间
│   └── heartbeat.json        # 心跳时间戳
└── task_details/
    └── {task_id}.json        # 单任务完整详情（含 body / messages / markdown）
```

---

## 设备状态推断规则

| 条件 | 推断状态 |
|------|---------|
| 未发现 `Cursor.exe` | 未启动 |
| Cursor 在前台 + 最近有任务活动 | 执行中 |
| Cursor 不在前台 + 最近有任务活动 | 忙碌中 |
| 有待处理任务 | 等待中 |
| Cursor 在前台 + 近期无新活动 | 待命中 |
| 其他 | 空闲 |

---

## 绑定机制

### 扫码绑定（推荐）

1. PC 仪表盘显示 QR 码（`/api/qr`）
2. 手机 PWA 扫描 QR 码，解析 deep link
3. 手机通过中继发送 `request_bind_code` 事件
4. PC 收到后生成绑定码，经中继回传 `bind_state`
5. PC 端执行 `bridgeflow approve-bind` 确认

### 绑定码手动绑定（备用）

```powershell
# PC 生成绑定码
bridgeflow bind-code
# 输出：绑定码 A1B2C3，有效期 300 秒

# 手机端"我的"页面手动输入绑定码

# PC 确认
bridgeflow approve-bind --code A1B2C3 --mobile-device-id MOBILE-XXXX --mobile-device-name "我的手机"
```

---

## 中继事件

### PC 端监听

| 事件 | 含义 |
|------|------|
| `command_from_admin` | 手机发来任务文本，PC 写 `TASK-*.md` |
| `request_dashboard` | 手机拉取状态，PC 返回 `dashboard_state` |
| `request_task_detail` | 手机拉取任务详情，PC 返回 `task_detail` |
| `request_bind_state` | 手机查询绑定状态，PC 返回 `bind_state` |
| `request_bind_code` | 手机申请绑定，PC 生成绑定码返回 `bind_state` |
| `approve_bind` | PC 确认绑定 |
| `unbind_device` | 解除绑定 |
| `execute_desktop_action` | 手机触发桌面动作，PC 执行后返回 `desktop_action_result` |

---

## 桌面动作

| 动作 | 说明 |
|------|------|
| `focus_cursor` | 定位并切换到 Cursor 窗口 |
| `inspect` | 向 Cursor 发送"巡检"文本 |
| `start_work` | 向 Cursor 发送"开工"文本 |

支持 `--dry-run` 参数，只预演不实际操作。

---

## 完整命令速查

```powershell
# 初始化
bridgeflow init
bridgeflow init --relay-url wss://ai.chedian.cc/bridgeflow/ws/ --room-key my-room
bridgeflow init --force

# 运行
bridgeflow run
bridgeflow run --config .\bridgeflow_config.json

# 任务文件
bridgeflow write-admin-task --text "请 PM 安排下一步"
bridgeflow write-reply --sender PM01 --text "已接单" --thread-key "xxx"

# 绑定
bridgeflow bind-status
bridgeflow bind-code
bridgeflow approve-bind --code A1B2 --mobile-device-id MOBILE-XXX --mobile-device-name "我的手机"
bridgeflow unbind

# 桌面动作
bridgeflow desktop-action --action focus_cursor
bridgeflow desktop-action --action inspect --dry-run
bridgeflow desktop-action --action start_work
```
