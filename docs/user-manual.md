# 码流（CodeFlow）用户操作手册

**版本：** v2.0.0 ｜ **更新日期：** 2026-04-04

---

## 一、系统要求

| 项目 | 要求 | 说明 |
|------|------|------|
| 操作系统 | Windows 10 或以上 | 暂不支持 macOS / Linux |
| Cursor | v3.0 或以上（已安装） | 下载地址：https://cursor.com |
| 屏幕分辨率 | 1920×1080 或以上 | 需要同时显示多个 Agent Tab |
| 网络 | 可访问外网 | 中继通信需要 WebSocket 连接 |

> **不需要安装 Python**——直接运行打包好的 EXE 即可。

---

## 二、前置准备

### 2.1 安装 Cursor

如果电脑上还没有 Cursor：

1. 打开 https://cursor.com
2. 下载 Windows 版安装包
3. 安装完成后打开 Cursor，登录账号

### 2.2 准备项目文件夹

选择一个本地文件夹作为团队协作目录，例如：

```
D:\my-ai-team\
```

这个文件夹将用来存放：
- `docs/agents/` — 任务单、报告、问题记录
- `.cursor/rules/` — Agent 协作规则
- `.cursor/skills/` — Agent 技能文件

> **任意盘符、任意路径均可**，只要你记得在哪就行。

### 2.3 获取码流 Desktop（CodeFlow Desktop）

获取 `CodeFlow-Desktop.exe`（约 50MB），放在任意位置。

---

## 三、首次启动（约 3 分钟）

### 步骤 1：双击运行 EXE

双击 `CodeFlow-Desktop.exe`，浏览器自动打开控制面板：

```
http://127.0.0.1:18765
```

### 步骤 2：选择项目文件夹

面板显示设置向导，点击 **Browse** 选择你准备好的项目文件夹。

### 步骤 3：选择团队模板

从 3 套预设团队中选一套：

| 模板 | 角色 | 适合场景 |
|------|------|----------|
| 软件开发团队 | PM + DEV + QA + OPS | 软件项目开发 |
| 自媒体团队 | PUBLISHER + COLLECTOR + WRITER + EDITOR | 内容创作 |
| 创业MVP团队 | MARKETER + RESEARCHER + DESIGNER + BUILDER | 产品验证 |

点击 **保存** 后，系统自动生成：

```
你的项目文件夹/
├── .cursor/
│   ├── rules/codeflow-core.mdc          ← Agent 协作协议（旧版可能为 CodeFlow-core.mdc）
│   ├── rules/codeflow-patrol.mdc        ← 自动巡检规则（旧版可能为 CodeFlow-patrol.mdc）
│   └── skills/file-protocol/SKILL.md    ← 文件协议技能
├── docs/agents/
│   ├── codeflow.json                    ← 团队配置（兼容旧名 codeflow.json）
│   ├── PM.md / PM.en.md                 ← 角色定义（中英双语）
│   ├── DEV.md / DEV.en.md
│   ├── QA.md / QA.en.md
│   ├── OPS.md / OPS.en.md
│   ├── tasks/                           ← 任务单目录
│   ├── reports/                         ← 完成报告目录
│   ├── issues/                          ← 问题记录目录
│   └── log/                             ← 历史归档目录
```

### 步骤 4：环境预检

面板自动执行 6 项检查：

| 检查项 | 说明 | 不通过怎么办 |
|--------|------|-------------|
| 项目目录 | 文件夹是否存在 | 重新选择文件夹 |
| 目录结构 | tasks / reports / issues / log 是否存在 | 点"修复" |
| 团队配置 | codeflow.json 是否生成 | 重新选择团队 |
| 角色文件 | rules + skills + 角色文档是否就绪 | 点"拷贝" |
| Cursor 窗口 | 是否检测到 Cursor 正在运行 | 先打开 Cursor |
| 快捷键 | Ctrl+Alt+1~4 是否已配置 | 自动写入 |

**6 项全绿 = 环境就绪。** 须全部通过后才能点击面板上的「启动巡检」；若有红项，先在 Cursor / 项目中按上表修正，再重新预检直至全绿。

### 步骤 5：用 Cursor 打开项目文件夹

1. 打开 Cursor
2. File → Open Folder → 选择你的项目文件夹
3. 在 Chat 面板创建 4 个 Agent Tab

