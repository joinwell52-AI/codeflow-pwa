---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: anti_hang_triage_20260421
priority: P1
---

# 分诊报告：Bridgeflow "AI 卡死" 风险点盘点与治理方案

## 1. 结论摘要

经过对全仓代码的系统性扫描（重点是 `codeflow-desktop/` 和 `codeflow-plugin/`），分诊结论如下：

- **项目代码中存在真卡点**：确实存在若干处未设超时的 `subprocess` 调用和过于沉重的同步 OCR 轮询逻辑。
- **主观卡顿感来源**：
  1. **同步阻塞 IO**：脚本在执行 OCR 或调用外部命令（如 `gh`）时，巡检线程完全挂起。
  2. **UI 争抢**：`pyautogui` 在模拟输入时频繁抢占焦点或执行耗时 `time.sleep`。
  3. **非代码因素**：Cursor Agent 推理层本身的延迟（这是我们无法通过修改本项目代码解决的）。

## 2. 明确修复清单（真卡点）

建议 ADMIN 派发 DEV 执行以下修复：

### A. Subprocess 超时加固 (P1)
**位置**：
- `codeflow-desktop/cursor_vision.py` (OCR 调用)
- `codeflow-desktop/release.py` (`gh` 工具调用)
- `codeflow-desktop/cursor_embed.py` (Cursor 进程控制)
- `codeflow-desktop/main.py` (各类 shell 辅助工具)

**修复方案**：所有 `subprocess.run` / `check_output` 必须强制带上 `timeout=30`（或根据业务需要调整），并捕获 `TimeoutExpired` 异常，记录 error 级别日志而非崩溃。

### B. Nudger 逻辑减负 (P1)
**位置**：`codeflow-desktop/nudger.py` 中的 `_locate_and_click_input` 和消息粘贴逻辑。

**修复方案**：
1. **减少 OCR 频率**：在 `_inp_retries` 循环中，如果连续两次 OCR 结果一致且未发现目标，应提前中断并报错，而不是耗尽重试次数。
2. **优化 Sleep**：将硬编码的 `time.sleep` 缩减，或改为基于事件的等待。

### C. 弃用低效工具 (已完成)
- **已落地**：下架 `codeflow_mcp.py`。该工具使用 `pyautogui` 且无超时保护，是极大的潜在卡点。

## 3. 已确认不是卡点（排除项）

- **`mcp_server.py`**：由于主要是本地文件读写，目前未发现阻塞路径。
- **`codeflow-plugin` 核心逻辑**：作为 MCP 运行在独立进程，其本身的阻塞不会直接导致 Cursor UI 卡死，但在极端情况下会响应超时。

## 4. 无法修复的外部因素

- **Cursor 模型推理延迟**：当 Agent 正在思考（Thinking）时，Cursor UI 的卡顿通常是模型生成压力或 VS Code 插件进程负载过高导致的，项目代码无能为力。

## 5. 建议行动

请 ADMIN 审批后，我将派发 `TASK-20260421-003-PM-to-DEV.md`。DEV 应按上述清单执行 A 类和 B 类修复。

---
**签名**：PM-01  
**日期**：2026-04-21
