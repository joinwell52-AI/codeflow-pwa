# CodeFlow 消息协议与各方交互文档

> 更新日期：2026-04-10  
> 适用版本：Desktop v2.9.14 / PWA v2.0.3

---

## 一、整体架构

```
手机 PWA          中继服务器              PC Desktop (Nudger)        Cursor AI
─────────         ─────────────           ───────────────────        ──────────
  │                    │                          │                      │
  │  ←── WebSocket ──→ │  ←── WebSocket ────────→ │                      │
  │                    │                          │  ←── pyautogui ────→ │
  │                    │                          │  ←── OCR 识别 ──────→ │
  │                    │                          │
  │                    │← 广播/定向投递 →│
```

- **手机 PWA**：主控台，发任务、看状态、看巡检轨迹
- **中继服务器**：`wss://ai.chedian.cc/codeflow/ws/`，纯转发，不存储
- **PC Desktop**：执行机，巡检文件、唤醒 AI、推送数据给手机
- **Cursor AI**：被 PC 通过 pyautogui 操控的 AI 角色（PM/DEV/QA/OPS 等）

---

## 二、中继路由规则

| 方向 | 规则 | 说明 |
|------|------|------|
| 手机→PC | **定向投递**（需带 `target_device_id`） | 手机发的控制指令必须指定 PC 的 device_id |
| PC→手机 | **广播**（不带 target_device_id） | PC 推送数据给同房间所有人 |
| 任意→任意 | 不在白名单的事件 → 中继拒绝 | 见 ALLOWED_EVENTS |

---

## 三、消息格式（统一）

```json
{
  "room_key": "用户的房间号",
  "sender": "Nudger | mobile_admin",
  "client_type": "desktop_nudger | mobile_admin",
  "event_type": "事件名",
  "payload": {}
}
```

---

## 四、手机 → PC 的消息（定向投递，需 target_device_id）

| 事件名 | 触发时机 | payload 关键字段 | PC 响应 |
|--------|---------|-----------------|---------|
| `request_dashboard` | 手机刷新/连接时 | `target_device_id` | 返回 `dashboard_state` |
| `patrol_status` | 轮询巡检状态（30s） | `target_device_id` | 返回 `patrol_state`（含轨迹） |
| `start_patrol` | 点"开始巡检" | `target_device_id` | 启动巡检，返回 `patrol_state` |
| `stop_patrol` | 点"停止巡检" | `target_device_id` | 停止巡检，返回 `patrol_state` |
| `request_bind_state` | 查询绑定状态 | `target_device_id` | 返回 `bind_state` |
| `request_bind_code` | 扫码绑定 | `target_device_id`, `mobile_device_id`, `mobile_device_name` | 返回 `bind_state`（含绑定码） |
| `execute_desktop_action` | 重置PC等操作 | `target_device_id`, `action` | 返回 `desktop_action_result` |
| `command_from_admin` | 手机发任务 | `target_device_id`, `text`, `target_role`, `priority` | 写文件，返回 `task_created` + `file_list` |
| `request_task_detail` | 查看任务详情 | `target_device_id`, `filename` | 返回 `task_detail` |

---

## 五、PC → 手机的消息（广播，同房间所有人收到）

| 事件名 | 触发时机 | payload 关键字段 | 手机处理 |
|--------|---------|-----------------|---------|
| `dashboard_state` | 响应 `request_dashboard` | `today_tasks`, `today_reports`, `today_issues`, `tasks[]`, `reports[]` | 更新今日统计、任务列表 |
| `patrol_state` | 响应 `patrol_status`/`start_patrol`/`stop_patrol` | `running`, `round`, `incomplete_tasks`, `patrol_trace[]` | 更新巡检状态 + 巡检轨迹 |
| `patrol_trace` | 定时推送（每5秒，有变化时） | `entries[]`（含 `t`,`stage`,`detail`） | 更新巡检轨迹列表 |
| `file_list` | 定时推送（每5秒，有变化时） | `tasks[]`, `reports[]`, `issues[]`, `today_tasks`, `today_reports` | 更新任务列表、今日统计 |
| `task_created` | 手机发任务后PC写文件成功 | `filename`, `target_role`, `text`, `status` | 显示 Toast，刷新任务列表 |
| `task_detail` | 响应 `request_task_detail` | `filename`, `content`, `meta` | 展示任务详情 |
| `bind_state` | 响应绑定请求 | `status`, `machine_code`, `pending_bind_code` | 更新绑定状态显示 |
| `desktop_action_result` | 响应 `execute_desktop_action` | `action`, `ok`, `message` | 显示操作结果 |
| `device_roster` | 任何设备上下线时 | `devices[]`（含 `device_id`,`device_name`,`owner_role`） | 更新在线设备列表，判断PC是否在线 |
| `alert` | 中继拒绝消息时 | `message` | 写入系统日志 |

