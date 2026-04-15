# V2EX 帖子 — 分享创造

**节点:** /t/create 或 /t/share
**标题:** 码流 CodeFlow v2.10 — CDP 巡检引擎 10ms 读取 Cursor DOM，手机指挥 AI 团队写代码（开源）

---

各位好！分享我做的开源项目：**码流（CodeFlow）v2.10.1**。

### 一句话介绍

用手机给 AI 团队发指令，PC 端自动执行，CDP 巡检引擎 10ms 读 DOM，零数据库。

### v2.10 重磅更新：CDP 巡检引擎

之前用 OCR 监控 Cursor Agent，延迟 300-800ms，精度约 90%。现在改用 Chrome DevTools Protocol：

| | OCR（旧） | CDP（新） |
|---|---|---|
| 精度 | ~90% | **100%** |
| 延迟 | 300-800ms | **10-15ms** |
| 识别方式 | 截屏 + 图像识别 | DOM 查询 + aria 属性 |
| 忌磌检测 | 像素猜测转圈 | Stop 按钮可见性 |
| 点击方式 | pyautogui 屏幕坐标 | dispatchMouseEvent 窗口坐标 |

设计原则：CDP 做主力，OCR 纯粹作为降级通道。每个 CDP 步骤失败都自动回退到 OCR，永不卡死。

### 背景

在 Cursor IDE 里跑了 4 角色 AI 团队（PM + DEV + QA + OPS），17 天干了 87 人天的活，线上发版 91 次，零事故。

### 产品组成

- **桌面端 EXE**（v2.10.1，~35MB）：CDP 巡检引擎 + OCR 降级，自动催办卡住任务，全量中英双语 UI
- **手机端 PWA**（v2.3.1）：发任务、看状态、读报告、扫码绑定，离线可用
- **MCP 插件**：在 Cursor 对话里初始化团队、派任务、读报告
- **WebSocket 中继**：手机 ↔ PC 实时同步

### 核心创新：文件名即协议

```
TASK-20260414-003-PM-to-DEV.md
```

一个文件名 7 个字段。不需要数据库、不需要消息队列。

### 4 套团队模板

- `dev-team`：PM / DEV / QA / OPS
- `media-team`：WRITER / EDITOR / PUBLISHER / COLLECTOR
- `mvp-team`：MARKETER / RESEARCHER / DESIGNER / BUILDER
- `qa-team`：PM / AUTO-TESTER / PERF-TESTER / SECURITY-TESTER

### 快速体验

1. 下载 EXE：https://github.com/joinwell52-AI/codeflow-pwa/releases
2. 国内镜像：https://gitee.com/joinwell52/cursor-ai/releases
3. 手机 PWA：https://joinwell52-ai.github.io/codeflow-pwa/
4. 产品主页：https://joinwell52-ai.github.io/codeflow-pwa/promotion/
5. GitHub：https://github.com/joinwell52-AI/codeflow-pwa
6. CDP 技术文档：https://github.com/joinwell52-AI/codeflow-pwa/blob/main/docs/cdp-multi-agent.md

v2.10.1 新增：全量 i18n 支持（130+ 翻译键），所有 API 消息、巡检轨迹、面板 UI 一键切换中英文。GitHub 社区健康度 100%。

MIT 开源，中英双语。欢迎 Star 和反馈！

### 方法论

理论基础在这里：https://joinwell52-ai.github.io/joinwell52/
