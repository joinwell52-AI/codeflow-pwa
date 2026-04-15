# CodeFlow Message Protocol and Interaction Overview

> Last updated: 2026-04-10  
> Applies to: Desktop v2.9.14 / PWA v2.0.3

---

## 1. Overall architecture

```
Mobile PWA        Relay server            PC Desktop (Nudger)        Cursor AI
─────────         ─────────────           ───────────────────        ──────────
  │                    │                          │                      │
  │  ←── WebSocket ──→ │  ←── WebSocket ────────→ │                      │
  │                    │                          │  ←── pyautogui ────→ │
  │                    │                          │  ←── OCR 识别 ──────→ │
  │                    │                          │
  │                    │← broadcast / targeted delivery →│
```

- **Mobile PWA**: command console — send tasks, view status, view Patrol trace
- **Relay server**: `wss://ai.chedian.cc/codeflow/ws/`, forward-only, no persistence
- **PC Desktop**: execution host — Patrol files, wake AI, push data to Mobile
- **Cursor AI**: AI roles (PM/DEV/QA/OPS, etc.) driven by PC via pyautogui

---

## 2. Relay routing rules

| Direction | Rule | Notes |
|------|------|------|
| Mobile→PC | **Targeted delivery** (requires `target_device_id`) | Mobile control commands must specify the PC `device_id` |
| PC→Mobile | **Broadcast** (no `target_device_id`) | PC pushes data to everyone in the same room |
| Any→Any | Events not on the allowlist → Relay rejects | See ALLOWED_EVENTS |

---

## 3. Message format (unified)

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

## 4. Mobile → PC messages (targeted delivery, requires `target_device_id`)

| Event name | When it fires | Key `payload` fields | PC response |
|--------|---------|-----------------|---------|
| `request_dashboard` | Mobile refresh / connect | `target_device_id` | Returns `dashboard_state` |
| `patrol_status` | Poll Patrol status (30s) | `target_device_id` | Returns `patrol_state` (includes trace) |
| `start_patrol` | Tap "Start Patrol" | `target_device_id` | Starts Patrol, returns `patrol_state` |
| `stop_patrol` | Tap "Stop Patrol" | `target_device_id` | Stops Patrol, returns `patrol_state` |
| `request_bind_state` | Query bind state | `target_device_id` | Returns `bind_state` |
| `request_bind_code` | Scan to bind | `target_device_id`, `mobile_device_id`, `mobile_device_name` | Returns `bind_state` (includes bind code) |
| `execute_desktop_action` | Reset PC, etc. | `target_device_id`, `action` | Returns `desktop_action_result` |
| `command_from_admin` | Mobile sends a task | `target_device_id`, `text`, `target_role`, `priority` | Writes file, returns `task_created` + `file_list` |
| `request_task_detail` | View task detail | `target_device_id`, `filename` | Returns `task_detail` |

---

## 5. PC → Mobile messages (broadcast, everyone in the room receives)

| Event name | When it fires | Key `payload` fields | Mobile handling |
|--------|---------|-----------------|---------|
| `dashboard_state` | In response to `request_dashboard` | `today_tasks`, `today_reports`, `today_issues`, `tasks[]`, `reports[]` | Update today’s stats and task list |
| `patrol_state` | In response to `patrol_status` / `start_patrol` / `stop_patrol` | `running`, `round`, `incomplete_tasks`, `patrol_trace[]` | Update Patrol status + Patrol trace |
| `patrol_trace` | Periodic push (every 5s when changed) | `entries[]` (includes `t`, `stage`, `detail`) | Update Patrol trace list |
| `file_list` | Periodic push (every 5s when changed) | `tasks[]`, `reports[]`, `issues[]`, `today_tasks`, `today_reports` | Update task list and today’s stats |
| `task_created` | After Mobile sends a task and PC writes the file successfully | `filename`, `target_role`, `text`, `status` | Show Toast, refresh task list |
| `task_detail` | In response to `request_task_detail` | `filename`, `content`, `meta` | Show task detail |
| `bind_state` | In response to bind requests | `status`, `machine_code`, `pending_bind_code` | Update bind status UI |
| `desktop_action_result` | In response to `execute_desktop_action` | `action`, `ok`, `message` | Show operation result |
| `device_roster` | When any device goes online/offline | `devices[]` (includes `device_id`, `device_name`, `owner_role`) | Update online device list; infer whether PC is online |
| `alert` | When Relay rejects a message | `message` | Write to system log |

---

## 6. PC scheduled push (no Mobile request required)

```
Every 5 seconds (poll_and_push coroutine):
  ├── File changed → push file_list + patrol_trace (reason=file_change)
  ├── Patrol event → push file_list + patrol_trace (reason=patrol_event)
  └── No change   → push file_list + patrol_trace (reason=heartbeat)
```

---

## 7. PC ↔ Cursor AI interaction (local, not via Relay)

| Action | Method | Trigger |
|------|------|---------|
| Switch AI role | OCR tab + pyautogui click | When an Agent needs to be activated |
| Send nudge message | pyperclip copy + pyautogui paste/send | Task file timed out with no reply |
| Detect Agent busy | OCR for "生成中/Generating" | Check before sending |
| Detect Connection Error | OCR for "Connection Error/Try again" | Each Patrol round |
| Reload Window | Ctrl+Shift+P → Developer: Reload Window → Enter to confirm | Connection Error detected or stuck for a long time |
| Embed control panel | Ctrl+Shift+B → paste URL → Enter | When CodeFlow starts |

---

## 8. Patrol trace stages (`patrol_trace` `stage`)

| stage | Meaning | Color |
|-------|------|------|
| `scan` | New task file scanned | Blue |
| `nudge` | nudge in progress (sending message to Agent) | Purple |
| `nudge_ok` | nudge message delivered | Green |
| `defer` | Deferred retry (Agent busy / cooling down) | Orange |
| `giveup` | Max retries exceeded, giving up | Red |
| `send_fail` | Send failed | Red |
| `switch_role` | Switch Agent role | Cyan |
| `busy_wait` | Waiting for Agent to finish generating | Gray |
| `conn_error_reload` | Connection Error detected, performing Reload | Orange |
| `cursor_reload` | Reload Window executed | Orange |
| `patrol_on` | Patrol started | Green |
| `patrol_off` | Patrol stopped | Gray |

---

## 9. Relay allowlist (ALLOWED_EVENTS)

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

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|------|---------|------|
| Mobile sends task, PC does not receive | `target_device_id` not bound | Re-scan on Mobile to bind PC |
| PC pushes, Mobile does not receive | Public Relay is old, allowlist missing events | Run `py -3 _deploy_relay.py` to update Relay |
| Patrol trace not updating | PC offline / Relay disconnected | Check PC Patrol status, reconnect |
| Connection Error does not auto-recover | OCR failed | Check whether `winocr` works |
| Today’s stats not updating | `file_list` blocked by Relay | Update Relay allowlist |
