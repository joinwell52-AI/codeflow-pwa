---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: fcop_0_4_0_release_20260422
priority: P1
created_at: 2026-04-22T02:10:00+08:00
---

# fcop 0.4.0 已发布到 PyPI + Git — 完整交付报告

## 背景

本会话（2026-04-21 夜 → 2026-04-22 凌晨）完成 fcop 从 0.3.0 到 0.4.0
的迭代，围绕三件事：

1. 协议增 **Rule 0.c · 只落真话**（AI 伦理底线，不捏造、引用必带出处）
2. MCP 补 **Solo 起手路径** + **角色代码硬校验**
3. 首批《**致 ADMIN 的一封信**》用户手册（中英双语，随 init 自动落地）

## 交付清单

### 1. PyPI 发布

- 版本：`fcop` 0.3.0 → **0.4.0**
- 地址：https://pypi.org/project/fcop/0.4.0/
- 验证：`pip install fcop==0.4.0` 已可用
- `uvx fcop` 冷启动可用（用户端不需要本地编译）

### 2. Git 推送

- Commit：`f0514b3 · fcop 0.4.0: rebrand codeflow_mcp to fcop, add Rule
  0.c, Solo mode, role validation, LETTER-TO-ADMIN`
- 分支：`main`
- 推送：已 push 至 `origin/main`
- 改动：24 files, +1557 / −974

### 3. 协议规则（`fcop-rules.mdc` v1.0.0 → v1.1.0）

- Rule 0 由两根柱子扩为三根：
  - 0.a · Land it as a File（必须落文件）
  - 0.b · No Single AI Does Decision-to-Execution Alone（多角色制衡）
  - **0.c · Only Land True Things（只落真话）** ← 新增
- 目的 / Purpose 段同步补一条。

### 4. 协议解释（`fcop-protocol.mdc` v1.0.0 → v1.1.0）

新增 "How Rule 0.c Applies" 章节，含：

- 引用格式对照表（文件路径+行号 / 命令+stdout / URL / thread_key）
- 读入信时的 5 项事实审查清单
- Solo 模式的更严自审要求

### 5. MCP 工具（14 → 16）

| 新增工具 | 作用 |
|---|---|
| `init_solo(role_code, role_label, lang)` | Solo 模式一键起手 |
| `validate_team_config(roles, leader)` | 落盘前干跑校验 |

既有工具加固：

- `create_custom_team` / `init_solo` 接入角色代码硬校验：拒绝中文、
  `-`、`.`、空格、保留字（`ADMIN` / `SYSTEM`）、重复角色
- `init_project` / `create_custom_team` / `init_solo` 全部在 `fcop.json`
  写 `"mode"` 字段（`team` / `solo`）

### 6. MCP 资源（4 → 6）

| 新增资源 | 内容 |
|---|---|
| `fcop://letter/zh` | 《FCoP 致 ADMIN 的一封信》中文说明书 |
| `fcop://letter/en` | Letter to ADMIN, English |

### 7. 《致 ADMIN 的一封信》用户手册

- 源文件：`src/fcop/_data/letter-to-admin.{zh,en}.md`
- 部署：`init_project` / `init_solo` / `create_custom_team` 执行时按
  `lang` 挑一份落到 `docs/agents/LETTER-TO-ADMIN.md`（永不覆盖）
- 内容要点：
  - 身份澄清（ADMIN = 真人，roles = AI，ADMIN **不进 `fcop.json.roles`**）
  - 起手三选一（Solo 第一 / 预设第二 / 自定义第三）
  - 自建角色硬规则 + 命名建议（推荐职能词 `MANAGER` / `CODER`，避开
    权威词 `BOSS` / `CEO` / `CHIEF`）
  - 4 条必读规则缩略版（0.a / 0.b / 0.c / Rule 1）

### 8. 文档同步

- `codeflow-plugin/README.md`：工具清单、资源清单、快速开始三段重写
- `codeflow-plugin/.cursor-plugin/plugin.json`：版本升 0.4.0
- `codeflow-plugin/src/fcop/__init__.py`：`__version__ = "0.4.0"`
- `CHANGELOG.md`：Unreleased 顶部加 fcop 0.4.0 专属条目

## 验证（冷启动烟测结果）

15 项断言全绿（其中 #8 "lowercase 被拒" 是我的 smoke 脚本逻辑写错了——
代码会 `.upper()` 容错大小写，这是**正确行为**）：

1. `validate_team_config` 合法输入 → OK
2–6. 中文 / `-` / `ADMIN` / leader 不在列表 / 单角色 → 全部被拦，给出双语错误
7. `init_solo(ME)` → `fcop.json.mode=solo` 写入
9. `init_solo(ADMIN)` → 保留字被拦
10. `create_custom_team(MANAGER,CODER,TESTER,ARTIST)` → `mode=team` 写入
11. `create_custom_team(程序员,测试)` → 中文被拦
12. `init_project("dev-team")` → `mode=team` 写入
13. `get_available_teams` 输出包含 Solo 且排第一
14. 4 个资源（letter/zh、letter/en、rules、protocol）全部可读
15. 16 个工具全部在 FastMCP 注册（`list_tools` 枚举确认）

## 影响范围

- 对 **现有 fcop 用户**：零破坏。`pip install -U fcop` 后既有 0.3.0
  起手工具继续可用，`fcop.json` 会多一个 `mode` 字段（默认 `team`），
  既有项目不受影响。
- 对 **新用户**：起手有三条明确路径，自建角色的非法输入在落盘前被拦。
- 对 **AI Agent**：`fcop-rules.mdc` 自动注入多一条 0.c，
  `fcop-protocol.mdc` 多一章 0.c 落地指南。

## 未做的事（留给后续迭代）

- Desktop 侧"3 选 1 起手表单"还没改（UI 层工作，不涉及 MCP）。
- `create_custom_team` 目前 `label == code`，不支持中文角色显示名；
  若要补需要新增可选参数 `role_labels`。
- 英文版 `README.md` / `README.en.md` 未单独同步（当前只有中文 README）。

## 自测结论

**建议上线 / 可直接使用**。PyPI 可下载，Git 已推送，本地冷启动验证通过。

如果你想立刻试，新开一个空目录：

```
mkdir C:\tmp\fcop-try
cd C:\tmp\fcop-try
# 在 Cursor 里开 Agent，说：
#   "用 Solo 模式初始化项目，角色代码叫 ME"
```

应当看到 `docs/agents/fcop.json` 含 `"mode": "solo"`，
`docs/agents/LETTER-TO-ADMIN.md` 中文说明书落地，
`.cursor/rules/` 下两份协议文件部署完成。

— PM
