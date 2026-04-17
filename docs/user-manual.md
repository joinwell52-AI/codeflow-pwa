# 码流（CodeFlow）用户操作手册

**版本：** v2.12.0 ｜ **更新日期：** 2026-04-06

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

获取 `CodeFlow-Desktop.exe`（约 35MB），放在任意位置。支持自动更新：启动后自动检测 GitHub/Gitee 最新版本并后台下载。

下载地址：
- **国内（推荐）**：https://gitee.com/joinwell52/cursor-ai/releases
- **GitHub**：https://github.com/joinwell52-AI/codeflow-pwa/releases

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
- 查看任务清单和报告（分类：任务单 / 报告 / 问题 / 归档）
- 查看任务 MD 原文内容
- 发送任务给指定角色
- 远程桌面操作（聚焦 Cursor / 查看状态 / 开始工作）
- 查看团队成员状态和任务分布

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

## 七、Agent 工作实况（手机端只读监控）

> v2.11.0 新增，v2.12.0 增强

点击手机 PWA 团队卡片中的任意角色，即可打开该角色的**工作实况面板**。

### 功能说明

| 功能 | 说明 |
|------|------|
| 实时状态 | 绿色脉冲 = 工作中，灰色 = 空闲，黄色 = 等待审批 |
| 消息气泡 | 显示 Agent 最近 20 条对话，用户/Agent 左右区分 |
| Markdown 渲染 | 加粗、列表、代码块、标题等格式与 PC 端一致 |
| 队长标识 | 主控角色卡片右上角显示金色 ★ |

### 注意事项

- **只读监控**：面板底部标注"只读监控"，不能在此发送指令
- **需要 CDP**：Desktop 必须以 `--remote-debugging-port=9222` 启动 Cursor 才能读取消息内容；否则只显示角色状态，无消息详情
- **数据延迟**：约 5 秒一次推送，非实时

### 团队卡片说明

- 主控角色（队长）卡片显示 **★** 金色星标
- 每个卡片显示：当前状态徽章 + 待处理任务数
- 点击卡片打开工作实况面板

---

## 八、自动故障恢复

巡检器内置多种自愈机制，大部分异常无需人工干预：

| 检测场景 | 检测方式 | 自动动作 |
|---|---|---|
| Cursor Connection Error | OCR 扫描聊天区域 | 自动 Reload Window |
| Extension Host 卡死 | OCR 检测 "Waiting for extension host" | 自动 Reload Window |
| Agent 任务卡住 | 任务文件超过 10 分钟未更新 | 先 Reload Window，再发催促消息 |
| Agent 等待确认 | OCR 检测"要我继续"等关键词 | 自动发送"继续"指令 |
| WebSocket 断连 | 连接异常检测 | 自动重连（指数退避） |
| PC 中继限流 | 消息发送频率控制 | 自动降频（15 秒间隔） |

> **Reload Window 冷却期**：120 秒内最多触发一次，避免反复刷新。可在 `codeflow-nudger.json` 中通过 `conn_error_reload_cooldown_s` 调整。

---

## 九、故障排查

### Cursor 窗口检测不到

- 确认 Cursor 已打开且窗口可见（不能最小化到托盘）
- 窗口标题必须包含 "Cursor" 字样

### 快捷键不生效

- 确认 Cursor 的 `keybindings.json` 中已写入 `Ctrl+Alt+1~4`
- 预检会自动写入，也可手动检查：`%APPDATA%\Cursor\User\keybindings.json`

### PWA 数据不更新 / 显示 PC 离线

1. 等待 10-15 秒，Desktop 重连后会自动推送（2s/5s/12s 三次重试）
2. 点击 PWA 顶部状态栏旁的小 **↻** 图标手动刷新
3. 如以上无效，强制刷新 PWA 页面（Safari 长按刷新 → 清除缓存并刷新）
4. **不需要**重新扫码绑定，room_key 已存储在本地

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

## 十、文件说明

| 文件 | 说明 |
|------|------|
| `CodeFlow-Desktop.exe` | 主程序，双击运行，约 35MB，支持自动更新 |
| `docs/agents/codeflow.json` | 团队配置（角色、房间密钥、中继地址；兼容 `codeflow.json`） |
| `docs/agents/tasks/*.md` | 任务单文件 |
| `docs/agents/reports/*.md` | 完成报告文件 |
| `docs/agents/issues/*.md` | 问题记录文件 |
| `docs/agents/log/*.md` | 历史归档文件 |
| `.cursor/rules/*.mdc` | Cursor Agent 规则文件 |
| `.cursor/skills/*/SKILL.md` | Cursor Agent 技能文件 |