**以软件开发团队为例，名称必须完全一致：**

| 编号 | Tab 名称 | 角色 |
|------|----------|------|
| 1 | `1-PM` | 项目经理 |
| 2 | `2-DEV` | 开发工程师 |
| 3 | `3-QA` | 测试工程师 |
| 4 | `4-OPS` | 运维工程师 |

> 操作方法：点 Chat 面板的 **「+」** 新建，再点名称重命名。

### 步骤 6：启动巡检

回到控制面板（`http://127.0.0.1:18765`），点击 **启动** 按钮。

启动后：
- 按钮变为青色亮灯状态
- Nudger 开始监听 `docs/agents/tasks/` 和 `reports/` 目录
- 有新任务文件落入时，自动用快捷键切换到对应 Agent Tab 并唤醒

**首次启动完成！**

---

## 四、手机绑定（可选）

### 4.1 打开 PWA

手机浏览器打开：

```
https://joinwell52-ai.github.io/codeflow-pwa/
```

建议添加到主屏幕：
- **iOS Safari：** 分享按钮 → "添加到主屏幕"
- **Android Chrome：** 右上角菜单 → "添加到主屏幕"

### 4.2 扫码绑定

1. PC 控制面板 → 手机连接区域 → 显示二维码
2. 手机 PWA → 点 **「我的」** → 点 **「扫码绑定 PC」**
3. 对准二维码扫描
4. 绑定成功，手机可以远程控制 PC

### 4.3 手机能做什么

- 远程启动 / 停止巡检
- 查看任务清单和报告
- 发送任务给指定角色
- 远程桌面操作（聚焦 Cursor / 查看状态 / 开始工作）

---

## 五、日常使用

每次使用只需：

1. **双击 `CodeFlow-Desktop.exe`**
2. **打开 Cursor**（确保 4 个 Agent Tab 在）
3. **点「启动」**

> 如果之前设置过项目文件夹和团队，不需要重新配置，直接启动。

---

## 六、控制面板功能一览

| 区域 | 功能 |
|------|------|
| 巡检控制 | 启动 / 停止 / 环境预检 / 重置 |
| 任务概览 | 待处理任务 / 完成报告 / 问题记录 / 唤醒统计 |
| 任务流水线 | 实时显示任务状态（执行中 / 可能卡住 / 超时 / 已完成） |
| 文件浏览 | 任务单 / 报告 / 问题 / 归档，可点击查看 Markdown 内容 |
| 手机连接 | 二维码 + 已绑定设备列表 + 解绑 |
| 实时日志 | INFO / WARNING / ERROR 分色显示 |
| 设置 | 中继地址 / 轮询间隔 / 语言切换（中/英） |

---

## 七、故障排查

### Cursor 窗口检测不到

- 确认 Cursor 已打开且窗口可见（不能最小化到托盘）
- 窗口标题必须包含 "Cursor" 字样

### 快捷键不生效

- 确认 Cursor 的 `keybindings.json` 中已写入 `Ctrl+Alt+1~4`
- 预检会自动写入，也可手动检查：`%APPDATA%\Cursor\User\keybindings.json`

### 手机扫码没反应

1. 确认已授予浏览器摄像头权限
2. 确认 PWA 右上角连接灯是绿色（先连上中继再扫码）
3. 刷新面板页面重新生成二维码

### 面板打不开

- 确认 EXE 正在运行（命令行窗口没关）
- 确认浏览器访问的是 `http://127.0.0.1:18765`
- 如果端口被占用，关闭其他占用 18765 端口的程序

### 重新选择项目 / 换团队

点控制面板右下角 **重置** 按钮（需二次确认），然后重新走向导。

---

## 八、文件说明

| 文件 | 说明 |
|------|------|
| `CodeFlow-Desktop.exe` | 主程序，双击运行，约 50MB |
| `docs/agents/codeflow.json` | 团队配置（角色、房间密钥、中继地址；兼容 `codeflow.json`） |
| `docs/agents/tasks/*.md` | 任务单文件 |
| `docs/agents/reports/*.md` | 完成报告文件 |
| `docs/agents/issues/*.md` | 问题记录文件 |
| `docs/agents/log/*.md` | 历史归档文件 |
| `.cursor/rules/*.mdc` | Cursor Agent 规则文件 |
| `.cursor/skills/*/SKILL.md` | Cursor Agent 技能文件 |
