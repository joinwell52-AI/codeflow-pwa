# 码流（CodeFlow）配置参考

**适用版本**：Desktop v2.8.75 / PWA v2.0.3  
**最后更新**：2026-04-10

---

## 一、配置文件总览

| 文件 | 位置 | 作用 | 修改后生效方式 |
|------|------|------|----------------|
| `codeflow-nudger.json` | 项目根目录 | PC 巡检器全部高级参数 | 重启 CodeFlow Desktop |
| `{项目}/.codeflow/config.json` | 项目内隐藏目录 | 项目级：room_key / relay_url | 重启 Desktop |
| `%APPDATA%\CodeFlow\config.json` | Windows 全局 | cursor_exe_path（跨项目）| 重启 Desktop |
| `web/pwa/config.js` | PWA 源码 | 手机端中继地址、版本号 | 重新部署 PWA |
| 环境变量 | 系统/Shell | 中继服务器监听地址和端口 | 重启中继服务 |

> `codeflow-nudger.json` 也兼容旧名 `bridgeflow-nudger.json`，两者同时存在时优先读新名。

---

## 二、PC 端巡检器（`codeflow-nudger.json`）

放在**项目根目录**（与 `docs/` 同级），不存在则全部使用默认值。

### 完整示例

```json
{
  "relay_url": "wss://ai.chedian.cc/codeflow/ws/",
  "room_key": "your-private-room-key",
  "lang": "zh",

  "hotkeys": {
    "PM":        ["ctrl", "alt", "1"],
    "DEV":       ["ctrl", "alt", "2"],
    "QA":        ["ctrl", "alt", "3"],
    "OPS":       ["ctrl", "alt", "4"]
  },

  "poll_interval": 5,
  "nudge_cooldown": 15,
  "idle_check_every_n": 6,
  "stuck_check_every_n": 30,

  "task_stuck_threshold_s": 600,
  "task_timeout_threshold_s": 1200,
  "auto_nudge_interval_s": 300,

  "patrol_ping_zh": "",
  "patrol_ping_en": "",

  "stuck_reload_window": true,
  "stuck_reload_min_age_s": 600,
  "stuck_reload_once_per_task": true,
  "reload_window_wait_s": 12,

  "use_file_watcher": true,

  "open_panel_in_cursor": true,
  "launch_cursor_if_absent": true,
  "cursor_exe_path": "",

  "auto_snap_on_launch": true,
  "input_offset": [0.80, 55]
}
```

---

### 2.1 连接参数

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `relay_url` | string | `"wss://ai.chedian.cc/codeflow/ws/"` | WebSocket 中继地址，必须与手机端一致 |
| `room_key` | string | `""` | 房间隔离 Key，PC 与手机**必须完全相同**才能互通；建议每团队设唯一随机字符串 |
| `lang` | string | `"zh"` | 催办消息语言：`"zh"` 或 `"en"` |

---

### 2.2 Agent 快捷键（`hotkeys`）

```json
"hotkeys": {
  "PM":        ["ctrl", "alt", "1"],
  "DEV":       ["ctrl", "alt", "2"],
  "QA":        ["ctrl", "alt", "3"],
  "OPS":       ["ctrl", "alt", "4"]
}
```

- **key**：角色名（大写），支持所有团队角色：`PM` / `DEV` / `QA` / `OPS` / `E2E` / `PUBLISHER` / `WRITER` / `EDITOR` / `COLLECTOR` / `BUILDER` / `DESIGNER` / `MARKETER` / `RESEARCHER`
- **value**：Cursor `keybindings.json` 里配置的 `aichat` 快捷键对应按键数组
- 必须与 Cursor 实际快捷键绑定一一对应，否则预检不通过

**自媒体团队示例：**
```json
"hotkeys": {
  "PUBLISHER": ["ctrl", "alt", "1"],
  "WRITER":    ["ctrl", "alt", "2"],
  "EDITOR":    ["ctrl", "alt", "3"],
  "COLLECTOR": ["ctrl", "alt", "4"]
}
```

---

### 2.3 巡检时间节奏

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `poll_interval` | `5`（秒）| 主循环扫描间隔 |
| `nudge_cooldown` | `15`（秒）| 同一收件人发完一条后的冷却时间，防止连发 |
| `idle_check_every_n` | `6`（轮）| 每 N 轮主循环检测一次 idle → 约 30s 一次 |
| `stuck_check_every_n` | `30`（轮）| 每 N 轮主循环扫描一次卡住任务 → 约 150s 一次 |

