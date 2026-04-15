# Changelog

**码流（CodeFlow）** 版本历史，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [Unreleased]

---

## [2.11.0] - 2026-04-06

### 桌面端（`codeflow-desktop`）

#### 新增：Agent 工作实况监控

通过 CDP 实时提取 Cursor 中 Agent 的聊天消息摘要，推送到手机端 PWA 供只读监控。

- **`cursor_cdp.py` 消息提取引擎**：JS 注入脚本新增第 7b 节，从 DOM 提取最近 20 条消息，自动分类为 `text` / `code` / `terminal` / `file_edit` / `tool` / `thinking` / `image` 七种类型并生成摘要
- **`cursor_cdp.py` 数据结构**：`CdpCursorState.messages` 填充真实数据，`to_dict()` 输出 `recent_messages` 字段
- **`nudger.py` Relay 推送**：`_push_desktop_snapshot()` 每次推送附带 `agent_live_state` 事件（状态 + 消息摘要）
- **`nudger.py` 按需请求**：新增 `request_agent_live` 事件响应，PWA 可主动拉取最新 Agent 状态

### PWA（`web/pwa/`）

#### 新增：Agent 实时状态 + 只读工作实况面板

- **Agent 卡片升级**：活跃 Agent 显示实时状态徽章（绿色脉冲 = 工作中，灰色 = 空闲，黄色 = 等待审批）及状态文字（"规划中..."、"生成中..."等）
- **工作实况面板**：点击 Agent 卡片展开只读监控面板，显示模型名 / 消息条数 / 模式，以及最近 20 条消息的分类摘要（带图标 💬📝⚙️✏️🔧💭🖼️）
- **明确"只读"定位**：面板底部标注"只读监控 · 如需指挥请发送任务"，没有输入框，不破坏现有 TASK 协议
- **i18n 双语**：新增 18 个中英文案 key（agentMonitor / agentLive / agentMsgType 系列）

#### 优化：去聊天化 — 强化任务语境

- CSS class 重命名：`chat-list` / `chat-item` / `chat-meta` → `task-record-list` / `task-record-item` / `task-record-meta`
- "消息记录" → "指令日志" / "Command Log"（中英双语）
- "暂无消息" → "暂无指令" / "No commands yet"
- "发送" / "收到" → "已派发" / "已接收"

#### 修复

- **工作实况面板改为底部浮层**：不再占用任务清单空间，半透明遮罩 + 拖拽条，点击遮罩或 ✕ 关闭
- **4 种状态智能提示**：未连接 PC / 等待数据 / CDP 未开 / 正常工作实况，不再显示无意义的"暂无活动"
- **消息摘要优化**：代码块/工具调用/文件编辑类消息 summary 改为实际内容而非 "5 lines"
- **标签修正**："用户" → "指令"、"条对话" → "条消息"，"只读监控"提示移到底部

### 中继服务（`server/relay/`）

- `ALLOWED_EVENTS` 白名单新增 `agent_live_state` / `request_agent_live`，修复 PC 推送被中继拒绝的问题

### 桌面端修复

- `nudger.py`：不管 `found` 是否为 true 都推送 `agent_live_state`，附带 `cdp_active` / `has_cdp` 诊断字段
- `nudger.py`：推送日志改为 INFO 级别，便于排查
- `cursor_cdp.py`：消息摘要改为优先使用 plainText 而非纯计数

#### 版本号

- PWA 版本升至 `2.4.2`

---

## [2.10.1] - 2026-04-06

### 桌面端（`codeflow-desktop`）

#### 新增：全量双语支持（i18n）

为所有用户可见文案建立统一 i18n 基础设施，切换语言后 API 消息、面板 UI、巡检轨迹全部跟随。

- **新增 `config.py` i18n 引擎**：`_T(key, **kwargs)` 翻译函数 + `_I18N` 集中字典（130+ 键），支持 `set_lang("en")` 一键切换
- **`web_panel.py` 全量双语**：65+ 处 API 返回消息、预检文案、Tk 文件对话框、团队模板名/角色标签
- **`nudger.py` 巡检轨迹双语**：48 处 `patrol_trace` detail + 返回消息全部走 `_T()`
- **`cursor_cdp.py`**：5 处 `state.error` 双语化
- **`cursor_vision.py`**：3 处 `state.error` 双语化
- **`cursor_embed.py`**：12 处返回消息双语化
- **`panel/index.html`**：补全 I18N 字典（CDP 区块、技能市场、切换实测、巡检轨迹表头等 28 键），时间格式跟随 locale

#### 仓库清理

- 删除 `docs/` 下 PWA 重复副本（index.html + config.js + sw.js + manifest.json + 7 个 logo PNG）
- 删除 `docs/promotion/promotion/` 嵌套错误目录
- 删除 `promotion/index.html` 根目录重复推广页
- 删除 `cursor-forum.png`（根目录 + web/pwa/，无引用）
- 删除 `codeflow-desktop/dist_snap/snap_click.exe`（二进制构建产物不入库）
- `.gitignore` 新增 `codeflow-desktop/dist_snap/` 规则

#### 文档

- **新增 LICENSE**（MIT）——修复 README 徽章断链
- **补全 4 个 Cursor 规则英文版**：`qa-team-lead.en.mdc` / `qa-team-tester.en.mdc` / `qa-team-auto-tester.en.mdc` / `qa-team-perf-tester.en.mdc`
- **补全 7 篇文档英文版**：release-process / nudger-shoulder-tap / message-protocol / github-repo-about / repo-collaboration / cursor-shortcuts-scope / github-actions-codeflow-pwa
- README 版本徽章更新至 v2.10.1

### PWA（`web/pwa/`）

- 版本号升至 `2.3.1`（Service Worker 缓存更新）
- 清理无引用的 `cursor-forum.png`

---

## [2.10.0] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 新增：Chrome DevTools Protocol (CDP) 巡检引擎

全面引入 CDP 作为 Cursor IDE 交互的主力通道，OCR 降级为纯备用。

- **新增 `cursor_cdp.py` 模块**：通过 WebSocket 连接 Cursor 的 `--remote-debugging-port=9222`，直接读取 DOM
- **精确 Agent 区分**：使用 `div[role="tab"]` + `aria-selected` 精确识别当前活跃角色，不再依赖 OCR 猜测
- **原生鼠标事件切换角色**：`Input.dispatchMouseEvent` 实时坐标点击，替代 `pyautogui` 屏幕坐标
- **精确忙碌检测**：检测 Stop/Cancel 按钮可见性 + Composer 区域 spinner，替代 OCR 字符猜测
- **消息输入**：通过 `nativeInputValueSetter` 绕过 React 受控组件，直接写入输入框
- **自动 CDP 激活**：`cursor_embed.py` 检测到 Cursor 未带 CDP 端口时自动重启并附加参数
- **面板实时显示**：前端新增 CDP/OCR 模式状态指示灯，实时显示当前巡检模式
- **DOM 探查接口**：新增 `/api/cdp-probe` 端点，用于调试和 Cursor 升级后维护选择器

#### 新增：四套团队模板全面支持

- **角色别名扩展**：`_ROLE_ALIASES` 从 dev-team 4 个角色扩展到全部四套团队 20 个角色
- **命令面板映射**：`_PALETTE_ROLE_LABELS` 覆盖 dev-team / media-team / mvp-team / qa-team
- **团队模板补全**：`TEAM_TEMPLATES` 新增 qa-team（LEAD-QA、TESTER、AUTO-TESTER、PERF-TESTER）
- **角色文件映射**：`_role_to_file()` 补全 qa-team 四角色的文档路径

#### 文档

- **新增 `docs/cdp-multi-agent.md`**：CDP 多 Agent 区分机制完整技术文档（选择器、忙碌检测、失效场景）
- **更新 `docs/agents/README.md`**：统一四套团队角色命名规范（文件协议 / Cursor Tab / 归一化规则）

---

## [2.9.44] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 新增：巡检器自动检测 "Waiting for extension host" 并 Reload Window

- OCR 检测关键词新增 `waiting for extension host`、`extension host`
- Cursor Extension Host 卡死时，巡检器自动执行 `Developer: Reload Window` 恢复
- 与 Connection Error 检测共享 120 秒冷却期，不会反复触发

---

## [2.9.43] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 修复：dashboard_state 消息超过中继 max_size 被拒绝（1009 message too big）

- `MAX_WS_BYTES` 从 14KB 调整为 200KB，匹配中继已放大的 512KB `TRANSPORT_MAX_BYTES`
- `_build_dashboard` 中 `markdown` / `raw_markdown` 截断长度从 2000 字扩展到 8000 字
- 14 条任务的 dashboard 约 34KB，不再触发分片截断，markdown 内容完整传递到 PWA

### 中继服务（远程 `120.55.164.16`）

- `MAX_MESSAGE_BYTES`：8KB → **256KB**（业务层消息体积校验）
- `TRANSPORT_MAX_BYTES`：16KB → **512KB**（WebSocket `max_size` 参数）
- 重启 `bridgeflow-relay.service` 生效

### PWA（`web/pwa`）v2.2.9

- 版本号升级触发 Service Worker 刷新，配合 PC 端修复

---

## [2.9.42] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 修复：PC 频繁断连与中继 rate limit

- `ping_timeout` 从 20s 调整为 60s，`ping_interval` 从 20s 调整为 30s
- `_push_interval`（dashboard 轮询频率）从 5s 调整为 15s
- 心跳只发 `file_list`（不再每次发 `patrol_trace`），减少消息量
- 连接建立后延迟 3 秒再推初始 `dashboard_state`，避免与 hello 消息一起触发 rate limit

### 中继服务（远程 `120.55.164.16`）

- `RATE_LIMIT_COUNT`：20 → **50**（每 10 秒窗口内允许消息数）

---

## [2.9.41] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 修复：连接后立即推送 dashboard_state

- PC 连接中继后 3 秒自动推送完整 `dashboard_state`（含 markdown），确保 PWA 第一时间收到带内容的数据
- `_send` 函数增加日志：记录消息类型、大小、异常

