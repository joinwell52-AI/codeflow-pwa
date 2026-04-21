# Cursor / VS Code 快捷键与「仅本项目生效」

## 结论（先看这个）

1. **快捷键规则默认写在用户配置里**：`%APPDATA%\Cursor\User\keybindings.json`（Windows），由 Cursor 监视并合并进默认规则。官方文档中的「高级自定义」指的是这份 **用户** `keybindings.json`，**不是**仓库里的 `.vscode/keybindings.json`。
2. **与 `settings.json` 不同**：工作区可以放 `.vscode/settings.json`；**VS Code 并不提供与之一一对应的、标准的工作区专用 `keybindings.json` 自动加载机制**（社区常见做法是用户级规则 + `when` 条件）。
3. **若网上方案把规则写进「项目根 `.vscode/keybindings.json`」**：需在你本机 Cursor 版本上**实测**是否被读取；**不要默认**认为放进仓库就会只对当前仓库生效。
4. **「仅本项目」在官方模型里**通常靠 **`when` 子句** 限制：规则仍在**用户** `keybindings.json`，通过 `workspaceFolderPath`、`resourceDirname`、`config.xxx` 等上下文判断当前是否在该项目。

## 想「只在本项目里响应 Ctrl+Alt+1～4」时的可行做法

| 做法 | 说明 |
|------|------|
| **用户 keybindings + `when`** | 在**用户** `keybindings.json` 增加规则，例如 `when` 使用 `workspaceFolderPath =~ /你的项目路径片段/`（路径随机器变化，换电脑要改或改用更稳的匹配）。 |
| **用户 keybindings + 工作区开关** | 在 `.vscode/settings.json` 设自定义项 `codeflow.keybindings.enabled: true`，用户 `keybindings.json` 里 `when: config.codeflow.keybindings.enabled`；只有打开本项目且启用时才生效。 |
| **多窗口时注意** | `when` 依赖当前窗口的 workspace；规则写错时可能「看起来全局生效」或「永远不生效」，用 **Developer: Inspect Context Keys** 排查。 |

## 与码流（CodeFlow）路线的关系

- **CodeFlow Desktop（巡检/催办）** 通过 **pyautogui** 发送 **Ctrl+Alt+1～4** 时，本质是 **操作系统向当前前台窗口** 发按键；**不会在 Cursor 内部自动区分「哪个仓库」**，依赖用户当时把 **正确的 Cursor 窗口** 置前。
- **因此**：若产品目标是「**不依赖用户全局快捷键配置**、**不依赖是否误绑到其他项目**」，更稳的是：
  - **侧栏标签 + OCR/点击**（当前巡检已支持的路径），或  
  - **MCP 工具**（在 Cursor 内显式调用，由工具内再聚焦窗口/走命令面板），或  
  - **接受「用户级 keybindings + when」** 作为可选高级配置，由文档说明如何写 `when`，**不把**「项目内 keybindings 文件存在」当作预检通过条件。

## 「放弃 Cursor 快捷键」时的替代

1. **桌面端巡检**：继续用快捷键或点击链路，由 CodeFlow 控制节奏；用户可减少在 Cursor 里绑定全局键。
2. **Cursor 扩展**：例如仓库内 `codeflow-desktop/cursor-extension/`（`codeflow-panel-launcher`）通过 VS Code 扩展 API 打开面板，或自写 MCP 扩展其它能力。
3. **纯手动**：侧栏点 Agent；预检验证「能切到」即可。

## 参考

- [VS Code: Keyboard shortcuts](https://code.visualstudio.com/docs/getstarted/keybindings)（用户 `keybindings.json`、`when` 子句）
- [When clause contexts](https://code.visualstudio.com/api/references/when-clause-contexts)

---

*文档说明产品边界，不替代 Cursor 版本更新带来的行为差异；以本机实测为准。*
