---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: anti_hang_triage_20260421
priority: P2
---

# 接单回执：排查并缓解"AI 卡死"的发生路径

## 接单状态

**已接单。**

## 对任务的理解

ADMIN 提出的是一个**现象级关切**，不是一个技术需求。PM 的理解是：

- ADMIN 感知到"AI 卡住"发生得太频繁
- ADMIN 提到的 `open_panel` 只是一个引子/直觉表达，不是精确的技术定位
- ADMIN 自己给不出具体复现路径，所以把分诊工作托付给 PM

换句话说，ADMIN 要的**不是一次 defensive coding 的覆盖性加固**，而是**一份能让 ADMIN 自己也看明白"原来卡的点在这几个地方"的分诊报告**。

## 排查计划（分 3 个阶段）

### 阶段 1 · 代码扫描（本地 grep 级，无需运行）

扫描 Bridgeflow 项目里所有可能阻塞的调用点，关键词包括但不限于：

- `subprocess.run / Popen` 不带 `timeout=`
- `requests.get / post` 不带 `timeout=`
- `input()` / `sys.stdin.readline()`
- `time.sleep(...)` 循环里
- `.wait() / .join()` 不带超时
- `while True:` 里没有退出条件
- `msvcrt.getch()` 等 Windows 输入 API
- `pywinauto` / `pyautogui` 相关窗口等待
- socket 操作未设 `settimeout`

扫描覆盖三个目录：
1. `codeflow-plugin/scripts/`（除 `mcp_server.py` 已核对外）
2. `codeflow-desktop/`
3. `scripts/`（根目录运维脚本）

### 阶段 2 · 候选清单甄别

对阶段 1 找到的每个位置，判断：

- 它是否真的会被 AI agent 触发（有些代码只在手动运维时跑，不会被 agent 调起）
- 它是否确实存在挂起风险（有些调用表面危险但业务上立刻返回）
- 风险真实存在的，给出建议超时值

### 阶段 3 · 结论分类

分诊结果会分成四档：

1. **真卡点 + 明确修复项**：列清单，建议 ADMIN 派 DEV 按清单改
2. **疑似卡点**：需要实际跑一下确认，会另起一份任务
3. **已确认不是卡点**：排除项，附排除理由
4. **不在项目代码范围内的卡**（Cursor agent 推理层、模型生成层等）：如实说明，本任务不修

## 预计完成时间

**T+24h 内**交付 `REPORT-20260421-001-PM-to-ADMIN.md` 分诊报告。

如果在阶段 1 扫描完就发现"项目代码里几乎没有真卡点"——这是一种合理的可能——PM 会提前把结论给 ADMIN，不占满 24h。

## 依赖

- 无外部依赖，本次任务 PM 自己就能完成分诊
- 如果进入修复阶段，会派给 DEV，DEV 按修复清单执行

## 风险提示

PM 的预判：**"AI 卡"的主观感知，大概率主要来自 Cursor agent 推理层或模型生成层的等待，而不是我们自己的项目代码**。真正发生在本项目代码里的卡死路径，可能比 ADMIN 预期的少。

这不是要否定 ADMIN 的关切——恰恰相反，分诊报告的价值就在于把"感觉上 AI 常卡"这个模糊体验，拆出**哪些属于我们能修**、**哪些需要换工具或换工作方式**。

---

**备注**：本次立案本身就是一个小样本——ADMIN 在聊天里抛出一个代码片段（关于 `open_panel` 加超时），PM 没有直接照做，而是按 FCoP 规则走 `TASK-ADMIN-to-PM` + `TASK-PM-to-ADMIN` 回执把意图结构化。这样 ADMIN 真正关心的"避免 AI 乱跑"反而通过 FCoP 的流程本身得到了保障。