### PWA（`web/pwa`）v2.2.8

#### 修复：file_list 不再覆盖 dashboard_state 数据

- `applyFileList` 彻底不操作 `taskItems` / `taskRecords`，仅更新统计数字
- `dashboard_state` 是带完整 markdown 的权威数据源，不再被 `file_list` 的最小数据覆盖
- 新增 `_ensureItemMd`：为缺少 markdown 的 item 自动生成合成内容

#### 修复：MD 原文显示

- 打开详情页时先显示"正在加载 MD 内容…"
- 3 秒内未收到 PC 回复则 fallback 到本地 `taskItems` 数据
- 点击"MD原文" tab 时自动重新请求 PC 获取完整内容

#### 修复：任务标题 7 层 fallback

1. `item.summary` / `item.body`
2. `markdown` 首行（去 `#`）
3. `raw_markdown` 首行（跳过 YAML front matter）
4. `messages` 中首条非空 body
5. `filename` 解析（`ADMIN01-to-PM` → `ADMIN01 → PM`）
6. `task_id`
7. "未命名任务"

---

## [2.9.40] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 修复：WebSocket 连接稳定性

- `websockets.connect` 的 `max_size` 从 16KB 调整为 1MB
- `poll_and_push` 异常处理更健壮：不再遇到任何异常就断连，改为连续 5 次异常才重连
- 新增 WebSocket 分片发送 `_send_chunked`：dashboard_state 超限时自动拆分 items 分批发送

### PWA（`web/pwa`）v2.2.5

#### 新增：任务列表分类 Tabs

- 任务列表页增加"任务单 / 报告 / 问题 / 归档"四个 Tab
- 对应 PC 端 `tasks` / `reports` / `issues` / `log` 目录

#### 新增：团队名显示

- "我的团队"标题后显示 `codeflow.json` 中配置的 `team_name`

#### 修复：normalizeRole 返回 ADMIN

- 空值、`SYSTEM`、未识别角色统一返回 `ADMIN`（不再显示 `OTHER`）

#### 修复：角色卡片缩写

- 长角色名（>3字符）显示 3 字母缩写 + 全名标签

---

## [2.9.36] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 新增：一键发版脚本 `publish.py`

- 自动化流程：Git tag → PyInstaller 打包 → GitHub Release → Gitee Release → PWA 同步
- `_github_pub.py` / `_gitee_pub.py` 支持动态读取版本号和 CHANGELOG

#### 修复：dashboard 推送 team_name 和完整团队信息

- `_read_team_info` 同时返回 `roles` 和 `team_name`
- `_build_dashboard` 扫描 `tasks` / `reports` / `issues` / `log` 四个目录
- 无 `body`/`summary` 时从 markdown 正文提取首行作为摘要

#### 新增：request_task_detail 处理

- PC 收到 PWA 的 `request_task_detail` 后，读取指定文件返回完整 markdown

### PWA（`web/pwa`）v2.2.0 ~ v2.2.4

#### 新增：团队角色动态同步

- 从 PC `dashboard_state` 接收 `team_roles`，动态更新角色卡片
- 角色列表缓存到 localStorage，断线时保持显示

#### 新增：统计卡片与角色任务分离

- 今日任务/今日回复/进行中/已完成：显示全部角色任务
- 点击团队成员卡片：过滤该角色的任务列表

---

## [2.9.35] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：自动更新机制改为直接覆盖（类似 Chrome）

- 废弃 batch 脚本方案（容易弹命令行窗口、路径问题）
- 新方案：下载完成后直接将旧 EXE 重命名为 .old，新 EXE 覆盖到原位置
- 程序退出后用户重新启动即为新版本
- 启动时自动清理上次残留的 .old 文件

---

## [2.9.34] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 新增：绑定即推、文件变化即推 dashboard

- 扫码绑定成功后立即推送 `dashboard_state`（角色+任务清单+统计），无需等巡检
- 文件变化（tasks/reports 新增或修改）时自动推送最新 dashboard 到 PWA

### PWA 端（`web/pwa/`）— v2.1.1

#### 新增：更新提示条

- 顶部蓝色渐变提示条：检测到新版本时弹出，点击强制刷新
- SW 不再静默自动刷新，改为用户主动确认更新

#### 修复：统计卡片与角色卡片分离

- 今日任务/今日回复/进行中/已完成：点击显示全部任务（不按角色过滤）
- 团队成员卡片：点击打开该角色的任务列表（按角色过滤）

#### 修复：主屏幕图标

- 重新生成标准正方形图标（192×192 / 512×512）
- 新增 maskable 图标（深蓝底色），适配 Android 自适应图标
- apple-touch-icon 改用正方形 192px 图标

---

## [2.9.33] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：自动更新重启失败（闪退不重启）

- batch 脚本改用 8.3 短路径，避免路径含空格/中文导致 copy/start 失败
- 新增更新日志文件（`%TEMP%\codeflow_update_<pid>.log`），方便排查失败原因
- `start` 命令加 `/D` 工作目录参数，确保新 EXE 在正确目录启动

---

## [2.9.32] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：dashboard 推送任务时携带 MD 正文

- `_build_dashboard` 每条任务 item 新增 `markdown`（去掉 front matter 的正文）和 `raw_markdown`（含 front matter 完整原文）字段
- PWA "MD原文" Tab 现在可以正常显示任务文件内容

---

## [2.9.31] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：dashboard 推送携带 team_roles 字段

- `_build_dashboard` 从 `codeflow.json` 读取当前项目团队角色列表
- PWA 收到后动态更新角色卡片，不再写死 PM/DEV/QA/OPS

### PWA（`web/pwa`）v2.0.4

#### 修复：团队角色与 PC 端实时同步

- `fixedTeamRoles()` 改为动态读取 dashboard 下发的 `team_roles`
- 本地 localStorage 缓存上次角色列表，断线时保持显示
- 角色列表变化时自动刷新团队面板和发送目标下拉

---

## [2.9.30] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 新增：双线路智能下载

- 下载前并发测速 Gitee / GitHub，自动选择响应最快的线路
- Gitee（国内）为优先线路，GitHub 为备用线路
- 主线路失败自动切换备用，无需用户干预
- 新增统一发版脚本 `release.py`，一条命令同步发布 GitHub + Gitee

---

## [2.9.29] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：自动更新下载走系统代理（VPN）

- `updater.py` 的 API 检查和文件下载均通过 `urllib.request.getproxies()` 读取系统代理
- 修复在开启 VPN/系统代理时下载仍卡在 0% 的问题

---

## [2.9.28] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：自动更新下载卡在 0% 问题

- 下载模块增加 TCP 连接超时（15秒）、单次 read 超时（30秒）、整体超时（5分钟）
- 支持下载失败自动重试（最多 5 次，间隔 2 秒）
- GitHub CDN 下载卡住时，30 秒后前端自动显示"手动下载"链接
- 修复 socket 超时未覆盖跳转阶段导致卡死的问题

---

## [2.9.26] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：引导阶段彻底隔离，不再被 Cursor Simple Browser 自动嵌入

- 引导阶段改用独立端口 **18766**，正常启动继续用 18765
- 根因：Cursor Simple Browser 会话恢复功能会在 Cursor 启动时自动恢复上次打开的 `127.0.0.1:18765` 标签，导致引导页被意外嵌入
- 换端口后 Cursor 恢复的是旧的正常面板端口，引导页不受影响
- 同时移除了 `/api/set_cursor_exe` 保存路径后触发嵌入的逻辑（v2.9.25 已修，本版继承）

---

## [2.9.25] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：引导阶段保存 Cursor 路径后不再触发嵌入

- `web_panel.py` `/api/set_cursor_exe` 保存路径后移除了自动触发 `embed_panel_after_launch` 的逻辑
- 引导期间 Cursor 已运行时不再被动嵌入引导页到 Simple Browser
- 引导阶段行为收敛为：只用系统浏览器打开引导页，记录路径，不做任何 Cursor 操作

---

## [2.9.24] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：引导完成后进程彻底退出

- 引导完成（填写完 Cursor 路径、团队、项目目录并保存）后，后端进程 1 秒内自动退出
- 前端引导页显示"配置已保存"后 3 秒自动关闭页面
- 不再打开任何额外浏览器标签、不再启动 Cursor、不再尝试嵌入面板
- 用户需要手动重新启动 CodeFlow 进入正常使用模式

#### 修复：引导阶段不再尝试嵌入 Cursor Simple Browser

- 引导期间只用系统浏览器打开引导页，完全移除对 `_schedule_embed_panel` 的调用
- 消除了引导期间可能触发 Cursor 自动启动的根源

---

## [2.9.22] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 改进：引导页实时显示启动版本检查状态

- 引导页打开 0.5 秒后立即轮询 `/api/update/check`
- 启动时版本检查进行中 → 显示「**正在检查版本，请稍候…**」
- 无新版本 → 提示栏自动隐藏，不打扰用户
- 发现新版本正在下载 → 显示「**发现新版本 vX.X.X，正在下载… XX%**」
- 下载完成 → 显示「**↺ 退出并重启安装新版本**」按钮
- 网络失败静默处理，不显示错误，不影响正常使用

---

## [2.9.21] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 改进：启动时按需进入引导页

- 有新版本 → 启动阶段快速检查（超时 5 秒），发现新版本立即进引导页，后台同步开始下载，引导页 2 秒后轮询即可看到下载进度和重启按钮
- 无新版本 / 检测超时 → 走原有逻辑（已配置项目直接进主面板，未配置走引导）
- 引导页不再需要等待 10 秒，因为启动时已触发检查，状态更新更快

---

## [2.9.20] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 改进：引导页支持更新检测与一键重启

引导页左侧版本号区域新增更新提示卡片：
- 打开引导页 **10 秒后**自动检测新版本（早于主面板的 20 秒）
- 下载中显示进度百分比
- 下载完成后显示「**↺ 退出并重启安装新版本**」按钮
- 点击后调用 `/api/update/apply`，batch 脚本热替换 EXE 并重启
- 引导页与主面板横幅状态同步，不重复下载

