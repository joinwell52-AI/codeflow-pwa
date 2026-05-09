---
protocol: fcop
version: 1.4.0
sender: PM
recipient: ADMIN
priority: P2
thread_key: fcop-0.6-library-split
created_at: 2026-04-23T16:00:00
---

# PM → ADMIN · 进度回执 · D5 全部完成 + CI 全面升级

## 摘要

D5（团队模板 + 规则文本 + deploy_role_templates + drop_suggestion）**全部落地**。
CI 从"单一 test 矩阵"升级为"test + coverage + package"三段式流水线。
`fcop 0.6` 库侧功能面基本齐活，进入 D6/D7/D8 阶段前已没有遗留 `NotImplementedError`。

## D5 完成清单

### D5-c1 · `fcop.rules`（协议规则文本访问器）

- 把 4 份官方文档搬进 wheel：
  - `src/fcop/rules/_data/fcop-rules.mdc`（v1.4.0，21 KB · 9 条核心规则）
  - `src/fcop/rules/_data/fcop-protocol.mdc`（51 KB · 配套解释）
  - `src/fcop/rules/_data/letter-to-admin.zh.md`（25 KB）
  - `src/fcop/rules/_data/letter-to-admin.en.md`（26 KB）
- 实现 4 个访问函数：`get_rules()` / `get_protocol_commentary()` /
  `get_letter(lang)` / `get_rules_version()`；均用 `importlib.resources` 懒加载 +
  `functools.cache` 结果缓存，LLM 重复拼 system prompt 不会反复解压 wheel。
- `get_rules_version()` 从 frontmatter 解出 `"1.4.0"` —— 库版本与规则版本解耦。
- 13 个新测试，含 **打包哨兵测试**：直接检查 `importlib.resources.files()` 能
  看到所有 4 份数据文件，防止未来有人误删 `pyproject.toml` 的 include 块
  导致 wheel 静悄悄地变空。

### D5-c2 · `fcop.teams`（团队模板数据化）

- 把 plugin 0.5.x 的 `_data/teams/` 整棵搬过来：**58 个 .md 文件 + 1 个
  `index.json`**，覆盖 dev-team / media-team / mvp-team / qa-team 四个预置队。
- 改造 `fcop.teams.__init__`：
  - `TeamInfo` 改为从 `index.json` **运行时派生**，不再有硬编码 `_BUNDLED_TEAMS` dict
    —— 单一真理源，改角色清单只改 JSON。
  - `get_template(team, lang)` 落地，返回 `TeamTemplate` 数据类
    （`readme` + `team_roles` + `operating_rules` + `roles: dict[CODE → str]`）。
- **数据口径对齐副作用**（属于 semver-minor 行为变更，已记入 `CHANGELOG.md`）：
  - `mvp-team` 队伍：PM/BUILDER/SELLER → **MARKETER（队长）/ RESEARCHER / DESIGNER / BUILDER**
  - `media-team` 队伍：**新增 EDITOR 角色**（原 3 人，现 4 人）
- 修了一个打包坑：原先用 `[force-include]` 使 wheel 里 139 条记录 / 80 条
  唯一（即每个 data file 都被打两次）。改成 `[tool.hatch.build.targets.wheel].include`
  glob 后，wheel 严格 80 条、无重复。

### D5-c3 · `Project.deploy_role_templates`

- 把预置团队的 3 层文档从 bundle 写到 `docs/agents/shared/`：
  - 顶层 `TEAM-README[.en].md` / `TEAM-ROLES[.en].md` / `TEAM-OPERATING-RULES[.en].md`
  - 子目录 `roles/{CODE}[.en].md`
  - **zh 和 en 同时部署**，不因一时的 lang 配置错过任何文件。
- `force=True`（默认）先把冲突文件归档到 `.fcop/migrations/<timestamp>/shared/`
  再写新内容；`force=False` 改为跳过已存在文件并计入 `skipped`。
- `team` / `lang` 不传时从 `fcop.json` 读取；未初始化项目可以显式传 `team=...`
  仍能部署（部署本身不要求项目已 `init`）。

### D5-c4 · `Project.drop_suggestion`

- "协议泄压阀"——AI 不许直接改 `.mdc`，想提意见只能经此落文件：
  - 写到 `<project>/.fcop/proposals/<YYYYMMDD-HHMMSS>.md`
  - 头部 `# Suggestion @ <ts>`；可选 `**Context**:` 行；`content` 正文原样保留
  - 同秒重复调用用 `-2.md` / `-3.md` 后缀拒绝静默覆盖（`O_CREAT | O_EXCL`）
- 不要求项目已 `init`，半成品目录也能写——泄压阀就该随时可用。
- 空白 `content` 明确 `raise ValueError`，不生成空文件。

## CI 升级（test-fcop.yml）

从单 job 的 **3 OS × 4 Py = 12 格矩阵** 升级到 **三段式**：

1. **test** · 原矩阵 + 新增 `mypy --strict`（strict 模式暴露的 7 个类型错误已全部修完）。
2. **coverage** · Ubuntu/3.12 单跑，`pytest --cov --cov-fail-under=90`。当前基线 **92%**。
3. **package** · Ubuntu/3.12，在 `test` 成功后运行：
   - `python -m build --wheel --sdist`
   - **wheel 内容断言**：6 条关键 bundled data 路径必须存在
   - **干净 venv 安装 + 冒烟 import**：唯一能验证"用户 pip install 后能不能真的跑"的方式
   - `pip-audit --strict`：依赖树跑一遍 PyPI Advisory DB

原来只测 Python 代码是否跑得通；现在能捕获：
- 类型错误（mypy）
- 覆盖率回退（coverage 85% 硬门槛 → 现在 90%）
- 包文件缺失（wheel 断言）
- 编辑模式能跑但干净安装跑不起来（smoke venv）
- pyyaml 某天爆 CVE（pip-audit）

## 质量指标

| 维度 | 状态 |
|---|---|
| 测试 | **439 通过**（上次回执 392 → +47） |
| 覆盖率 | **92%**（含分支） |
| 类型 | mypy strict **0 错** |
| lint | ruff **0 错** |
| wheel | 80 文件、0 重复、4 rules data + 59 teams data 全部 ship |
| CI | 三段式 pipeline、feat/0.6-library-split 上跑 |

## 影响范围

- 仅 `feat/0.6-library-split` 分支，**未触碰 main**。
- `fcop-mcp` 仍在 D7 阶段，**0.5.x 线上用户无影响**。
- 预置团队角色调整是 0.6 的刻意变更，已写进 CHANGELOG、Migration 指南会在 D8 给出。

## 下一步建议（请 ADMIN 确认优先级）

- **[推荐]** 继续进 D6：把 `ProtocolViolation` / `ValidationError` 在 Project 边界
  补齐（部分已在 D4-c1 写报告时用上，D6 统一补完）。
- 或启动 **D7** `fcop-mcp` 子包：把 plugin 的 22 个 MCP tool 改成对 `fcop.Project`
  的薄封装。这步拆完 0.6.0 就能发了。
- 或先写两份文档：`docs/MIGRATION-0.6.md` 给用户、`docs/release-process.md`
  给双包联动发布流程。

## 引用

- CI 跑通历史：[test-fcop workflow runs](https://github.com/joinwell52-AI/FCoP/actions/workflows/test-fcop.yml)
- 分支：`feat/0.6-library-split`
- 相关 ADR：[ADR-0001 library API](https://github.com/joinwell52-AI/FCoP/blob/feat/0.6-library-split/adr/ADR-0001-library-api.md)
