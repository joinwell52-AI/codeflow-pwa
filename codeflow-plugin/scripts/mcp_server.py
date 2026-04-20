"""
CodeFlow MCP Server — the FCoP toolbox (产品中文名：码流).

MCP is a **toolbox**, not the protocol. The protocol lives in
`rules/codeflow-core.mdc` (filename-is-the-spec, YAML frontmatter, flat
directories). This file is the standard-issue tool belt every agent puts
on when arriving at the jobsite: same verbs on Windows / macOS / Linux,
same verbs in Cursor / Claude Desktop / CLI, same verbs across every
agent role in a multi-agent team.

四个字:**工具箱**。不是协议,不是注册中心,不是数据库,不是审计员。
MCP 服务的是"多 agent / 跨平台 / 统一着装 / 快速部署"这四件事——让不同
宿主、不同操作系统下的 agent,用同一套动词(list_tasks / read_task /
write_task / ...)说同一种话。协议本身在 codeflow-core.mdc 里。

Tool-addition rule (minimization check) / 加工具的判据:
  Before adding a new tool, ask:
  "Is this a **wrench**, or an **opinion** about how agents should work?"

  - Wrenches: grammar-aware listing, schema validation, atomic ID allocation,
    cross-platform path handling. These help agents do FCoP work correctly
    where raw file ops would be error-prone. → Add them.
  - Opinions: meta-management, convention-evolution machinery, state
    registries, shadow protocols. Agents can already do these with plain
    file ops if they really want to. → Leave them out. Filename is the spec.

  加新工具前问一句:**"这是一把扳手,还是一种关于 agent 该怎么干活的意见?"**
  扳手放进来(语法感知的查询、schema 校验、原子 ID 分配、跨平台路径)。
  意见留在外面——agent 想做,在 tasks/ 下开个子目录自己做就行,不需要协议插手。

Current tools:
  - Project initialization (create docs/agents/ structure)
  - Team status overview (task/report/issue counts)
  - Task listing and reading (grammar-aware: to-ROLE / to-ROLE.SLOT / to-TEAM)
  - Task writing with frontmatter validation
  - Report listing and reading
  - Custom team creation with user-defined roles
  - Bilingual support (zh/en)
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP(
    name="CodeFlow",
    instructions="Multi-AI Agent collaboration hub (码流 / CodeFlow) — file-driven task management. "
    "Supports bilingual (Chinese/English) output via lang parameter.",
)


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v is not None and v != "":
            return v
    return default


PROJECT_DIR = Path(_env("CODEFLOW_PROJECT_DIR", "CODEFLOW_PROJECT_DIR", default=".")).resolve()
AGENTS_DIR = PROJECT_DIR / "docs" / "agents"
TASKS_DIR = AGENTS_DIR / "tasks"
REPORTS_DIR = AGENTS_DIR / "reports"
ISSUES_DIR = AGENTS_DIR / "issues"
SHARED_DIR = AGENTS_DIR / "shared"
LOG_DIR = AGENTS_DIR / "log"


def _task_file_matches_recipient(filename: str, recipient: str) -> bool:
    """判断任务文件名是否发给指定角色。

    识别 FCoP v2.12.17 的 4 种收件人形式：
      - 直送：``-to-{ROLE}.md``
      - 槽位：``-to-{ROLE}.{SLOT}.md`` （点号分隔）
      - 广播：``-to-TEAM.md`` 或 ``-to-TEAM.{SCOPE}.md`` （对所有角色命中）
      - 匿名槽位：``-to-assignee.{SLOT}.md``

    角色名本身可以含连字符（AUTO-TESTER / LEAD-QA），slot 分隔符只用 `.`
    """
    if not recipient:
        return True
    role = re.escape(recipient.strip().upper())
    fn = filename.upper()
    pat_role = rf"-TO-{role}(\.[A-Z0-9_-]+)?\.(MD|FCOP)$"
    pat_team = r"-TO-TEAM(\.[A-Z0-9_-]+)?\.(MD|FCOP)$"
    return bool(re.search(pat_role, fn) or re.search(pat_team, fn))


def _team_config_path_read() -> Path | None:
    primary = AGENTS_DIR / "codeflow.json"
    legacy = AGENTS_DIR / "CodeFlow.json"
    if primary.exists():
        return primary
    if legacy.exists():
        return legacy
    return None


# ─── Bilingual strings ───────────────────────────────────

L = {
    "zh": {
        "not_init": "未初始化",
        "tasks": "待处理任务",
        "reports": "完成报告",
        "issues": "问题记录",
        "recent_tasks": "最近任务",
        "recent_reports": "最近报告",
        "no_tasks": "没有找到任务",
        "no_reports": "没有找到报告",
        "no_issues": "暂无问题记录",
        "filter": "筛选",
        "total": "共",
        "unit": "个",
        "task_created": "任务已创建",
        "file_not_found": "文件不存在",
        "archived": "已归档",
        "files": "个文件",
        "no_match": "没有找到相关文件",
        "available_teams": "可用团队模板",
        "roles": "角色",
        "leader": "主控",
        "team": "团队",
        "welcome_title": "欢迎使用码流（CodeFlow）",
        "welcome_body": "请开始分配第一个任务。",
        "your_members": "你的团队成员",
        "team_template": "团队模板",
        "directories": "目录结构",
        "custom_created": "自定义团队已创建",
    },
    "en": {
        "not_init": "Not initialized",
        "tasks": "Pending tasks",
        "reports": "Reports",
        "issues": "Issues",
        "recent_tasks": "Recent tasks",
        "recent_reports": "Recent reports",
        "no_tasks": "No tasks found",
        "no_reports": "No reports found",
        "no_issues": "No issues recorded",
        "filter": "filter",
        "total": "Total",
        "unit": "",
        "task_created": "Task created",
        "file_not_found": "File not found",
        "archived": "Archived",
        "files": "file(s)",
        "no_match": "No matching files found",
        "available_teams": "Available team templates",
        "roles": "Roles",
        "leader": "Leader",
        "team": "Team",
        "welcome_title": "Welcome to CodeFlow",
        "welcome_body": "Start assigning your first task.",
        "your_members": "Your team members",
        "team_template": "Team template",
        "directories": "Directories",
        "custom_created": "Custom team created",
    },
}


def t(key: str, lang: str = "zh") -> str:
    return L.get(lang, L["en"]).get(key, key)


# ─── Team templates with bilingual labels ─────────────────

TEAM_TEMPLATES = {
    "dev-team": {
        "name_zh": "软件开发团队",
        "name_en": "Software Development Team",
        "roles": [
            {"code": "PM", "label_zh": "项目经理", "label_en": "Project Manager"},
            {"code": "DEV", "label_zh": "开发工程师", "label_en": "Developer"},
            {"code": "QA", "label_zh": "测试工程师", "label_en": "QA Engineer"},
            {"code": "OPS", "label_zh": "运维工程师", "label_en": "DevOps Engineer"},
        ],
        "leader": "PM",
    },
    "media-team": {
        "name_zh": "自媒体团队",
        "name_en": "Content Media Team",
        "roles": [
            {"code": "PUBLISHER", "label_zh": "审核发行", "label_en": "Publisher & Reviewer"},
            {"code": "COLLECTOR", "label_zh": "素材采集", "label_en": "Content Collector"},
            {"code": "WRITER", "label_zh": "拟题提纲", "label_en": "Content Writer"},
            {"code": "EDITOR", "label_zh": "润色编辑", "label_en": "Content Editor"},
        ],
        "leader": "PUBLISHER",
    },
    "mvp-team": {
        "name_zh": "创业MVP团队",
        "name_en": "Startup MVP Team",
        "roles": [
            {"code": "MARKETER", "label_zh": "增长运营", "label_en": "Growth Marketer"},
            {"code": "RESEARCHER", "label_zh": "市场调研", "label_en": "Market Researcher"},
            {"code": "DESIGNER", "label_zh": "产品设计", "label_en": "Product Designer"},
            {"code": "BUILDER", "label_zh": "快速原型", "label_en": "Rapid Builder"},
        ],
        "leader": "MARKETER",
    },
}


def _team_name(tmpl: dict, lang: str) -> str:
    return tmpl.get(f"name_{lang}", tmpl.get("name_en", ""))


def _role_codes(tmpl: dict) -> list[str]:
    return [r["code"] for r in tmpl["roles"]]


def _role_label(role: dict, lang: str) -> str:
    return role.get(f"label_{lang}", role.get("label_en", role["code"]))


def _role_table(tmpl: dict, lang: str) -> str:
    lines = []
    for r in tmpl["roles"]:
        lines.append(f"  {r['code']} — {_role_label(r, lang)}")
    return "\n".join(lines)


# ─── Utilities ────────────────────────────────────────────


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_task_seq(directory: Path, prefix: str) -> int:
    if not directory.exists():
        return 1
    max_seq = 0
    for f in directory.glob(f"{prefix}*.md"):
        m = re.search(rf"{prefix}(\d{{3}})", f.name)
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq
    return max_seq + 1


def _scan_dir(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    items = []
    # 递归扫描：允许子目录分组（如 tasks/individual/、tasks/sprint-3/）
    for f in sorted(directory.rglob("*.md")):
        try:
            relpath = str(f.relative_to(directory)).replace("\\", "/")
        except ValueError:
            relpath = f.name
        items.append({
            "filename": f.name,
            "relpath": relpath,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return items


# FCoP 协议字段的可接受别名——读取时全部归一化成规范值 fcop（小写）。
# 规范值小写是因为 YAML 字段值遵循 machine-identifier 惯例（参考 http / ssh /
# grpc 等），而品牌名 "FCoP" 用在文档、标题、外部发布物里，两者分工。
# 历史值 agent_bridge（2026-04-20 之前的内部代号）作为别名永久接受。
_FCOP_PROTOCOL_ALIASES = {
    "fcop",             # 规范值本身
    "agent_bridge",     # 2026-04-20 之前的历史内部代号
    "agent-bridge",     # 英文连字符化变体
    "file-coordination",
    "file_coordination",
}


def _parse_frontmatter(filepath: Path) -> dict:
    """极简 YAML frontmatter 解析（只拆一级 key: value）。"""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip()
    # protocol 字段归一化：把历史值和常见别名统一成规范值 fcop，
    # 让下游消费者无需各自兼容多套写法。
    proto = out.get("protocol", "").strip()
    if proto and proto.lower() in _FCOP_PROTOCOL_ALIASES:
        out["protocol"] = "fcop"
    # version 字段归一化：允许 1 / 1.0 / "1.0" 三种写法等价，
    # 在内存里统一成整数字符串 "1"。避免下游按字符串比较时漏匹配。
    ver = out.get("version", "").strip().strip('"').strip("'")
    if ver in ("1", "1.0"):
        out["version"] = "1"
    return out


def _load_project_config() -> dict | None:
    path = _team_config_path_read()
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ─── MCP Tools ────────────────────────────────────────────


@mcp.tool
def init_project(team: str = "dev-team", lang: str = "zh") -> str:
    """Initialize CodeFlow project structure with a team template.

    Creates docs/agents/ directories (tasks, reports, issues, shared, log) and a welcome task.

    Args:
        team: Team template ID. Options: dev-team, media-team, mvp-team
        lang: Output language. Options: zh (Chinese), en (English)
    """
    if team not in TEAM_TEMPLATES:
        return f"Unknown team: {team}. Options: {', '.join(TEAM_TEMPLATES.keys())}"

    # shared/ 从 v2.12.17 起是团队标配：看板、冲刺、术语表、索引等共享产物的家
    for d in [TASKS_DIR, REPORTS_DIR, ISSUES_DIR, SHARED_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    tmpl = TEAM_TEMPLATES[team]
    name = _team_name(tmpl, lang)
    codes = _role_codes(tmpl)

    readme = AGENTS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# 码流（CodeFlow）\n\n"
            f"{t('team_template', lang)}: **{name}**\n\n"
            f"{t('roles', lang)}: {', '.join(codes)}\n\n"
            f"## {t('directories', lang)}\n\n"
            f"- `tasks/` — Task files\n"
            f"- `reports/` — Completion reports\n"
            f"- `issues/` — Issue records\n"
            f"- `shared/` — Team-wide standing docs (DASHBOARD / SPRINT / GLOSSARY / ...)\n"
            f"- `log/` — Archives\n",
            encoding="utf-8",
        )

    # shared/ 首次创建时留一份使用说明，避免空目录，也引导 Agent 怎么用
    shared_readme = SHARED_DIR / "README.md"
    if not shared_readme.exists():
        shared_readme.write_text(
            "# shared/ — 团队共享产物 / Team-wide Standing Docs\n\n"
            "与 `tasks/ reports/ issues/` 不同，本目录里的文档是**全队共读、允许原地更新**"
            "的知识沉淀，不在任务流程中流转。\n\n"
            "Unlike flow files, documents here are read by the whole team and MAY be "
            "updated in place — they are standing knowledge, not work items.\n\n"
            "## 推荐命名前缀 / Recommended prefixes\n\n"
            "| 前缀 Prefix | 用途 Purpose |\n"
            "|---|---|\n"
            "| `SPRINT-`    | 冲刺计划、节奏 / Sprint plans & cadence |\n"
            "| `DASHBOARD-` | 全貌看板 / Overview boards |\n"
            "| `STATUS-`    | 当前状态活页 / Living status pages |\n"
            "| `INDEX-`     | 导航索引 / Navigation indexes |\n"
            "| `MATRIX-`    | 人岗或资源矩阵 / Role / resource matrices |\n"
            "| `GLOSSARY-`  | 术语表 / Terminology |\n"
            "| `RULES-`     | 本项目局部约定 / Project-local conventions |\n"
            "| `DECISION-`  | 决策记录（只追加）/ Decision records (append-only) |\n"
            "| `RETRO-`     | 复盘（只追加）/ Retrospectives (append-only) |\n"
            "| `SPEC-`      | 需求或规格说明 / Specifications |\n\n"
            "如果现有前缀都不合适，自己创一个 UPPERCASE-HYPHEN 新前缀即可。\n"
            "If none of these fits, coin a new UPPERCASE-HYPHEN prefix.\n",
            encoding="utf-8",
        )

    config = {
        "team": team,
        "team_name": name,
        "roles": [{"code": r["code"], "label": _role_label(r, lang)} for r in tmpl["roles"]],
        "leader": tmpl["leader"],
        "lang": lang,
        "created_at": _now(),
    }
    config_file = AGENTS_DIR / "codeflow.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    leader = tmpl["leader"]
    welcome = TASKS_DIR / f"TASK-{_today()}-001-SYSTEM-to-{leader}.md"
    if not welcome.exists():
        welcome.write_text(
            f"---\ntask_id: TASK-{_today()}-001\nsender: SYSTEM\n"
            f"recipient: {leader}\ncreated_at: {_now()}\n"
            f"priority: normal\ntype: setup\n---\n\n"
            f"# {t('welcome_title', lang)}\n\n"
            f"{t('team_template', lang)}: **{name}**\n\n"
            f"{t('your_members', lang)}: {', '.join(codes)}\n\n"
            f"{t('welcome_body', lang)}\n",
            encoding="utf-8",
        )

    return (
        f"Project initialized: {name}\n"
        f"Directories: tasks/, reports/, issues/, log/\n"
        f"{t('roles', lang)}:\n{_role_table(tmpl, lang)}\n"
        f"{t('leader', lang)}: {leader}\n"
    )


@mcp.tool
def create_custom_team(
    team_name: str,
    roles: str,
    leader: str,
    lang: str = "zh",
) -> str:
    """Create a custom team with user-defined roles.

    Role codes can be anything — they become part of task filenames.
    For example: TASK-20260403-001-BOSS-to-CODER.md

    Args:
        team_name: Display name for the team (e.g. "My Design Studio")
        roles: Comma-separated role codes (e.g. "BOSS,CODER,TESTER,ARTIST")
        leader: Leader role code (must be one of the roles)
        lang: Output language: zh or en
    """
    role_list = [r.strip().upper() for r in roles.split(",") if r.strip()]
    if len(role_list) < 2:
        return "At least 2 roles required."
    if leader.upper() not in role_list:
        return f"Leader '{leader}' must be one of the roles: {', '.join(role_list)}"

    for d in [TASKS_DIR, REPORTS_DIR, ISSUES_DIR, SHARED_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    config = {
        "team": "custom",
        "team_name": team_name,
        "roles": [{"code": r, "label": r} for r in role_list],
        "leader": leader.upper(),
        "lang": lang,
        "created_at": _now(),
    }
    config_file = AGENTS_DIR / "codeflow.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = AGENTS_DIR / "README.md"
    readme.write_text(
        f"# 码流（CodeFlow）— {team_name}\n\n"
        f"{t('roles', lang)}: {', '.join(role_list)}\n"
        f"{t('leader', lang)}: {leader.upper()}\n",
        encoding="utf-8",
    )

    welcome = TASKS_DIR / f"TASK-{_today()}-001-SYSTEM-to-{leader.upper()}.md"
    if not welcome.exists():
        welcome.write_text(
            f"---\ntask_id: TASK-{_today()}-001\nsender: SYSTEM\n"
            f"recipient: {leader.upper()}\ncreated_at: {_now()}\n"
            f"priority: normal\ntype: setup\n---\n\n"
            f"# {t('welcome_title', lang)}\n\n"
            f"{t('team_template', lang)}: **{team_name}**\n\n"
            f"{t('your_members', lang)}: {', '.join(role_list)}\n\n"
            f"{t('welcome_body', lang)}\n",
            encoding="utf-8",
        )

    return (
        f"{t('custom_created', lang)}: {team_name}\n"
        f"{t('roles', lang)}: {', '.join(role_list)}\n"
        f"{t('leader', lang)}: {leader.upper()}\n"
    )


@mcp.tool
def get_team_status(lang: str = "") -> str:
    """Get current team status — task/report/issue counts and recent activity.

    Args:
        lang: Output language (zh/en). Empty = auto-detect from project config.
    """
    cfg = _load_project_config()
    if not lang:
        lang = cfg.get("lang", "zh") if cfg else "zh"

    tasks = _scan_dir(TASKS_DIR)
    reports = _scan_dir(REPORTS_DIR)
    issues = _scan_dir(ISSUES_DIR)

    if cfg:
        team_name = cfg.get("team_name", cfg.get("team", "?"))
        role_codes = [r["code"] for r in cfg.get("roles", [])]
        team_info = f"{team_name} ({', '.join(role_codes)})"
    else:
        team_info = t("not_init", lang)

    recent_tasks = [x["filename"] for x in tasks[-5:]]
    recent_reports = [x["filename"] for x in reports[-5:]]

    return (
        f"{t('team', lang)}: {team_info}\n"
        f"{t('tasks', lang)}: {len(tasks)} {t('unit', lang)}\n"
        f"{t('reports', lang)}: {len(reports)} {t('unit', lang)}\n"
        f"{t('issues', lang)}: {len(issues)} {t('unit', lang)}\n\n"
        f"{t('recent_tasks', lang)}:\n"
        + "\n".join(f"  - {x}" for x in recent_tasks) + "\n\n"
        f"{t('recent_reports', lang)}:\n"
        + "\n".join(f"  - {x}" for x in recent_reports)
    )


@mcp.tool
def list_tasks(
    recipient: str = "",
    parent: str = "",
    batch: str = "",
    lang: str = "",
) -> str:
    """List tasks, optionally filtered.

    Recipient matching is FCoP-aware (v2.12.17):
      - ``recipient=BUILDER`` matches ``to-BUILDER``, ``to-BUILDER.D1``, and ``to-TEAM``
      - ``recipient=assignee`` matches ``to-assignee.D1`` etc.

    Args:
        recipient: Filter by recipient role. Also matches TEAM broadcast and ROLE.SLOT.
        parent: Filter by parent task id in frontmatter (for 分包 / subtask batches).
        batch:  Filter by batch tag in frontmatter (groups of sibling sub-tasks).
        lang:   Output language (zh/en). Empty = auto-detect.
    """
    cfg = _load_project_config()
    if not lang:
        lang = cfg.get("lang", "zh") if cfg else "zh"

    tasks = _scan_dir(TASKS_DIR)

    if recipient:
        tasks = [
            x for x in tasks
            if _task_file_matches_recipient(x["filename"], recipient)
        ]

    if parent or batch:
        filtered = []
        for x in tasks:
            fp = TASKS_DIR / x.get("relpath", x["filename"])
            front = _parse_frontmatter(fp) if fp.exists() else {}
            if parent and front.get("parent", "").strip() != parent.strip():
                continue
            if batch and front.get("batch", "").strip() != batch.strip():
                continue
            filtered.append(x)
        tasks = filtered

    if not tasks:
        msg = t("no_tasks", lang)
        if recipient:
            msg += f" ({t('filter', lang)}: to-{recipient})"
        return msg

    lines = [f"{t('total', lang)} {len(tasks)} {t('unit', lang)}:\n"]
    for x in tasks:
        rel = x.get("relpath") or x["filename"]
        lines.append(f"  - {rel}  ({x['modified']})")
    return "\n".join(lines)


@mcp.tool
def read_task(filename: str) -> str:
    """Read the full content of a task file.

    Args:
        filename: Task filename, e.g. TASK-20260403-001-BOSS-to-CODER.md
    """
    fp = TASKS_DIR / filename
    if not fp.exists():
        return f"File not found: {filename}"
    return fp.read_text(encoding="utf-8")


@mcp.tool
def write_task(
    sender: str,
    recipient: str,
    title: str,
    content: str,
    priority: str = "normal",
    task_type: str = "feature",
) -> str:
    """Write a new task file. Role codes can be any string defined by the team.

    Args:
        sender: Sender role code (any string, e.g. PM, BOSS, PUBLISHER)
        recipient: Recipient role code (any string, e.g. DEV, CODER, WRITER)
        title: Task title
        content: Task description in Markdown
        priority: Priority: urgent, normal, low
        task_type: Type: feature, bugfix, review, deploy, research, content
    """
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    today = _today()
    prefix = f"TASK-{today}-"
    seq = _next_task_seq(TASKS_DIR, prefix)
    task_id = f"TASK-{today}-{seq:03d}"

    s = sender.strip().upper()
    r = recipient.strip().upper()
    filename = f"{task_id}-{s}-to-{r}.md"
    filepath = TASKS_DIR / filename

    md = (
        f"---\ntask_id: {task_id}\nsender: {s}\n"
        f"recipient: {r}\ncreated_at: {_now()}\n"
        f"priority: {priority}\ntype: {task_type}\n---\n\n"
        f"# {title}\n\n{content}\n"
    )
    filepath.write_text(md, encoding="utf-8")

    cfg = _load_project_config()
    lang = cfg.get("lang", "zh") if cfg else "zh"
    return f"{t('task_created', lang)}: {filename}"


@mcp.tool
def list_reports(reporter: str = "", lang: str = "") -> str:
    """List reports, optionally filtered by reporter role code.

    Args:
        reporter: Filter by reporter role code. Empty = all.
        lang: Output language (zh/en). Empty = auto-detect.
    """
    cfg = _load_project_config()
    if not lang:
        lang = cfg.get("lang", "zh") if cfg else "zh"

    reports = _scan_dir(REPORTS_DIR)
    if reporter:
        upper = reporter.upper()
        reports = [x for x in reports if upper in x["filename"].upper()]

    if not reports:
        msg = t("no_reports", lang)
        if reporter:
            msg += f" ({t('filter', lang)}: {reporter})"
        return msg

    lines = [f"{t('total', lang)} {len(reports)} {t('unit', lang)}:\n"]
    for x in reports:
        lines.append(f"  - {x['filename']}  ({x['modified']})")
    return "\n".join(lines)


@mcp.tool
def read_report(filename: str) -> str:
    """Read the full content of a report file.

    Args:
        filename: Report filename
    """
    fp = REPORTS_DIR / filename
    if not fp.exists():
        return f"File not found: {filename}"
    return fp.read_text(encoding="utf-8")


@mcp.tool
def list_issues(lang: str = "") -> str:
    """List all issue files.

    Args:
        lang: Output language (zh/en). Empty = auto-detect.
    """
    cfg = _load_project_config()
    if not lang:
        lang = cfg.get("lang", "zh") if cfg else "zh"

    issues = _scan_dir(ISSUES_DIR)
    if not issues:
        return t("no_issues", lang)
    lines = [f"{t('total', lang)} {len(issues)} {t('unit', lang)}:\n"]
    for x in issues:
        lines.append(f"  - {x['filename']}  ({x['modified']})")
    return "\n".join(lines)


@mcp.tool
def archive_task(task_id: str, lang: str = "") -> str:
    """Archive a completed task and its report to log/ directory.

    Args:
        task_id: Task ID prefix, e.g. TASK-20260403-001
        lang: Output language (zh/en). Empty = auto-detect.
    """
    cfg = _load_project_config()
    if not lang:
        lang = cfg.get("lang", "zh") if cfg else "zh"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    moved = []
    for d in [TASKS_DIR, REPORTS_DIR]:
        if not d.exists():
            continue
        for f in d.glob(f"{task_id}*.md"):
            dest = LOG_DIR / f.name
            shutil.move(str(f), str(dest))
            moved.append(f.name)

    if not moved:
        return f"{t('no_match', lang)}: {task_id}"
    return f"{t('archived', lang)} {len(moved)} {t('files', lang)}: " + ", ".join(moved)


@mcp.tool
def get_available_teams(lang: str = "zh") -> str:
    """List available preset team templates.

    Args:
        lang: Output language: zh (Chinese) or en (English)
    """
    lines = [f"{t('available_teams', lang)}:\n"]
    for key, tmpl in TEAM_TEMPLATES.items():
        name = _team_name(tmpl, lang)
        lines.append(f"  **{key}** — {name}")
        lines.append(f"    {t('roles', lang)}:")
        for r in tmpl["roles"]:
            lines.append(f"      {r['code']} — {_role_label(r, lang)}")
        lines.append(f"    {t('leader', lang)}: {tmpl['leader']}\n")

    lines.append(
        "\nCustom: use `create_custom_team` to define your own roles."
        if lang == "en" else
        "\n自定义：使用 `create_custom_team` 定义你自己的角色。"
    )
    return "\n".join(lines)


# ─── MCP Resources ────────────────────────────────────────


def _resource_status_impl() -> str:
    return get_team_status()


@mcp.resource("codeflow://status")
def resource_status_codeflow() -> str:
    """Current project collaboration status summary."""
    return _resource_status_impl()


@mcp.resource("CodeFlow://status")
def resource_status_codeflow_alias() -> str:
    """Alias URI for older integrations."""
    return _resource_status_impl()


def _resource_config_impl() -> str:
    path = _team_config_path_read()
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return '{"status": "not initialized"}'


@mcp.resource("codeflow://config")
def resource_config_codeflow() -> str:
    """Current CodeFlow project configuration."""
    return _resource_config_impl()


@mcp.resource("CodeFlow://config")
def resource_config_codeflow_alias() -> str:
    """Alias URI for older integrations."""
    return _resource_config_impl()


# ─── Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