---

## [2.9.19] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 新增：EXE 自动更新

新增 `updater.py` 模块，实现完整的自动更新流程：

- **启动后 15 秒**自动后台检查 GitHub Releases 最新版本（不阻塞启动）
- 发现新版本后**静默后台下载**新 EXE 到临时目录，显示下载进度
- 下载完成后面板**顶部绿色横幅**提示用户，点击「立即重启更新」
- 点击后写入 batch 替换脚本：等旧进程退出 → 复制新 EXE → 启动新版本 → 清理临时文件
- 新增 API：`GET /api/update/check`（状态轮询）、`POST /api/update/apply`（触发替换）
- 前端每 15 秒轮询一次更新状态，启动 20 秒后开始轮询

---

## [2.9.18] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：引导阶段指定 Cursor 路径后不再自动拉起 Cursor

`_schedule_embed_panel` 新增 `auto_launch_cursor` 参数。引导阶段（首次设置 `cursor_exe_path`、引导完成回调）一律传 `False`，只嵌入已运行的 Cursor 窗口，不会自动把 Cursor 打开。正常启动路径（已有项目目录）保持原有行为（`True`，Cursor 未运行时第 1 次允许拉起）。

---

## [2.9.17] - 2026-04-13

### 桌面端（`codeflow-desktop`）

#### 修复：初始化指定 Cursor 路径后不再触发重启

`wizSelectCursor()` 保存路径成功后直接更新引导界面状态并解锁「下一步」，不再调用 `/api/restart`，初始化流程在当前进程内连续完成。

#### 修复：启动时只打开一个面板页

删除引导阶段多余的 `webbrowser.open(url)` 直接调用，面板打开逻辑统一由 `_schedule_embed_panel` 负责（优先嵌入 Cursor Simple Browser，连续失败 3 次后才降级系统浏览器，且只打开一次）。

#### 修复：打包脚本 `pack.cmd` 移除 `>NUL` 重定向

Windows 安全策略在某些机器上把 `>nul`/`>NUL` 重定向拦截为文件操作并弹出警告，改为直接输出，消除误报弹窗。

#### 修复：`config.py` 移除 `from __future__ import annotations`

Python 3.12 + PyInstaller 冻结环境下，`@dataclass` 与 `from __future__ import annotations` 共存可能触发 `typing.ClassVar` 循环初始化错误，删除该导入（3.12 原生支持 `tuple[float, float]` 写法，不需要此声明）。

#### 打包环境升级

`pack.cmd` 打包解释器从 `py -3.10` 升级为 `py -3.12`，与运行环境保持一致。

---

## [2.9.16] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 彻底废弃快捷键机制

OCR 视觉模式下切换 Agent 全程通过侧栏坐标点击完成，快捷键没有任何实际作用，本版本将其完全移除。

**删除的代码/字段：**
- `config.py`：删除 `hotkeys` 字段（含默认值 `{"PM": ["ctrl","alt","1"], ...}`）
- `nudger.py`：删除 `_hotkey_from_label()`、`_resolve_role()`、`_switch_and_send_blind()`、`check_keybindings()`、`ensure_keybindings()` 函数
- `nudger.py`：`_switch_and_send_with_vision()` 删除"降级用热键"分支
- `nudger.py`：`switch_and_send()` 移除 `hotkeys` 参数，删除 `_resolve_role` 调用，直接规范化 role 名称
- `main.py`：删除 `check_keybindings` import、启动时快捷键检查日志、从 codeflow.json 构造 `new_hotkeys` 的逻辑、`codeflow-nudger.json` 中 `hotkeys` 键的解析
- `web_panel.py`：删除"回退到 nudger hotkeys 里的角色"兜底逻辑

**greet_all_roles 角色来源变更：**
- 原来从 `config.hotkeys.keys()` 读取要打招呼的角色列表
- 现在从 `_UI_LABELS`（预检时注册的侧栏标签映射）读取，无则从 tasks/ 收件人推断

---

## [2.9.15] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 预检与快捷键说明修正
- **删除预检里的无用 `check_keybindings` import**：`_api_preflight` 只 import 了该函数但从未调用，删除死代码，避免误导。
- **预检不再要求配置快捷键**：EXE 内置 `winocr`，`HAS_VISION` 始终为 `True`；切换 Agent 的主路径是 OCR 识别侧栏坐标后鼠标点击，快捷键仅为 OCR 失败时的降级备用，预检无需检查。
- **文档更新**：`docs/config-reference.md` 和 `codeflow-desktop/BUILD.md` 中的快捷键"必须配置"描述已更正。

---

## [2.8.75] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 打招呼消息"先找角色，后生成内容"根本修复
- **`msg_factory` 延迟消息生成机制**：`switch_and_send` 支持 `message` 传入 `callable(role) -> str`；消息内容推迟到 OCR 三重校验（侧栏 + author + title）全部通过、粘贴前一刻才调用生成，从根本上杜绝"消息是 WRITER 的却发到 COLLECTOR 窗口"的窗口串台问题。
- **`_switch_and_send_with_vision` 新增 `msg_factory` 参数**：在 `vision[粘贴前] 角色再确认通过` 日志之后、`_wait_while_agent_busy` 之前调用工厂函数生成消息，确保消息内容与当前已确认窗口角色严格绑定。
- **`greet_all_roles` 改为传 callable**：不再预先生成消息字符串，而是在循环里定义 `_make_greet_msg(confirmed_role)` 工厂函数传入 `switch_and_send`，彻底解决预生成内容与实际切换窗口不符的竞态问题。

---

## [2.8.74] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 打招呼无限重试直至成功
- **打招呼是强制初始化，不设重试上限**：原来最多重试 2 次后放弃（记 `greet_fail`），改为 `while True` 循环，直到 `switch_and_send` 返回 `True` 才继续下一个角色。
- **指数退避等待**：失败后等待时间从 10s 开始，每次翻倍（10→20→40→60s 封顶），避免频繁触发 Cursor 界面。
- **可中断**：每轮循环开始检查 `self._running`，面板点「停止巡检」时立即退出，不阻塞。
- **日志事件**：重试中记 `greet_fail_retry`（含 attempt 次数和 wait_s），成功后才记 `greet_ok`。

---

## [2.8.73] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 打招呼角色文件路径修复 + `_greeted_roles` 状态污染修复
- **新增 `_role_to_file()` 函数**：统一映射角色代码到 `docs/agents/` 路径，覆盖标准团队（PM/DEV/OPS/QA/E2E）和媒体团队（WRITER/EDITOR/PUBLISHER/COLLECTOR）及 MVP 团队（BUILDER/DESIGNER/MARKETER/RESEARCHER）；同时正确处理 `03-WRITER` 格式（剥离前缀数字）。
- **`build_nudge_message` 新增 `mark_greeted=False` 参数**：打招呼时生成消息不再同步标记 `_greeted_roles`；`switch_and_send` 返回 `True` 后才调用 `mark_role_greeted(role)` 正式标记，避免发送失败时角色被错误标为"已打招呼"导致后续只发短句。
- **新增 `mark_role_greeted()` 独立函数**：供确认发送成功后显式调用。

---

## [2.8.72] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### `greet_strict` 等待时间大幅延长（保持严格校验不降标准）
- **`greet_strict` 模式专用慢速参数**：切换后等待从 6s → **12s**，复核前等待从 2.2s → **4s**，每轮复核间隔从 2.8s → **4s**，粘贴前终检等待从 1.85s → **3s**；给 Cursor UI（author/title）充足时间完成渲染，三重校验在 UI 完全稳定后进行。
- **严格校验规则不变**：仍要求 `sidebar + author` 一致，或 `sidebar + title` 一致，或顶部 Tab 命中；任一组内部不一致（如 sidebar=EDITOR 但 author=PUBLISHER）仍拒绝。

---

## [2.8.71] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 打招呼失败后重试（最多 2 次）
- **`greet_all_roles` 加重试循环**：`greet_strict` 校验失败后最多重试 2 次，每次重试前额外等待 10s（让 Cursor UI 稳定），全部失败才记 `greet_fail`。

---

## [2.8.70] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 技能市场：根目录型仓库安装修复 + 安装完成显示「重新安装」
- **根目录型 skill 安装按钮修复**：`smart-illustrator` 等 SKILL.md 在仓库根目录的仓库，前端过滤条件原来要求路径含 `/repoId/`（末尾有斜杠），根目录型路径末尾无斜杠导致匹配失败、不显示「安装全部」按钮。修复：同时检查 `endsWith('/repoId')`，`fetchRepos` 和 `installRepoAll` 均已修正。
- **安装完成显示「重新安装」**：当仓库下所有 skill 均已安装（`installed === total`）时，按钮文字改为「重新安装」，边框变绿色；计数标签颜色同步变绿。
- **进度完成后 3 秒自动刷新**：`installRepoAll` 完成后延迟 3s 调用 `fetchRepos()`，按钮状态同步更新为「重新安装」。

---

## [2.9.04] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 首次引导向导（全新项目初始化流程）
- **沉浸式引导页**：新项目首次启动时自动打开全屏引导向导，分三步：①连接 Cursor → ②选择团队 → ③初始化项目。
- **自动检测 Cursor**：Step 0 自动检测 `Cursor.exe` 路径，已找到则显示路径；未找到时提供"浏览选择"按钮。
- **左侧品牌区**：引导页左侧用 `product.png` 宣传图铺满，底部渐变遮罩保证文字可读。
- **项目目录浏览**：Step 2 项目路径改为系统文件夹选择对话框（`tkinter.filedialog`），无需手动输入。
- **引导完成自动退出**：配置保存后程序自动退出（`os._exit(0)`），用户重启即为正常启动流程。
- **前端提示**：完成页显示"配置已保存，请关闭页面后重启程序即可正常使用"，3 秒后自动关闭浏览器标签。