**实际频率速查：**

| 行为 | 默认间隔 | 计算方式 |
|------|----------|----------|
| 主循环扫文件 | ~5s | `poll_interval` |
| idle「继续」催促 | ~30s | `poll_interval × idle_check_every_n` |
| 卡住任务扫描 | ~150s | `poll_interval × stuck_check_every_n` |
| 同一任务两次催促 | 5 分钟 | `auto_nudge_interval_s` |
| 同收件人发完后冷却 | 15s | `nudge_cooldown` |

---

### 2.4 卡住任务判定

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `task_stuck_threshold_s` | `600`（10分钟）| `tasks/` 下任务文件自最后修改起超过此时间，视为「可能卡住」 |
| `task_timeout_threshold_s` | `1200`（20分钟）| 超过此时间升级为「超时」 |
| `auto_nudge_interval_s` | `300`（5分钟）| 同一 TASK 编号两次自动催促的最小间隔 |

---

### 2.5 催促消息文案

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `patrol_ping_zh` | `""` | 后续催促短句（中文）。空字符串使用内置默认 |
| `patrol_ping_en` | `""` | 后续催促短句（英文）。空字符串使用内置默认 |

**内置默认文案：**
```
中文：【码流巡检】巡检，开工。请自行查看 docs/agents/tasks/ 等待办任务。
英文：[CodeFlow] Patrol ping — proceed. Open docs/agents/tasks/ for pending items.
```

> 首次打招呼（`first_hello`）固定包含角色文件路径，不受此配置影响。

---

### 2.6 卡住时自动 Reload Window

当任务长时间未闭环时，先执行 `Developer: Reload Window` 恢复可能卡死的 Cursor UI，再发催促短句。

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `stuck_reload_window` | `true` | 是否启用卡住时自动 Reload Window |
| `stuck_reload_min_age_s` | `600`（秒）| 触发 Reload 的任务最小年龄，建议与 `task_stuck_threshold_s` 对齐 |
| `stuck_reload_once_per_task` | `true` | 每个 TASK 编号仅 Reload 一次，避免反复刷窗口 |
| `reload_window_wait_s` | `12`（秒）| Reload 后等待 Cursor 就绪再发催促的时间 |

---

### 2.7 文件监听

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `use_file_watcher` | `true` | 使用 `watchdog` 监听目录 `.md` 变更并打断睡眠，加快响应新文件。需已安装 `watchdog` 包 |

---

### 2.8 Cursor 集成

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `open_panel_in_cursor` | `true` | 面板优先在 Cursor Simple Browser 内嵌打开（`Ctrl+Shift+B` 方式）|
| `launch_cursor_if_absent` | `true` | Cursor 未运行时自动启动 |
| `cursor_exe_path` | `""` | `Cursor.exe` 完整路径，非标准安装路径时填写 |
| `auto_snap_on_launch` | `true` | 启动后自动 Windows 左右分屏（Cursor 左，面板右）|
| `cursor_acp_endpoint` | `""` | （实验性）Cursor JSON-RPC 端点，配置后优先用 ACP 打开面板 |
| `cursor_acp_layout` | `"split-right"` | ACP 分屏布局 |
| `cursor_acp_width_ratio` | `0.35` | ACP 分屏宽度比例 |

---

### 2.9 输入框偏移

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `input_offset` | `[0.80, 55]` | Agent 输入框位置微调：`[x 比例, y 偏移 px]`。OCR 找不到输入框时的 fallback 估算位置 |

---

## 三、手机端 PWA（`web/pwa/config.js`）

修改后需重新部署才能生效（`py -3 _deploy_pwa.py`）。

### 完整示例

