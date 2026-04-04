# Changelog

BridgeFlow 版本历史，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [Unreleased]

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