#### 进程查找重构（彻底修复 Surface 等机器找不到 Cursor 的问题）
- **三层查找策略**：①`CreateToolhelp32Snapshot` Win32 API（最可靠，不依赖外部命令）→ ②`psutil`（兜底）→ ③`tasklist` 全量输出自行过滤（兜底²）。
- 彻底解决 `tasklist /fi "imagename eq cursor.exe"` 在部分 Windows 版本大小写过滤失效的问题。
- 降级逻辑排除已知系统窗口（`Windows 输入体验`、`Program Manager`、`向日葵`等），不再误选非 IDE 窗口。

#### 项目级配置隔离（多项目并行）
- 日志切换到 `{project_dir}/.codeflow/desktop.log`，不同项目日志互不干扰。
- 截图 `tab_debug.png` 保存到项目 `.codeflow/` 目录。
- 配置拆分为全局（`cursor_exe_path`）和项目级（`{project_dir}/.codeflow/config.json`）。
- exe 放在项目文件夹内运行，自动以 exe 所在目录为项目根，无需选择对话框。

#### 端口统一固定
- 面板端口统一固定为 `18765`，废弃之前的路径 hash 动态端口（曾导致重启后端口变化、面板断线）。

#### Bug 修复
- 正常启动时 `start_panel` 未传端口导致使用默认值、URL 写死 `18765` 但实际端口不同，已修复。
- 引导完成后错误地触发 `/api/restart` 重启新进程导致端口变化和重启循环，已修复（改为直接退出）。
- `wiz-left-bg` CSS `background-image` 路径在打包环境解析失败，改用 `<img>` 标签。
- logo 路径 `panel/logo-sm.png` 修正为 `logo-sm.png`。

---

## [2.8.77] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 发送串台根本修复
- **粘贴前顶部 Tab 终止校验**：`greet_strict` 模式下，在粘贴前终检和普通粘贴前 recheck 环节，额外调用 `get_active_tab_role`（× 关闭按钮法 + 像素亮度法）确认顶部激活 Tab 必须与目标角色一致；不匹配则放弃发送，彻底杜绝多 Tab 场景下焦点串台导致消息发错窗口的问题。

---

## [2.8.76] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### OCR 切换可靠性修复
- **激活高亮行 OCR 补偿**：Cursor 侧栏被选中的 Agent 行因背景高亮导致 OCR 识别失败时，自动通过相邻行 y 坐标线性插值估算缺失行坐标，写入 `role_positions` 占位（`NN-?`），使点击切换仍能命中目标。
- **切换等待时间放宽**：`greet_strict` 模式等待由 12s 不变，普通催办 `_WAIT_AFTER_CLICK` 由 2.5s → 3.0s；验证失败后额外多等 1.0s 再重扫，给 Cursor 渲染更充裕的时间。
- **OCR 坐标缺失时降级热键**：`_switch_and_send_with_vision` 中若 `vision_click_role` 找不到坐标，自动降级用 `hotkeys` 里的快捷键切换，不再直接跳过。
- **聊天标题 y 阈值放宽**：`get_chat_title_role` 的 `y < 160px` 限制放宽至 `y < 240px`，兼容多 Tab 布局时标题行下移的情况。

#### 打招呼消息内容修复
- **`first_hello` 模板新增 `{role_name}`**：同时显示角色代码名（如 `COLLECTOR`）和文件路径（`docs/agents/COLLECTOR.md`），发送到错误窗口时 Agent 也能自行核对身份。
- **`build_nudge_message` 媒体/MVP 团队支持**：`_role_to_file` 补全 WRITER / EDITOR / PUBLISHER / COLLECTOR / BUILDER / DESIGNER / MARKETER / RESEARCHER 的映射，不再 fallback 成错误文件名。
- **`_fmt_tpl` 容错**：模板中多余占位符不再抛 `KeyError`，缺失键自动补空串。
- **`bridgeflow-nudger/nudger.py` 同步修复**：`role_code` 提取正则改为 `re.sub(r'^\d+[-_\s]*', '', ...)` 正确剥离 `NN-` 前缀；`_ROLE_TO_FILE` 补全媒体+MVP团队角色。

---

## [2.8.64] - 2026-04-10

### 桌面端（`codeflow-desktop`）

#### 首次身份校验加强
- **`greet_strict` 粘贴前终检**：多轮复核通过后再额外静止 ~1.85s 扫一次 vision，校验失败则整条 `first_hello` 消息不发出，确保首条身份问候绝不发错 Agent 窗口。
- **`_is_role_active_for_greet`** 逻辑不变（Tab / 侧栏+Author 双重命中才通过），终检在复核之后作为独立防线追加，不影响正常后续催办路径。

#### 后续催办改为短句
- 每个角色 **首次** 仍发完整 `first_hello`（包含 `role_file` 指引）；该角色一旦进入 `_greeted_roles` 集合，后续所有新文件通知、定时催办、stuck 催促一律改发 **`patrol_ping`**（中文默认：`【码流巡检】巡检，开工。请自行查看 docs/agents/tasks/ 等待办任务。`），由 Agent 自行打开任务文件阅读，不再贴长文案。
- 可在 `codeflow-nudger.json` 的 `patrol_ping_zh` / `patrol_ping_en` 字段覆盖短句文案（空字符串则使用内置默认）。

#### 卡住检测参数可配置
- `TaskTracker` 的阈值从硬编码改为读取 `config`，支持在 `codeflow-nudger.json` 中按项目调整：

  | 配置字段 | 默认 | 含义 |
  |---|---|---|
  | `task_stuck_threshold_s` | 600（10 分钟）| tasks/ 下 .md 多久未更新算「可能卡住」 |
  | `task_timeout_threshold_s` | 1200（20 分钟）| 多久算「超时」 |
  | `auto_nudge_interval_s` | 300（5 分钟）| 同一 TASK 编号两次自动催促最小间隔 |
  | `stuck_reload_window` | true | 自动催促卡住任务前是否先 Reload Window |
  | `stuck_reload_min_age_s` | 600 | 触发 Reload 的任务最小年龄（对齐 stuck 阈值） |
  | `stuck_reload_once_per_task` | true | 每个 TASK 编号仅 Reload 一次，避免反复刷窗口 |
  | `reload_window_wait_s` | 12 | Reload 后等待 Cursor 就绪的秒数 |

- 面板 `get_status()` 的 `patrol_tuning` 字段同步暴露上述配置，便于实时核查生效参数。

#### 卡住时自动 Reload Window
- 新增 `reload_cursor_window(config)` 函数：`Ctrl+Shift+P` → 粘贴 `Developer: Reload Window` → 回车，用于恢复长时间卡死的 Cursor UI。
- 在 `auto_nudge_stuck()` 中于发送催办短句前自动调用：仅当 `stuck_reload_window=true` 且任务年龄 ≥ `stuck_reload_min_age_s` 且（`stuck_reload_once_per_task=true` 下该 TASK 尚未 Reload）才触发；Reload 成功后重新 `find_cursor_window` 获取最新句柄，再发短句催办；Reload 失败不记入已处理集合，下次仍可重试。

#### 催办时机说明（文档化）
- 主循环 `poll_interval`（默认 5s）× `stuck_check_every_n`（默认 30 轮）= **约 150s 扫一次卡住任务**；idle 「继续」每 `idle_check_every_n`（默认 6 轮）≈ **30s 一次**；同一收件人发完一条后仍有 `nudge_cooldown`（默认 15s）冷却保护。

---

## [2.8.19] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **技能市场数据源改为 `external/README.md`**：面板「技能市场」优先解析 `external/README.md` 中的 Markdown 表格（本地目录 / GitHub URL / 用途摘要），自动提取推荐仓库列表；用内置 `_SKILL_REPOS` 补充友好中文名称和描述；README 未覆盖的仓库从内置列表 fallback 补齐。新增仓库只需在 README 表格加一行，无需改代码。

## [2.8.18] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **修复外部技能显示空白**：`_get_external_dir()` 原来完全依赖用户在面板设置的「项目目录」，未设置时返回 `None` 导致技能市场和已下载技能均显示空白。新增 fallback 逻辑：优先查找 `web_panel.py` 父级目录（`BridgeFlow/external/`）和 `codeflow-desktop/external/`，未设置项目目录时也能自动定位到 `D:\BridgeFlow\external\`。`_api_skills_list` 同步改为调用 `_get_external_dir()`，逻辑统一。

## [2.8.17] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **技能市场**：「外部技能」区块新增「技能市场」子区块，内置5个预设仓库（Anthropic官方、小红书、智能配图、微信公众号等），一键 `git clone --depth=1` 下载到 `external/`，已下载可一键更新（`git pull`）；下载完成后在「已下载技能」区选择安装到当前项目 `.cursor/skills/`。
- **新增 `_bump_version.py`**：统一版本号同步工具，用相对路径替代历史遗留的硬编码临时脚本。

## [2.8.16] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **新增外部技能安装功能**：面板新增「外部技能」区块，自动扫描项目同级 `external/` 目录下所有 `SKILL.md`，读取 name/description，支持一键安装到项目 `.cursor/skills/<name>/`，已安装的显示绿色"✓ 已安装"标记，可重装覆盖。后端新增 `GET /api/skills/list` 和 `POST /api/skills/install` 接口。

## [2.8.15] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **新增 `get_chat_title_role()` 专用函数**（`cursor_vision.py`）：专门从 OCR 结果中识别聊天区左上角的 Agent 大标题，条件为 y<160px、x≥30px、符合角色命名格式，按 y 升序取最顶行，是判断"当前激活 Agent 是谁"的唯一可靠来源。
- **实测验证统一调用该函数**：成功显示 `已切换 → 01-PUBLISHER`，失败显示 `目标=02-COLLECTOR，聊天区标题=01-PUBLISHER（切换失败）`，彻底告别误报。