---

## 六、PC 定时主动推送（无需手机请求）

```
每 5 秒（poll_and_push 协程）：
  ├── 有文件变化 → 推送 file_list + patrol_trace（reason=file_change）
  ├── 有巡检事件 → 推送 file_list + patrol_trace（reason=patrol_event）
  └── 无变化     → 推送 file_list + patrol_trace（reason=heartbeat）
```

---

## 七、PC 与 Cursor AI 的交互（本地，不经过中继）

| 操作 | 方式 | 触发条件 |
|------|------|---------|
| 切换 AI 角色 | OCR 识别标签 + pyautogui 点击 | 需要唤醒某个 Agent 时 |
| 发送催促消息 | pyperclip 复制 + pyautogui 粘贴发送 | 任务文件超时未回复 |
| 检测 Agent 是否忙 | OCR 识别 "生成中/Generating" | 发送前检查 |
| 检测 Connection Error | OCR 识别 "Connection Error/Try again" | 每轮巡检检查 |
| Reload Window | Ctrl+Shift+P → Developer: Reload Window → 回车确认 | 检测到 Connection Error 或长时间卡住 |
| 嵌入控制面板 | Ctrl+Shift+B → 粘贴URL → 回车 | CodeFlow 启动时 |

---

## 八、巡检轨迹事件阶段（patrol_trace stage）

| stage | 含义 | 颜色 |
|-------|------|------|
| `scan` | 扫描到新任务文件 | 蓝色 |
| `nudge` | 正在催办（发送消息给 Agent） | 紫色 |
| `nudge_ok` | 催办消息已送达 | 绿色 |
| `defer` | 延后重试（Agent忙/冷却中） | 橙色 |
| `giveup` | 超过最大重试次数，放弃 | 红色 |
| `send_fail` | 发送失败 | 红色 |
| `switch_role` | 切换 Agent 角色 | 青色 |
| `busy_wait` | 等待 Agent 完成生成 | 灰色 |
| `conn_error_reload` | 检测到 Connection Error，执行 Reload | 橙色 |
| `cursor_reload` | 执行了 Reload Window | 橙色 |
| `patrol_on` | 巡检启动 | 绿色 |
| `patrol_off` | 巡检停止 | 灰色 |

---

## 九、中继白名单（ALLOWED_EVENTS）

```python
# server/relay/server.py
ALLOWED_EVENTS = {
    "hello", "ping",
    # 手机→PC 控制
    "command_from_admin", "admin_command",
    "request_dashboard", "request_task_detail", "request_message_history",
    "start_patrol", "stop_patrol", "patrol_status",
    "request_bind_state", "request_bind_code",
    "execute_desktop_action",
    # PC→手机 推送
    "dashboard_state", "patrol_state", "patrol_trace",
    "file_list", "file_change", "agent_status",
    "task_created", "task_detail", "task_event",
    "reply_summary", "bind_state",
    "desktop_action_result", "device_roster",
    "message_history", "alert",
    "conn_error_reload",
}
```

---

## 十、常见问题排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| 手机发任务PC收不到 | `target_device_id` 未绑定 | 手机重新扫码绑定PC |
| PC推送手机收不到 | 公网中继版本旧，白名单缺事件 | 运行 `py -3 _deploy_relay.py` 更新中继 |
| 巡检轨迹不更新 | PC未在线/中继断连 | 检查PC巡检状态，重连 |
| Connection Error不自动恢复 | OCR识别失败 | 检查 `winocr` 是否正常 |
| 今日统计不更新 | `file_list` 事件被中继拦截 | 更新中继白名单 |