```js
global.CODEFLOW_CONFIG = {
  appName:         "码流（CodeFlow）",
  appNameShort:    "码流 CodeFlow",
  appTagline:      "指令成流，智能随行",
  appTaglineEn:    "Commands Flow, Intelligence Follows.",
  appVersion:      "2.0.3",
  relayUrl:        "wss://ai.chedian.cc/codeflow/ws/",
  relayLabel:      "公网正式中继",
  roomKey:         "codeflow-default",
  autoConnect:     true,
  defaultTarget:   "PM"
};
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `appVersion` | string | `"2.0.3"` | **每次改动任何 PWA 文件必须递增**，否则 Service Worker 缓存不刷新，用户看到旧版 |
| `relayUrl` | string | `"wss://ai.chedian.cc/codeflow/ws/"` | 中继地址，必须与 PC 端 `relay_url` 完全一致 |
| `relayLabel` | string | `"公网正式中继"` | 显示在连接状态栏的标签，仅用于界面展示 |
| `roomKey` | string | `"codeflow-default"` | 默认房间 Key；用户扫码或在设置页手动修改后，存入 `localStorage` 覆盖此值 |
| `autoConnect` | boolean | `true` | 打开 PWA 时自动连接中继 |
| `defaultTarget` | string | `"PM"` | 发消息框默认收件人角色代码 |
| `appName` 等 | string | 见示例 | 品牌文案，仅影响界面显示，不影响功能 |

### 用户可在 PWA 内直接修改的配置（存 localStorage）

- **房间 Key**：扫码绑定或设置页手动输入，优先级高于 `config.js`
- **中继地址**：设置页修改，优先级高于 `config.js`

---

## 四、中继服务器（自建）

通过**环境变量**配置，无配置文件。

```bash
# 监听地址（默认 0.0.0.0，监听所有网卡）
export CODEFLOW_RELAY_HOST=0.0.0.0

# 监听端口（默认 5252）
export CODEFLOW_RELAY_PORT=5252

# 启动
python server/relay/server.py
```

### 内置限制（需修改源码才能调整）

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 单条消息大小 | **8 KB** | 超过则丢弃，禁止在中继传大文件正文 |
| 传输层帧上限 | 16 KB | WebSocket 帧最大长度 |
| 频率限制 | 20 条 / 10s | 超速断开连接 |
| room_key 最大长度 | 64 字符 | |

---

## 五、配置优先级

```
用户 localStorage（PWA 设置页）
    ↓ 覆盖
web/pwa/config.js（PWA 默认值）

────────────────────────────────
{项目}/.codeflow/config.json    ← 向导保存的 room_key / relay_url
    ↓ 覆盖
codeflow-nudger.json            ← 高级参数（hotkeys / 时间节奏 / reload 等）
    ↓ 覆盖
NudgerConfig 代码默认值（config.py）
    ↑ 兜底读取
%APPDATA%\CodeFlow\config.json  ← 全局：cursor_exe_path
```

---

## 六、常用场景速查

### 换团队（自媒体 → 开发团队）

```json
"hotkeys": {
  "PM":  ["ctrl", "alt", "1"],
  "DEV": ["ctrl", "alt", "2"],
  "QA":  ["ctrl", "alt", "3"],
  "OPS": ["ctrl", "alt", "4"]
}
```

### 换自建中继

`codeflow-nudger.json`：
```json
"relay_url": "wss://your-server.com/codeflow/ws/"
```
`web/pwa/config.js`：
```js
relayUrl: "wss://your-server.com/codeflow/ws/"
```
两处必须同步，且 `room_key` 也要相同。

### 调快响应速度（任务催促更及时）

```json
"task_stuck_threshold_s": 300,
"auto_nudge_interval_s": 120,
"stuck_check_every_n": 15
```

### 关闭 Reload Window（不想自动刷新）

```json
"stuck_reload_window": false
```

### 自定义催促短句

```json
"patrol_ping_zh": "【巡检】继续执行，查看 docs/agents/tasks/",
"patrol_ping_en": "[Patrol] Continue — check docs/agents/tasks/"
```

### Cursor 不在标准路径

```json
"cursor_exe_path": "C:\\Program Files\\Cursor\\Cursor.exe"
```

---

## 七、角色代码枚举

### 开发团队（dev-team）

| 角色代码 | 说明 |
|----------|------|
| `PM` | 项目经理 / 任务调度 |
| `DEV` | 全栈开发工程师 |
| `QA` | 测试工程师 |
| `OPS` | 运维部署工程师 |
| `E2E` | 端到端测试专员 |

### 自媒体团队（media-team）

| 角色代码 | 说明 |
|----------|------|
| `PUBLISHER` | 发布统筹 |
| `WRITER` | 文章撰写 |
| `EDITOR` | 编辑排版 |
| `COLLECTOR` | 素材收集 |

### MVP 团队（mvp-team）

| 角色代码 | 说明 |
|----------|------|
| `BUILDER` | 产品构建 |
| `DESIGNER` | 设计 |
| `MARKETER` | 市场推广 |
| `RESEARCHER` | 研究调研 |

---

## 八、任务优先级枚举

| 值 | 含义 | 响应预期 |
|----|------|----------|
| `P0` | 阻塞 / 紧急 | 立即处理 |
| `P1` | 高 | 当日完成 |
| `P2` | 中 | 本周完成 |
| `P3` | 低 | 有空再做 |