## [2.8.14] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **实测验证改用聊天区标题栏 OCR**：Cursor 聊天区左上角的大标题（如 `01-PUBLISHER`）是当前激活 Agent 最可靠的来源。点击后在 OCR 结果中扫描 x<窗口60%、y<200px 的区域，找到的第一个角色名即为当前标题；严格比对目标角色，匹配则成功，不匹配则报失败并显示实际标题名，彻底解决误报问题。

## [2.8.13] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **实测验证改为像素亮度检测**：OCR `all_roles` / `role_positions` 包含全部角色，无法区分"当前激活哪个"。新方案：点击后对目标 Agent 行截图，计算该行像素平均亮度与其他角色行的亮度差值——Cursor 激活行背景明显更亮（差值 ≥8），以此作为唯一判断依据；详情输出 `亮度 目标=xx 其他均值=xx`，失败时附完整诊断。

## [2.8.11] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **实测成功必须显示 Agent 名字**：成功详情从 `侧栏已确认（via positions）` 改为 `已切换 → 01-PUBLISHER`，显示 OCR 实际读到的完整角色名（优先 author 行，其次 role_positions key，再次 all_roles 列表）。

## [2.8.10] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **面板 UI 重设计（嵌入优化）**：全面重写 CSS，字体基准从 16px 缩至 11px，heading 12px，代码 10.5px；控件 padding/间距紧凑化，更适合 Cursor Simple Browser 嵌入窗口；颜色系统升级为更深的 `#0b0f1a` 背景 + 更细的 border，整体风格 Compact Dark Terminal；scrollbar 细化为 4px。

## [2.8.9] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **实测详情精简**：成功时只显示 `侧栏已确认（via positions/roles/author）`；只有 OCR 未匹配时才输出完整诊断信息，保持界面整洁。

## [2.8.8] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **实测详情全量输出 OCR 原始内容**：验证步骤的详情栏现在固定显示 `author=... | roles=[...] | positions=[...]`，无论成功还是已点击，都能看到 OCR 实际扫到了什么，方便定位识别问题。

## [2.8.7] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **修复切换实测误报失败**：验证逻辑改为检查 OCR `role_positions` / `all_roles`（侧栏可见项），不再依赖 `agent_role`（聊天 Author 行，切换后不立即刷新，导致始终读到上一个角色名）；等待时间从 1.5s 延长至 2.5s；OCR 仍无法确认时标记为"已点击"而非"失败"，方便人工核查。

## [2.8.6] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **修复切换实测表格始终空白**：`test_all_poll` 接口误注册在 POST 路由，前端 GET 请求每次得到 404 后静默重试，步骤数据永远无法返回。已将该接口移至 GET 路由。
- **修复实测时 Cursor 窗口被还原为标准大小**：`_safe_focus` 使用 `SW_RESTORE(9)` 会强制还原最大化窗口；改为先调用 `IsZoomed` 判断当前状态，最大化时用 `SW_MAXIMIZE(3)` 保持，否则用 `SW_SHOW(5)` 不改变窗口大小。

## [2.8.5] - 2026-04-08

### 桌面端（`codeflow-desktop`）

- **修复切换实测竞态**：线程启动前先在主线程重置 `_test_all_state`（`running: True, steps: [], total: 0`），消除线程初始化与前端轮询之间的竞态窗口；`_api_agent_test_all` 末尾补 `return`。

### 桌面端（`bridgeflow-nudger`）

- **实验性 ACP**：可选在 `codeflow-nudger.json` 配置 `cursor_acp_endpoint`（或环境变量 `CODEFLOW_ACP_ENDPOINT`），向 Cursor 侧发送 JSON-RPC `workspace/openSimpleBrowser`（`layout` / `widthRatio`）；成功则不再用系统浏览器 + `win_snap`。端点与方法以所用 Cursor 版本为准，见 `BUILD.md`。
- **环境预检**：启动巡检（`/api/start`）前 **必须** 预检全部通过；未通过时返回 400 并提示在 Cursor/项目中修正后重跑预检。面板「启动巡检」对应展示告警并刷新预检列表。`first_hello` 与 BUILD 说明与之一致。
- **巡检轨迹**：内存环形缓冲仍最多 **280** 条；面板 `/api/patrol_trace` 支持 `limit`/`offset` 分页，表格底部增加上一页/下一页与说明。
- **巡检轨迹搜索**：`q` 参数在内存中按说明/阶段/时间及附加字段做子串匹配（空格/逗号分隔多词为 AND）；面板增加搜索框与清除。
- **随机等待**：主循环在 `poll_interval` 上叠加 `patrol_sleep_jitter_s`（默认约 0.4～2.5s）；每次成功向 Cursor 发送后叠加 `post_send_jitter_s`（默认约 0.25～1.8s）。可在项目根 `codeflow-nudger.json` 覆盖；`get_status().patrol_tuning` 可查看当前值。

---

## [2.2.1] - 2026-04-04

### 桌面端（`bridgeflow-nudger`）

- **预检 · Agent 切换实测**：在「快捷键」「Agent 映射」之外，新增一项——按 `codeflow.json` 顺序 **真实发送各角色快捷键**，再 **OCR 校验当前焦点 Agent**，证实窗口可见且能切换；未通过则整表预检不通过。面板 **2.2.1**。

---

## [2.2.0] - 2026-04-04

### 桌面端（`bridgeflow-nudger`）

- **向导步骤 3**：Agent 对齐说明按 **`docs/agents/codeflow.json` 的 `roles`**（所选团队模板）动态生成，支持自媒体等多套角色，不再写死 PM/DEV/QA/OPS。
- **团队策略**：已配置后 **不提供「切换团队」入口**；「团队」区块增加说明——更换团队模板须 **「重置」** 后重新走向导；「同步角色模板」仅按**当前**模板刷新 `docs/agents/`。重置确认文案同步说明会覆盖 `codeflow.json` 等。
- **vision**：`ocr_with_layout_boost` 增加 **右侧竖条** OCR 并与坐标合并，改善 Open Agents 在 **右侧** 时侧栏角色识别不到的问题。
- **版本**：面板/API 上报 **2.2.0**（`web_panel._VERSION`）。

---

## [2.1.4] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **环境预检**：撤销阻塞「全部通过」的 **客户确认** 步骤；快捷键与 Agent 映射 **仅由预检自动判定**，移除 `preflight_user_confirm` 落盘与 `/api/preflight_confirm`。
- **面板**：预检明细列增加换行与 `overflow-x` 约束，减轻横向撑破布局。

## [2.1.3] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **巡检文案**：首轮与各通道消息带 **角色代码 + 侧栏标签（01-PM～04-OPS）**，要求身份不符时勿执行任务。
- **闭环判定**：`terminal` 元数据 + `thread_key` 等补充已闭环任务号，减轻假催办；面板流水线与 nudger 共用 `collect_closed_task_ids`。
- **BUILD.md**：补充 CodeFlow 与 Cursor 分工说明。

## [2.1.2] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **vision_no_input（chat_open=true）**：在 Agent 模式且已识别侧栏角色时，若 OCR 仍识别不到输入框占位符，增加**窗口右下几何兜底**为输入区（`input_box_heuristic`），减少仅因主题/语言导致的死循环；并扩充 placeholder 关键词与模型行检测（gpt-4 等）。轨迹阶段 **`vision_input_heuristic`** 表示本次使用了兜底。

---

## [2.1.1] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **预检区块**：每次「环境预检」结束后，**全部通过**则自动**折叠**预检区域；**有未通过项**则自动**展开**，便于逐项处理。标题旁箭头与折叠状态同步。

---

## [2.1.0] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **环境预检 · Agent 映射**：在找到 Cursor 窗口后自动 **聚焦 → 截图 OCR**，为每个配置的快捷键角色（PM/DEV/QA/OPS）建立 **逻辑角色 ↔ 侧栏 OCR 文案 ↔ 屏幕坐标**；预检项「Agent 映射」全部命中后更易保证巡检接手。映射可写入 `docs/agents/.codeflow/preflight_agent_map.json` 备查。
- **面板**：预检区展示映射表与当前焦点 OCR、OCR 耗时。

---

## [2.0.9] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **Open Agents / Pinned 列表**：Cursor 界面为 **01-PM、02-DEV**（前导零）时，原 OCR 正则无法识别「01」中的 **1-PM**（`0` 会阻断匹配）。已改为数字前缀支持可选 **0**，与列表文案一致。
- **区域锚点**：除「Pinned」外，识别 **Open Agents Window** 标题行，便于竖向列表区域推断。
- **点击切换**：`click_role` 优先尝试 **01-PM / 02-DEV** 等与界面一致的串，再回退 **1-PM / PM**，提高对「打招呼」等流程的命中率。

---

## [2.0.8] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **视觉发送快路径**：与 Cursor 实际行为一致——**Ctrl+Alt 切 Agent 通常会同时带上聊天输入焦点**。若 OCR 已判定「当前即目标 Agent 且存在输入框」，则**直接粘贴发送**，不再先多轮 Ctrl+L；否则**先试一次快捷键**，若随后 OCR 同时满足目标 Agent + 输入框，则**跳过**慢路径（Ctrl+L 循环 + 多轮切换）。仅当快路径未达成时才走原有慢路径。

---

## [2.0.7] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **视觉发送顺序**：先多次 **Ctrl+L** 确保检测到聊天 **输入框**（轨迹 `vision_chat_focus` / `vision_chat_ready`），再进入切换 Agent；避免未打开聊天就快捷键/点击/命令面板连打。
- **减少命令面板**：切换轮次改为 **2**；**Ctrl+Shift+P** 仅在**最后一轮**作为兜底（`vision_palette` 不再每轮都出现）。

---

## [2.0.6] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **无面板即无进程**：浏览器每 **4s** `POST /api/panel_ping`；若 **约 42s** 未收到心跳，或 **3 分钟内从未** 有面板连接，则 **自动 `shutdown_desktop()`**，避免无控制面板仍运行巡检/pyautogui导致乱点。与「关标签 / 退出」互为补充。
- **面板文案**：顶部提示条同步说明心跳与自动退出逻辑。

---

