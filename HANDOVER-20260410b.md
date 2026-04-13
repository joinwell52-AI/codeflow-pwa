# CodeFlow 交接文档
**版本**：Desktop v2.8.75 / PWA v2.0.3  
**日期**：2026-04-10（第二版，本次 Session 更新）

---

## 一、本次 Session 核心修复（v2.8.70 ～ v2.8.75）

### 问题背景
巡检器启动时向各 Agent 打招呼，出现两类严重问题：
1. **消息发错窗口**：消息内容是 WRITER 的，却发到了 COLLECTOR 窗口（根本原因：消息在切换窗口前预先生成，与实际切换结果脱钩）
2. **greet_strict 校验失败后不重试**：校验失败直接放弃，导致部分角色始终未收到第一条身份确认消息

### 修复链条（按版本顺序）

| 版本 | 修复内容 |
|------|---------|
| v2.8.70 | 技能市场根目录型仓库安装按钮修复；安装完成显示「重新安装」 |
| v2.8.71 | greet_strict 失败后最多重试 2 次 |
| v2.8.72 | greet_strict 模式等待时间延长（12s/4s/4s/3s），校验标准不降 |
| v2.8.73 | `_role_to_file()` 补全媒体/MVP团队路径；`mark_greeted=False` 防止状态污染 |
| v2.8.74 | 打招呼改为无限重试（指数退避 10→20→40→60s），直到成功 |
| v2.8.75 | **根本修复**：消息改为 `msg_factory` callable，在 OCR 三重确认角色后才生成，彻底杜绝消息与窗口不符 |

### 关键设计原则（已固化）
- **打招呼是强制初始化**，不允许失败放弃，必须成功才继续下一个角色
- **消息内容必须在角色确认后生成**，不能预先生成
- **greet_strict 三重校验**：sidebar + author 一致，或 sidebar + title 一致（任一组内部不一致则拒绝）
- **`_greeted_roles` 状态只在发送成功后标记**，失败时不污染状态

---

## 二、三条工作线

```
本地开发  →  改代码 → 打包 → 测试
PWA 发布  →  py -3 _deploy_pwa.py
GIT 备份  →  git push backup main
```

### 仓库说明

| 仓库 | 地址 | 用途 |
|------|------|------|
| `codeflow-pwa`（公开） | github.com/joinwell52-AI/codeflow-pwa | PWA 静态文件，GitHub Pages 发布手机端 |
| `codehouse`（私有） | github.com/joinwell52-AI/codehouse | 完整代码备份（`git push backup main`） |

---

## 三、Desktop 打包流程

```
1. 改代码（nudger.py / web_panel.py / panel/index.html 等）
2. 升版本号（三处同步）：
   - codeflow-desktop/main.py      → VERSION = "x.x.x"
   - codeflow-desktop/web_panel.py → _VERSION = "x.x.x"
   - codeflow-desktop/panel/index.html → PC vx.x.x
3. 打包：
   cd codeflow-desktop
   py -3.10 -m PyInstaller build.spec --noconfirm
4. 产物：codeflow-desktop/dist/CodeFlow-Desktop.exe
5. 测试副本：D:\newflow-1\CodeFlow-Desktop.exe
```

---

## 四、当前版本状态

### Desktop v2.8.75（本 Session 最终版）
- **打招呼机制**：OCR 三重校验通过后才生成并发送消息，消息与窗口严格绑定
- **greet_strict**：切换后等待 12s，三重校验（sidebar+author/title），失败无限重试（指数退避）
- **技能市场**：支持根目录型仓库（smart-illustrator 等），安装完成显示「重新安装」
- **单实例**：固定端口 `18765`，mutex `CodeFlowDesktop_18765`
- **项目级配置**：日志到 `{project_dir}/.codeflow/desktop.log`

### PWA v2.0.3（未变更）
- 巡检轨迹通过 WebSocket 事件推送
- PC 在线后自动更新任务列表、统计、巡检状态

---

## 五、关键文件路径

```
D:\BridgeFlow\
├── codeflow-desktop/
│   ├── main.py             # VERSION（当前 2.8.75）
│   ├── web_panel.py        # _VERSION + API + 技能市场后端
│   ├── nudger.py           # 巡检核心：switch_and_send / greet_all_roles
│   │                       # 关键函数：_is_role_active_for_greet / _role_to_file
│   │                       # 关键机制：msg_factory / mark_role_greeted
│   ├── cursor_vision.py    # OCR 视觉检测
│   ├── cursor_embed.py     # Cursor 嵌入（Ctrl+Shift+B）
│   ├── config.py           # NudgerConfig：所有可配置参数
│   ├── panel/index.html    # 前端面板 UI
│   └── dist/CodeFlow-Desktop.exe
├── web/pwa/                # PWA 主源
├── docs/agents/            # Agent 角色定义
├── docs/agents/tasks/      # 任务文件（只追加不修改）
├── external/               # 外部技能仓库（git clone 到此）
├── _deploy_pwa.py          # PWA 一键发布
└── CHANGELOG.md            # 版本历史
```

---

## 六、巡检器关键参数（codeflow-nudger.json）

| 参数 | 默认 | 含义 |
|------|------|------|
| `task_stuck_threshold_s` | 600 | 任务多久未更新算"卡住" |
| `task_timeout_threshold_s` | 1200 | 任务超时阈值 |
| `auto_nudge_interval_s` | 300 | 同一任务两次自动催促最小间隔 |
| `stuck_reload_window` | true | 卡住时先 Reload Window 再催促 |
| `patrol_ping_zh` | "" | 后续催促短句（空=用内置默认） |

---

## 七、greet_strict 校验流程（关键机制）

```
1. 切换侧栏 → 等待 12s（UI 渲染完成）
2. OCR 扫描：
   - sidebar + author 一致且均匹配目标 → 通过
   - sidebar + title 一致且均匹配目标 → 通过
   - 任一组内部不一致 → 拒绝，继续等待重扫
3. 复核 5 轮（4s/轮）：每轮重新 OCR 确认
4. 粘贴前终检（再等 3s + OCR）
5. ← 此处调用 msg_factory(confirmed_role) 生成消息
6. 粘贴 + 回车发送
7. send_ok → mark_role_greeted(role)
```

---

## 八、注意事项

- 修改含中文的文件（`.html` / `.md` / `.py`）必须用 Python 读写，禁止 PowerShell `-replace`
- 不要把真实 `room_key` 写到公开示例配置
- 中继限制单条消息 8KB
- `docs/agents/tasks/` 下已有任务文件只追加，不修改
- 打包产物 `dist/CodeFlow-Desktop.exe` 不进 git（`.gitignore` 已配置）
