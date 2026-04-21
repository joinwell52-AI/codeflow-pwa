# Contributing to CodeFlow / 贡献指南

[English](#english) | [中文](#中文)

---

## English

Thank you for your interest in contributing to CodeFlow!

### Ways to Contribute

- **Bug Reports** — Open an [Issue](https://github.com/joinwell52-AI/codeflow-pwa/issues) with reproduction steps
- **Feature Requests** — Describe the use case and expected behavior
- **Code** — Fix bugs or implement features via Pull Requests
- **Documentation** — Improve docs, fix typos, add translations
- **Testing** — Report compatibility issues on different OS / Cursor versions

### Getting Started

1. **Fork** this repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<your-username>/codeflow-pwa.git
   cd codeflow-pwa
   ```
3. Create a **feature branch**:
   ```bash
   git checkout -b feat/your-feature
   ```

### Development Setup

**Desktop (Python 3.12)**
```bash
cd codeflow-desktop
pip install pyautogui pyperclip pywin32 websockets winocr Pillow watchdog psutil
python main.py
```

**PWA (Static HTML)**
```bash
# No build step — open web/pwa/index.html in browser
# Or use a local server:
python -m http.server 8080 -d web/pwa
```

**MCP Plugin**
```bash
cd codeflow-plugin
pip install -r requirements.txt
```

### Project Structure

```
BridgeFlow/
├── codeflow-desktop/    # Desktop app (Python, PyInstaller)
├── codeflow-plugin/     # Cursor MCP plugin
├── web/pwa/             # PWA source (HTML/JS)
├── docs/                # Documentation (bilingual)
├── server/relay/        # WebSocket relay server
└── .cursor/rules/       # AI agent role definitions
```

### Pull Request Guidelines

1. **One PR per feature/fix** — keep changes focused
2. **Test your changes** — run the desktop app and verify core flows
3. **Follow existing style** — Python 3.10+ type hints, no unused imports
4. **Bilingual docs** — if you modify a `.md` in `docs/`, update the `.en.md` counterpart too
5. **No secrets** — never commit tokens, passwords, or API keys

### Commit Message Format

```
type: short description

# Types: feat, fix, docs, refactor, ci, release, chore
# Examples:
#   feat: add CDP retry logic for flaky connections
#   fix: patrol trace missing timestamp in English locale
#   docs: add Japanese translation for README
```

### Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

---

## 中文

感谢你对 CodeFlow 的关注！

### 贡献方式

- **Bug 报告** — 提交 [Issue](https://github.com/joinwell52-AI/codeflow-pwa/issues)，附上复现步骤
- **功能建议** — 描述使用场景和预期行为
- **代码贡献** — 通过 Pull Request 修复 Bug 或实现新功能
- **文档改善** — 改进文档、修正错别字、补充翻译
- **测试反馈** — 反馈不同操作系统 / Cursor 版本的兼容性问题

### 快速开始

1. **Fork** 本仓库
2. **克隆**你的 fork：
   ```bash
   git clone https://github.com/<你的用户名>/codeflow-pwa.git
   cd codeflow-pwa
   ```
3. 创建**功能分支**：
   ```bash
   git checkout -b feat/your-feature
   ```

### 开发环境

**桌面端（Python 3.12）**
```bash
cd codeflow-desktop
pip install pyautogui pyperclip pywin32 websockets winocr Pillow watchdog psutil
python main.py
```

**PWA（纯静态 HTML）**
```bash
# 无需构建，直接在浏览器打开 web/pwa/index.html
# 或使用本地服务器：
python -m http.server 8080 -d web/pwa
```

### PR 规范

1. **一个 PR 只做一件事**
2. **自测通过** — 启动桌面端验证核心流程
3. **遵循现有风格** — Python 3.10+ 类型注解，无多余 import
4. **双语文档** — 修改 `docs/` 下的 `.md` 时，同步更新 `.en.md`
5. **禁止提交敏感信息** — token、密码、API key 等

### 行为准则

参与贡献前请阅读[行为准则](CODE_OF_CONDUCT.md)。