## [2.0.5] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **关闭浏览器即退出**：面板页监听 **`pagehide`**，在**非刷新**关闭标签时 **`fetch('/api/quit', { keepalive: true })`**，与点「退出」相同，避免「只关网页进程还在」。**刷新（F5）不会**触发退出。
- **提示条**：面板顶部增加红色提示说明上述行为；多开多个面板标签时，**关闭任一标签会结束整个进程**。
- **第二实例弹窗**：文案更新，说明可关标签退出及任务管理器处理方式。

---

## [2.0.4] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **巡检轨迹面板**：内层 **`#traceScrollWrap`** 纵向滚动、表头 sticky；默认拉取 **200** 条；环形缓冲 **280** 条。解决「看不到上面记录、无滚动条」问题。
- **轨迹粒度**：视觉发送失败时不再只显示笼统 `send_fail`，而区分 **`vision_palette`**（已走 Ctrl+Shift+P）、**`vision_switch_fail`**、**`vision_no_input`**、**`vision_role_mismatch`**、**`vision_scan_fail`** 等；打招呼增加 **`greet_try` / `greet_ok` / `greet_fail` / `greet_done`**。
- **说明**：命令面板是切换 Agent 的**第三档降级**（快捷键→点击→命令面板），OCR 长期对不上时会出现多次 `vision_palette`，属预期；若 **`vision_no_input`** 持续出现，需保证 Agent 聊天区可见、侧栏未完全挡住输入区。

---

## [2.0.3] - 2026-04-06

### 桌面端（`bridgeflow-nudger`）

- **单实例**：Windows 下使用命名互斥 **`Local\CodeFlowDesktop_SingleInstance_Mutex_v1`**，避免多次双击 exe 出现多个 **CodeFlow-Desktop.exe**（任务管理器同名 `(2)`）。若已有实例在运行，新进程弹窗说明后退出。

---

## [2.0.2] - 2026-04-04

### 桌面端（`bridgeflow-nudger`）

- **退出与后台残留**：停止巡检时置位全局中止标志，打断进行中的 `pyautogui` 快捷键/点击链；面板 **`/api/quit`**、**Ctrl+C**、**SIGTERM** 统一走 **`shutdown_desktop()`**：先停巡检、再关闭本地面板 HTTP 服务、**`os._exit(0)`** 结束进程，避免「只关浏览器 / 任务管理器看似关了」仍占内存并继续模拟输入。
- **日志**：说明须使用面板 **「退出」** 或 **Ctrl+C**；仅关闭浏览器标签**不会**停止进程。
- **查找 Cursor 窗口**：`cursor_vision` 仅依赖 `QueryFullProcessImageName` 时，部分环境下对 Cursor 进程返回空路径，导致永远 `no_cursor_window`。现 **`find_all_cursor_windows`** 增加与巡检器相同的 **OpenProcess 回退解析**；且 **`vision_find_window` 失败时**在 **`nudger`** 中回退到 **EnumWindows + 双路径 exe 解析**，避免「已开 Cursor 却仍提示未找到窗口」。

### 仓库整理（协作）
- **文档**：新增 **`docs/repo-collaboration.md`**（分支约定、勿提交目录）；**README**、**HANDOVER** 增加引用。（后续约定：**仅 `main` 为主分支**，不再使用 `master`。）
- **`.gitignore`**：忽略 `_pages_tmp/`、临时提交说明、桌面端调试图、`CodeFlow-Desktop.spec` / `BridgeFlow-Desktop.spec`（自动生成；以 **`build.spec`** / **`pack.cmd`** 为准）。
- **Git**：不再跟踪上述两个自动生成的 `.spec` 文件。

---

## [2.0.1] - 2026-04-04

### 桌面端（`bridgeflow-nudger`）

- **版本号**：`main.py`、`web_panel.py` → **2.0.1**；打包产物 **`bridgeflow-nudger/dist/CodeFlow-Desktop.exe`**（`pack.cmd`）。
- **控制面板**：「团队」区域增加 **「同步角色模板」**（英文 **Sync role templates**），对应 **`POST /api/copy_templates`**，将内置 `templates/`（含当前团队的 `docs/agents/` 角色文档、`.cursor/rules`、`skills`）覆盖到已选项目目录。**更新角色请用此按钮，勿用「重置」**（重置会清配置、停巡检）。
- **文档**：**`HANDOVER-20260403.md`** 补充三套模板路径、同步与重置区别、**`codeflow-plugin` 为可选 MCP** 的说明。

### PWA（与桌面端版本号对齐）

- **`web/pwa/config.js`** 的 **`appVersion`** → **2.0.1**；根目录 **`config.js`**、**`index.html`**（`manifest.json` 缓存参数）、**`sw.js`** 与主源同步。

### Cursor 插件（可选）

- **`codeflow-plugin/.cursor-plugin/plugin.json`** → **2.0.1**（与主线版本号一致）。

---

## [2.0.0] - 2026-04-04

码流（CodeFlow）**改名后主版本对齐**：桌面端、PWA、Cursor 插件元数据统一 **2.0.0**。

### 版本号
- **桌面端**：`bridgeflow-nudger/main.py`、`web_panel.py` → **2.0.0**；打包产物仍为 **`dist/CodeFlow-Desktop.exe`**（`pack.cmd` / `build.spec`）。
- **PWA**：`web/pwa/config.js` 的 `appVersion` **2.0.0**；根目录 `config.js` / `index.html`（manifest 缓存参数）/ `sw.js` 与主源同步。
- **插件**：`codeflow-plugin/.cursor-plugin/plugin.json` → **2.0.0**。

### GitHub 仓库（PWA）
- 对外 PWA 仓库：**`joinwell52-AI/codeflow-pwa`**；Pages：**https://joinwell52-ai.github.io/codeflow-pwa/**（`.github/workflows/deploy-pwa.yml` 已同步 `external_repository`）。

### 中英双语文案
- **中文**：主标语「指令成流，智能随行」；副标语「手机驭 AI，指令达团队」；一句话简介见 `appSummary`。
- **英文**：`appTaglineEn` / `appSubtaglineEn` / `appSummaryEn`（与顶栏英文切换、`meta`/`manifest` 英段一致）。

### 品牌与配置路径
- **中文品牌名**：码流（CodeFlow）；**一句话简介** 见 `web/pwa/config.js`（`appSummary`）与 `manifest.json`（`description`）。
- **PWA**：`web/pwa/` 为唯一主源；仓库根目录静态副本与 `web/pwa/` 同步，便于静态托管对照。
- **中继**：默认 WebSocket 路径 `/codeflow/ws/`（生产环境需 Nginx/网关与客户端一致）。
- **团队配置**：优先 `docs/agents/codeflow.json`，仍兼容旧版 `bridgeflow.json`；高级巡检配置优先 `codeflow-nudger.json`，兼容 `bridgeflow-nudger.json`。

### 工作台 UI（原 v1.9.8 起）
- **工作台分栏**：宽屏（≥720px）支持左侧或右侧 **Agent 竖栏**（状态徽章 + 任务条数），标题栏 `⇄` 切换左右；点击角色后自动聚焦「发送任务」输入框，便于连续对话。

### 修复 / 增强（Desktop 巡检器 `bridgeflow-nudger/nudger.py`）
- **切换 Agent 更韧**：每轮内依次 **快捷键 → 点击角色 → Ctrl+Shift+P 搜索 `1-PM`/`2-DEV`/`3-QA`/`4-OPS` 并回车**，最多 **3 轮**整轮重试；每步后 OCR 验证，减少「发现不对仍继续」的误发。
- **预检「找不到 Cursor」偶发**：窗口枚举改为 **PROCESS_QUERY_LIMITED_INFORMATION + QueryFullProcessImageName**（降低 OpenProcess 失败率）、**允许标题暂为空**（Electron 偶发）、`find_cursor_window` **最多 4 次短重试**，减轻另一台电脑上「多刷新几次又好」的现象。
- **巡检器 v1.9.9**：`poll_interval` / `find_cursor_*` / `idle_check_every_n` / `stuck_check_every_n` 写入 **`bridgeflow-nudger.json`** 可调；主循环睡眠可被 **watchdog**（`use_file_watcher`，可选依赖）打断以更快响应新 `.md`；面板显示轮询秒数、watchdog 状态、预检 **Cursor 探测耗时**；新增 `requirements.txt`。
- **巡检可观测性**：`patrol_trace()` 环形缓冲 + **`GET /api/patrol_trace`**；面板 **「巡检轨迹」** 表格与 `[巡检]` 日志一致，精确到文件级、defer 原因、发送成败等阶段。
- **催办丢失**：因冷却或 Agent 忙碌跳过催办时，`FileWatcher` 已将文件记入 `_known`，若未加入待办队列则该任务**永远不会再被催办**；现合并 `_nudge_pending` 重试队列并设单次上限重试次数。
- **打招呼崩溃**：`first_hello` 等模板无 `{filename}` 占位符时仍调用 `.format(...)` 会触发 `ValueError`；现用 `_fmt_tpl` 安全格式化。
- **角色匹配**：任务收件人为 `DEV01` 等时，与 OCR 当前角色 `DEV` 不一致导致无法判定已激活；现统一经 `_role_key_for_task` 比较。

### 计划中
- GitHub Actions CI/CD（已配置 `.github/workflows/`）
- PWA GitHub Pages 自动部署

### 新增（插件 / Phase 2）
- **MCP 中继桥**：`BRIDGEFLOW_ROOM_KEY` 非空时启动后台线程，轮询 `docs/agents` 并通过 WebSocket 推送 `file_change`；接收 `command_from_admin` / `admin_command` 写入 `docs/agents/inbox/`
- **中继服务**：`server/relay/server.py` 增加事件类型 `file_change`、`agent_status`、`message_history`、`request_message_history`、`admin_command`（与 `command_from_admin` 同为定向投递）

---

## [v1.9.6] - 2026-04-04

### OCR 视觉增强 + 快捷键优先 + 文件推送优化

