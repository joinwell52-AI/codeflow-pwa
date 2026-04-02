# Changelog

BridgeFlow 版本历史，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [Unreleased]

### 计划中
- GitHub Actions CI/CD（已配置 `.github/workflows/`）
- PyPI 正式上传（准备中）
- PWA GitHub Pages 自动部署

---

## [0.2.0] - 2026-03-21

### 新增
- **自动生成唯一房间号**：`bridgeflow init` 自动生成 `bf-{主机名}-{8位随机hex}`，
  每台机器天然隔离，不再共用 `bridgeflow-default` 公共房间
- 房间号嵌入 QR 二维码，手机扫码后自动同步，无需手填
- 启动横幅增加房间号显示
- init 完成后提示"手机扫描二维码可自动同步房间号"
- `scripts/一键安装启动.bat`（Windows）/ `scripts/一键安装启动.sh`（macOS/Linux）：
  检查 Python → 安装 bridgeflow → 自动运行，双击一步到位

---

## [0.1.9] - 2026-03-21

### 新增
- `bridgeflow run` 发现新版时交互询问是否立即升级并重启（`check_update_interactive`）
  - 升级成功后自动重启进程（`os.execv` / `subprocess` 双保险）
  - `--auto-upgrade` 参数：跳过确认直接升级（无人值守/脚本场景）
- `bridgeflow run` 找不到配置文件时自动执行 `init`（无需手动两步操作）
- `bridgeflow init` 自动生成双击启动脚本
  - Windows：`启动BridgeFlow.bat`
  - macOS / Linux：`start_bridgeflow.sh`
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