#### 新增 `cursor_vision.py` — Cursor 窗口视觉识别模块
- **自适应 OCR**：截图 Cursor 窗口 → 英中双语 OCR → 结构化分析 UI 状态
- **角色名模糊匹配**：空格/连字符/点号互通（`2 DEV` → `2-DEV`），正则驱动
- **Pinned 面板推断**：检测到 `Pinned` 标签后，从面板结构推断 OCR 漏掉的角色（如 1-PM 被转圈图标遮挡）
- **Agent 忙碌检测**：扫描 `Awaiting`/`Generating`/`Stop` 等关键词，判定 Agent 是否在工作中
- **角色状态读取**：竖排 Pinned 列表下方的状态文字提取（如 `Awaiting plan review`）

#### 巡检器 `nudger.py`
- **快捷键优先 + 视觉验证**：切换角色改为先按 `Ctrl+Alt+N` → OCR 验证 → 失败则点击角色名兜底 → 再验证，最多重试 2 次
- **忙碌免打扰**：催办前检测 Agent 忙碌状态，忙碌时自动推迟，不打断工作中的 Agent
- **文件推送按天过滤**：`tasks/reports/issues` 三文件夹全部推给 PWA，新增 `today_*` 计数字段
- **轮询节奏优化**：`poll_interval` 5s，`nudge_cooldown` 15s，不再频繁催办

#### PWA `index.html`
- **Dashboard 当天统计**：使用后端 `today_tasks`/`today_reports`/`today_issues` 显示当日数据
- **背景色统一**：`.app-shell` 与"我的"页面统一深蓝渐变背景
- **manifest 背景同步**：`background_color`/`theme_color` 更新为 `#162540`/`#1c2e4a`

#### 版本号统一
- PWA `config.js`、Desktop `main.py`、`web_panel.py` 全部升至 `1.9.6`

---

## [PWA v1.9.0 + Desktop v1.0.1] - 2026-04-03

### 通信链路打通（PWA ↔ 中继 ↔ PC Desktop）

#### 中继服务 `server/relay/server.py`
- **白名单扩展**：`ALLOWED_EVENTS` 新增 9 个事件类型：`start_patrol`、`stop_patrol`、`patrol_status`、`patrol_state`、`request_bind_state`、`request_bind_code`、`bind_state`、`execute_desktop_action`、`desktop_action_result`
- **定向投递扩展**：`start_patrol`、`stop_patrol`、`patrol_status`、`request_bind_state`、`request_bind_code`、`execute_desktop_action` 加入定向路由（需 `target_device_id`）

#### PC Desktop `bridgeflow-nudger/nudger.py`
- **`recv_loop` 全面扩展**：从只处理 `command_from_admin` 扩展为处理 8 种事件类型
- **`request_dashboard`**：回发 `dashboard_state`（扫描 tasks/reports 目录，解析 YAML front matter，返回任务列表 + 统计数据）
- **`start_patrol` / `stop_patrol`**：远程启停巡检（非阻塞线程），回发 `patrol_state`
- **`patrol_status`**：回发当前巡检状态（运行中/轮次）
- **`request_bind_state`**：回发 `bind_state`（读 bridgeflow.json 设备列表）
- **`request_bind_code`**：写入绑定设备到 bridgeflow.json，回发 `bind_state`
- **`execute_desktop_action`**：支持 `focus_cursor` / `inspect` / `start_work` / `restart` 四种桌面动作

#### PWA `web/pwa/index.html`
- **`hello` 修复**：补全 `device_id: localMobileDeviceId`，确保 PWA 出现在中继 `device_roster` 中
- **巡检控制修复**：`start_patrol`、`stop_patrol`、`patrol_status`、`execute_desktop_action` 全部补上 `target_device_id`
- **连接时序优化**：`onopen` 只发 `hello` + `request_device_roster`；收到 `device_roster` 后再 `requestDashboard` + `requestPatrolStatus` + 启动轮询
- **轮询频率统一**：巡检状态轮询统一为 8 秒，`onclose` 时自动清除
- **版本号**：`config.js` 升至 `1.9.0`

#### Desktop 面板 `panel/index.html`
- **i18n 国际化**：完整中英文切换（~60 个翻译词条），Header 语言切换按钮，`localStorage` 持久化
- **预检翻译**：后端返回的中文预检项名称/详情在前端做映射翻译

#### 角色文档体系（3 套团队 × 中英双语）
- **24 个角色定义文档**：`templates/agents/` 下按团队分目录
  - `dev-team/`：PM / DEV / QA / OPS（各 `.md` + `.en.md`）
  - `media-team/`：PUBLISHER / COLLECTOR / WRITER / EDITOR（各 `.md` + `.en.md`）
  - `mvp-team/`：MARKETER / RESEARCHER / DESIGNER / BUILDER（各 `.md` + `.en.md`）
- **初始化自动复制**：`_copy_templates(project_dir, team_id)` 按选定团队复制对应角色文档到客户项目 `docs/agents/`
- **预检增强**：角色文件检查从只看 rules + skills 扩展为同时检查角色文档是否存在
- **切换项目 / 重新拷贝**：`_api_change_project` 和 `_api_copy_templates` 均读取当前团队 ID 传递

#### 文档更新
- **README.md 重写**：从旧版 PyPI 包架构更新为三模块独立架构（Desktop + Plugin + PWA），更新目录结构、快速开始、团队模板说明、文件协议说明

---

## [Desktop v1.0.0] - 2026-04-03

### 架构迁移：PyPI 包 → 三模块独立架构

- **删除** `src/bridgeflow/` 整个 PyPI 包源码目录（已迁移到 `bridgeflow-nudger/` + `bridgeflow-plugin/`）
- **删除** `pyproject.toml`、`scripts/bfstart.bat`、`scripts/bfstart.sh`（不再需要）
- **删除** 旧版中文文档（`docs/GitHub发布说明.md`、`docs/PyPI发布说明.md`、`docs/产品设计说明.md`），已重新整理为 `docs/user-manual.md` + `docs/config-reference.md`
- **清理** `_smoke_test/` 测试数据
- **新增** `bridgeflow-nudger/` — PC Desktop 独立模块
- **新增** `bridgeflow-plugin/` — Cursor MCP 插件模块

### BridgeFlow Desktop — 独立 EXE 控制面板

全新独立桌面端，包含 Nudger（唤醒器）、Web Panel（控制面板）、Relay Client（中继客户端），打包为单文件 EXE。

### 核心架构
- **快捷键驱动唤醒**：使用 `Ctrl+L` 聚焦 Cursor AI 对话输入框，不依赖坐标猜测，支持任意窗口尺寸和分辨率
- **Tab 切换**：`Ctrl+Alt+1~4` 切换 Agent Tab（1-PM / 2-DEV / 3-QA / 4-OPS），通过 Cursor keybindings.json 自动配置
- **任务生命周期**：TaskTracker 追踪任务状态（执行中 → 可能卡住 → 超时 → 已过期），超 24h 自动标记过期
- **窗口焦点恢复**：唤醒操作后自动恢复之前的前台窗口

### Web Panel（http://127.0.0.1:18765）
- **设计系统**：Dark Mode OLED 方案，Fira Sans + Fira Code 字体，品牌青色 `#22d3ee`
- **两步设置向导**：步骤1 选择项目文件夹 → 步骤2 选择团队模板 → 保存设置
- **环境预检（6 项）**：项目目录、目录结构、团队配置、角色文件（rules + skills）、Cursor 窗口、快捷键
- **巡检控制**：启动（运行中保持青色亮灯）、停止、环境预检、重置（二次确认弹窗）
- **任务概览**：4 张数据卡片（待处理任务 / 完成报告 / 问题记录 / 唤醒统计）
- **任务流水线**：实时显示任务状态（执行中 / 可能卡住 / 超时 / 已完成 / 已过期）
- **文件浏览**：任务单 / 报告 / 问题 / 归档四个 Tab，每个文件可点击"查看"预览 Markdown 内容
- **手机连接**：房间密钥显示 + QR 码生成 + 已绑定设备列表 + 解绑 / 重新生成密钥
- **实时日志**：SSE 推送，INFO / WARNING / ERROR 分色显示
- **配置面板**：中继地址、轮询间隔、唤醒冷却等
- **自定义确认弹窗**：深色毛玻璃风格，替代浏览器原生 confirm()
- **版权标识**：© 2026 joinwell52-AI

### 后端 API
- `GET /api/status` — 面板状态（运行状态 / 团队 / 任务计数）
- `GET /api/preflight` — 环境预检（6 项检查 + 可操作标记）
- `GET /api/pipeline` — 任务流水线（含过期状态）
- `GET /api/files?dir=` — 文件列表（tasks / reports / issues / log）
- `GET /api/file_content?dir=&name=` — 读取 MD 文件内容
- `GET /api/teams` — 团队模板列表
- `GET /api/devices` — 已绑定设备
- `GET /api/logs` — SSE 实时日志
- `POST /api/start` / `stop` — 启动 / 停止巡检
- `POST /api/setup` — 初始化团队配置
- `POST /api/change_project` — 切换项目文件夹
- `POST /api/copy_templates` — 拷贝角色文件到项目
- `POST /api/reset` — 重置配置（清除本地状态）
- `POST /api/regenerate_key` — 重新生成房间密钥
- `POST /api/unbind` — 解绑设备

### 技术栈
- Python 3.12 + PyInstaller 单文件打包
- 零额外依赖 Web 服务（`http.server` + `ThreadingMixIn`）
- `pyautogui` + `pywin32` 窗口控制
- Google Fonts CDN（Fira Code / Fira Sans）
- `qrcode-generator` JS 库（QR 码生成）

---

## [0.2.6] - 2026-04-02

### 改进
- **扫码自动确认绑定**：手机扫码后 PC 端自动批准，无需手动确认

---

## [0.2.5] - 2026-04-02

### 修复
- **扫码绑定无法识别**：二维码内容从 161 字符（QR Version 9, 61x61）精简到 37 字符（Version 3, 37x37），scale 从 4 改到 8，识别率大幅提升
- PWA 扫码兼容新旧两种二维码格式（`bf:MC|DID` 和 `bridgeflow://bind?...`）
- PWA 预加载 jsQR 库（页面加载时即开始，不等点扫码才加载）
- 扫描间隔从 300ms 缩短到 200ms，增加 `inversionAttempts: 'attemptBoth'`

### 删除
- PWA 移除测试数据（`DEMO_META` 和 `test-data/` 目录），正式版不再显示假数据

---

## [0.2.4] - 2026-04-02

### 修复
- **首次运行不再散落文件到桌面**：`bridgeflow run` 检测到当前目录无配置时，自动创建 `BridgeFlow/` 子文件夹并在其中初始化，所有文件（配置、运行时、rules、tasks、reports）整齐归入项目文件夹

---

## [0.2.3] - 2026-04-02

### 新增
- **本地运维仪表盘（Ops Panel）**：`bridgeflow run` 启动后自动打开 `http://localhost:18765`，
  网页面板集中展示所有环境预检结果，替代旧版 `bfstart.bat/sh` 脚本方案
  - `GET /api/preflight` — 一键预检：Python、Cursor安装/运行、4 Agent 窗口、PyPI 网络、Relay 网络、版本对比
  - `POST /api/upgrade` — 网页一键升级 `pip install --upgrade bridgeflow`（后台执行、实时日志）
  - `GET /api/upgrade-status` — 轮询升级进度和输出
  - `POST /api/restart` — 网页一键重启 BridgeFlow 进程
- 仪表盘 UI 全新设计：预检面板 + 版本升级 + 连接状态 + 扫码绑定 + 任务统计

### 变更
- **`bridgeflow run` 不再阻断启动**：移除 Cursor 未安装/Agent 未就绪的交互式阻断检查，
  所有环境检测改由仪表盘网页展示，用户可按提示自行修复后点击 Re-check
- 移除 `--auto-upgrade` 命令行参数（升级操作统一移至仪表盘）
- 移除 `_make_launcher()` 函数（不再生成 `start.bat/start.sh`）

### 删除
- `scripts/bfstart.bat` — 已废弃，改用仪表盘方案
- `scripts/bfstart.sh` — 已废弃，改用仪表盘方案

---

## [0.2.2] - 2026-04-02

### 修复
- **`bridgeflow run` 自动初始化 bug**：`config_path` 未 resolve 成绝对路径，导致新机器首次运行报 `FileNotFoundError`
- **Windows CMD 编码崩溃**：所有 Python 模块的 console 输出（print/input/error）全部改为纯 ASCII 英文，彻底解决 GBK 编码环境下的 `UnicodeEncodeError`
  - 涉及文件：`cli.py`、`version_check.py`、`env_check.py`、`config.py`、`cursor_probe.py`、`runner.py`、`ws_client.py`、`file_protocol.py`、`patrol.py`、`task_writer.py`、`executor.py`、`status_store.py`、`binding.py`
- **PWA 状态匹配兼容**：`progress` 和 `type` 字段的正则匹配同时支持中英文值（`pending`/`in_progress`/`replied`/`task`）

### 变更
- PWA 版本号升至 1.8.0

---

## [0.2.1] - 2026-04-02

### 新增
- **全套英文文档**：所有中文文档均提供对应英文版（`.en.md` / `.en.mdc`）
  - `docs/user-manual.en.md` — 用户操作手册英文版
  - `docs/config-reference.en.md` — 配置参考英文版
  - `docs/agents/README.en.md` — Agent 文件结构英文版
  - `docs/agents/ADMIN-01.en.md` / `PM-01.en.md` / `DEV-01.en.md` / `OPS-01.en.md` / `QA-01.en.md` — 5 个角色文件英文版
  - `.cursor/rules/*.en.mdc` — 6 个 Cursor 规则文件英文版
  - `src/bridgeflow/data/rules/*.en.mdc` — 5 个包内规则模板英文版
- OPS01 角色补全至配置参考文档的 `roles` 示例中

### 修复
- **Agent 命名全局统一**为 `1-PM / 2-DEV / 3-QA / 4-OPS`（代码 `cursor_probe.py`、配置模板、文档全部对齐）
- `config-reference.md` 中 `patrol.role_to_chat` 示例映射错误（`QA01:"3-QA"` 缺失），补齐 `OPS01` 映射
- `config-reference.md` 中 `roles` 块缺少 `OPS01` 条目
- `.cursor/rules/ops-bridge.mdc` 的 `alwaysApply` 由 `false` 改为 `true`（与交底要求一致）
- `user-manual.md` 故障排查中 `start.bat` 改为 `bfstart.bat`
- `README.md` 目录结构与实际文件名不一致（旧中文文件名 → 当前英文文件名）
- `README.md` 底部链接指向已不存在的旧文件名

### 变更
- `config-reference.md` 版本号从 v0.1.8 更新为 v0.2.1

---

## [0.2.0] - 2026-03-21

### 新增
- **自动生成唯一房间号**：`bridgeflow init` 自动生成 `bf-{主机名}-{8位随机hex}`，
  每台机器天然隔离，不再共用 `bridgeflow-default` 公共房间
- 房间号嵌入 QR 二维码，手机扫码后自动同步，无需手填
- 启动横幅增加房间号显示
- init 完成后提示"手机扫描二维码可自动同步房间号"
- `scripts/bfstart.bat`（Windows）/ `scripts/bfstart.sh`（macOS/Linux）：
  检查 Python → 安装 bridgeflow → 自动运行，双击一步到位

---

## [0.1.9] - 2026-03-21

### 新增
- `bridgeflow run` 发现新版时交互询问是否立即升级并重启（`check_update_interactive`）
  - 升级成功后自动重启进程（`os.execv` / `subprocess` 双保险）
  - `--auto-upgrade` 参数：跳过确认直接升级（无人值守/脚本场景）
- `bridgeflow run` 找不到配置文件时自动执行 `init`（无需手动两步操作）
- `bridgeflow init` 自动生成双击启动脚本
  - Windows：`start.bat`
  - macOS / Linux：`start.sh`
- 启动横幅显示当前版本号（`v0.1.x`）
- `bridgeflow init` 完成后打印当前版本号和升级命令
- `__init__.py` 版本号修正为 `0.1.8`（之前误写为 `0.1.0`）

---

## [0.1.8] - 2026-03-21

### 新增
- 服务端二维码生成（`segno` 库），本地仪表盘直接展示 QR 图片
- 二维码内容为 deep link（`bridgeflow://bind?...`），包含中继地址/机器码/房间/设备 ID
- 手机端 PWA 扫码功能（`jsQR`，双 CDN 备用：`cdn.jsdelivr.net` + `unpkg.com`）
- 扫码后自动解析参数并发送绑定请求
- 全部角色 `.mdc` 规则文件补全至 `.cursor/rules/`
- 项目独立化：`D:\BridgeFlow` 作为独立 Git 仓库
- `pyproject.toml` 添加 GitHub/PyPI/文档 URLs
- `README.md` 添加 PyPI/GitHub 徽章
- 新增 `docs/GitHub发布说明.md`
- 完善 `docs/PyPI发布说明.md`（含 GitHub Actions 流程）
- 新增 `.github/workflows/publish.yml`（tag 触发自动发布 PyPI）
- 新增 `.github/workflows/deploy-pwa.yml`（main 推送自动部署 PWA）

### 修复
- 扫码绑定：`sendMsg` 错误调用改为正确的 `sendEvent`
- Service Worker 缓存版本强制升级（每次改动同步升 `appVersion`）

---

## [0.1.7] - 2026-03-17

### 新增
- Windows 注册表检测 Cursor 安装路径（`winreg` 模块）
- 跨平台 Cursor 检测：Windows / macOS / Linux 三路兼容

### 修复
- 非标准安装路径（如 `D:\Program Files\cursor\`）仍能正确检测 Cursor

---

## [0.1.6] - 2026-03-15

### 新增
- 本地 HTTP 仪表盘（`localhost:18765`）
- `bridgeflow run` 自动打开浏览器到仪表盘
- 仪表盘 `/api/status` 接口（JSON）
- `env_check.py` 跨平台环境检测模块

---

## [0.1.5] - 2026-03-12

### 修复
- `bridgeflow run` 连接状态回调，不再静默失败
- `ws_client.py` 增加 `on_connected` / `on_disconnected` 回调

---

## [0.1.4] - 2026-03-10

### 新增
- `bridgeflow run` 启动横幅（OS / Python / Cursor 检测 / 设备 ID / 机器码）
- WebSocket 连接成功/断开控制台输出

---

## [0.1.3] - 2026-03-08

### 新增
- `bridgeflow init` 自动复制 `.cursor/rules/` 规则文件（5 个角色）
- `pm-bridge.mdc`、`dev-bridge.mdc`、`ops-bridge.mdc`、`qa-bridge.mdc` 规则文件

---

## [0.1.2] - 2026-03-06

### 修复
- `bridgeflow init` 从已安装包的 `data/` 目录正确读取 `bridgeflow_config.json`
- 修复 `FileNotFoundError` 路径问题

---

## [0.1.1] - 2026-03-04

### 修复
- 包数据文件路径修正（`data/*.json`、`data/rules/*.mdc`）

---

## [0.1.0] - 2026-03-01

### 初版发布
- Python CLI：`bridgeflow init` / `run` / `write-admin-task` / `write-reply`
- WebSocket 轻量中继（可集成到 FastAPI/Starlette 后端或独立运行）
- 手机端 PWA（GitHub Pages 托管）
- 桌面桥接器：任务文件写入 / 回执扫描 / 摘要推送
- 设备绑定机制（生成绑定码 / 确认 / 解绑）
- 桌面动作：`focus_cursor` / `inspect` / `start_work`
- agent_bridge 文件协议（`TASK-YYYYMMDD-序号-发送方-to-接收方.md`）
- 5 个角色 Cursor 规则文件（ADMIN / PM / DEV / OPS / QA）
