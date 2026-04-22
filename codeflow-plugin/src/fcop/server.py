"""
fcop — the MCP toolbox for FCoP (File-based Coordination Protocol).

MCP is a **toolbox**, not the protocol. The protocol lives in two sibling
rule files: `rules/fcop-rules.mdc` (the protocol rules) and
`rules/fcop-protocol.mdc` (the protocol commentary — filename-is-the-spec,
YAML frontmatter, flat directories, patrol triggers, etc.). Rules say
*what must hold*; commentary says *how it looks in practice*. This file
is the standard-issue tool belt every agent puts on when arriving at the
jobsite: same verbs on Windows / macOS / Linux, same verbs in Cursor /
Claude Desktop / CLI, same verbs across every agent role in a multi-agent
team.

四个字:**工具箱**。不是协议,不是注册中心,不是数据库,不是审计员。
MCP 服务的是"多 agent / 跨平台 / 统一着装 / 快速部署"这四件事——让不同
宿主、不同操作系统下的 agent,用同一套动词(list_tasks / read_task /
write_task / ...)说同一种话。协议本身在 fcop-rules.mdc(协议规则)与
fcop-protocol.mdc(协议解释)里。

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

  Two shapes of wrench / 扳手有两种形态:
    (a) Problem-solving wrenches — help agents DO FCoP work correctly.
        e.g. `inspect_task` catches filename↔frontmatter mismatches that
        raw read_file + regex would miss.
    (b) Safety-fuse wrenches — PREVENT specific bad behaviours. Their value
        shows up in what bad thing does NOT happen, not in what good thing
        they produce. e.g. `drop_suggestion` exists so agents have a
        legitimate outlet for protocol disagreement, instead of silently
        editing `fcop-rules.mdc` / `fcop-protocol.mdc` themselves. The tool
        is trivially simple; the value is entirely in the Rules-level
        sentence "use this instead of touching the rules files".

    (a) 解题型扳手:帮 agent 把 FCoP 的活儿干对(inspect_task 这类)。
    (b) 保险丝型扳手:拦截特定坏行为,价值体现在"没它时会发生什么坏事",
        而不是"有它时能做什么好事"(drop_suggestion 这类)。

Current tools:
  - UNBOUND report (unbound_report) — MUST be the first call in a new session.
    Safety-fuse wrench that enforces FCoP v1.1 Rule 0 (no role-claim from
    context, no writes before ADMIN assignment) by producing a standardized
    report format agents cannot easily "helpfully improve on".
  - Project initialization (create docs/agents/ structure)
  - Team status overview (task/report/issue counts)
  - Task listing and reading (grammar-aware: to-ROLE / to-ROLE.SLOT / to-TEAM)
  - Task writing with frontmatter validation
  - Task inspection (schema + filename/frontmatter consistency check) — wrench
  - Report listing and reading
  - Custom team creation with user-defined roles
  - Suggestion valve (drop_suggestion) — safety fuse for protocol disagreement
  - Bilingual support (zh/en)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from contextlib import ExitStack
from datetime import datetime
from importlib import resources
from pathlib import Path

from fastmcp import FastMCP


def _packaged_data(filename: str) -> Path | None:
    """Return a filesystem path to a bundled data file under `fcop/_data/`.

    After `pip install fcop` the file lives inside the wheel as package data
    (`fcop/_data/<filename>`). `importlib.resources` is the only portable way
    to reach it; practically Python wheels for pure-python packages are
    unpacked so the `Traversable` IS a `Path`.
    """
    try:
        base = resources.files("fcop") / "_data" / filename
    except (ModuleNotFoundError, AttributeError):
        return None
    try:
        p = Path(str(base))
        return p if p.exists() else None
    except Exception:
        return None


def _packaged_data_bytes(filename: str) -> bytes | None:
    """Byte-level read of a bundled data file (zipsafe fallback)."""
    try:
        base = resources.files("fcop") / "_data" / filename
        with ExitStack() as stack:
            path = stack.enter_context(resources.as_file(base))
            return Path(path).read_bytes()
    except Exception:
        return None


mcp = FastMCP(
    name="fcop",
    instructions=(
        "【目的 / Purpose】本协议让 Agent 通过 FCoP 与团队协同工作；"
        "团队可以是多 Agent 多角色，也可以是单 Agent 单角色（solo 模式），"
        "协作都以**文件**为媒介。\n"
        "This protocol enables agents to coordinate with a team via FCoP; "
        "teams can be multi-agent or single-agent (solo mode), and "
        "coordination always happens through files.\n\n"
        "本项目的协议由两个同级文件共同定义："
        "`.cursor/rules/fcop-rules.mdc`（协议规则，alwaysApply）+ "
        "`.cursor/rules/fcop-protocol.mdc`（协议解释，alwaysApply）。"
        "冲突时以 fcop-rules.mdc 为准。本 MCP（`fcop`）是协议的标准工具箱。\n"
        "The protocol is defined by two sibling files: "
        "`.cursor/rules/fcop-rules.mdc` (protocol rules, alwaysApply) + "
        "`.cursor/rules/fcop-protocol.mdc` (protocol commentary, "
        "alwaysApply). fcop-rules.mdc wins on conflict. This MCP (`fcop`) "
        "is the standard toolbox for the protocol.\n\n"
        "FCoP · File-based Coordination Protocol —— 多 AI Agent 文件驱动协作协议。\n"
        "FCoP — a file-based coordination protocol for multi-AI agent teams.\n\n"
        "【Rule 1 · UNBOUND】新会话默认处于 UNBOUND 态，第一个动作必须是"
        "调用 `unbound_report()` 输出项目客观状态并等待 ADMIN 指派身份。"
        "不得从上下文推断角色，不得在未获指派前写任何文件。\n"
        "New sessions start UNBOUND. FIRST action MUST be `unbound_report()`; "
        "wait for ADMIN's explicit role assignment. Do not infer your role; "
        "do not write any files before assignment."
    ),
)


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v is not None and v != "":
            return v
    return default


# ─── Project-root resolution (0.4.1) ──────────────────────────────
#
# Before 0.4.1, PROJECT_DIR was hard-locked to FCOP_PROJECT_DIR at module
# import time, with a silent `.` (= cwd) fallback. In Cursor the MCP
# subprocess's cwd is the user home, so "no env set" meant "everything
# lands in %USERPROFILE%". Nasty, silent, and per-project reconfig was
# the only workaround.
#
# 0.4.1 does four things:
#   1. Honour FCOP_PROJECT_DIR (primary, unchanged).
#   2. Honour the legacy CODEFLOW_PROJECT_DIR with a one-shot stderr
#      deprecation warning — anyone who carried a 0.3.x mcp.json across
#      the rename would otherwise silently break.
#   3. Auto-detect by walking up from cwd looking for FCoP / Cursor /
#      VCS / project markers. Helps CLI callers; does NOT help Cursor
#      (its MCP cwd is the home dir), hence step 4.
#   4. Expose `set_project_dir(path)` as an MCP tool so an Agent inside
#      Cursor can pin the project root in one sentence, without the user
#      ever editing mcp.json.
#
# Module-level PROJECT_DIR et al. are exposed via __getattr__ so every
# access is fresh — callers of `set_project_dir` flip the state and all
# 70-ish AGENTS_DIR / TASKS_DIR references pick up the new value with no
# refactor.

# Auto-detect markers. Order matters: first hit on each candidate dir wins.
#
# We deliberately avoid bare ".cursor" / ".vscode" here — those directories
# exist under every user's home (e.g. %USERPROFILE%\.cursor holds the
# global mcp.json and logs), which made 0.4.1's auto-detect silently bind
# to the home dir when Cursor spawned MCP with cwd = %USERPROFILE%. 0.4.2
# uses only strong signals: something INSIDE .cursor/rules counts, .cursor
# on its own does not.
_AUTO_MARKERS: tuple[tuple[str, str], ...] = (
    ("docs/agents/fcop.json", "initialized FCoP project"),
    (".cursor/rules/fcop-rules.mdc", "Cursor + FCoP rules"),
    (".git", "git repo root"),
    ("pyproject.toml", "Python project root"),
    ("package.json", "Node project root"),
)

_LEGACY_WARNED = False


def _home_dirs() -> set[Path]:
    """Return resolved paths that should never be treated as a project root.

    Covers Windows (``%USERPROFILE%``), POSIX (``$HOME``), and Windows'
    shared profile root (``C:\\Users``) in case ``Path.home()`` returns
    something odd. Anything here, even if a marker matches, means we keep
    walking up (or fall through to cwd fallback with a warning).
    """
    out: set[Path] = set()
    for v in (os.environ.get("USERPROFILE"), os.environ.get("HOME")):
        if v:
            try:
                out.add(Path(v).resolve())
            except Exception:
                pass
    try:
        out.add(Path.home().resolve())
    except Exception:
        pass
    if os.name == "nt":
        # Parent of USERPROFILE is typically C:\Users — also unsafe.
        for p in list(out):
            out.add(p.parent)
    return out


def _resolve_project_dir() -> tuple[Path, str]:
    """Return `(project_dir, source)` using the 0.4.2 cascade.

    `source` is a short human-readable tag used by `unbound_report` so the
    ADMIN can see *why* the project root is what it is (env var name /
    auto-detected marker / cwd fallback / unsafe-home warning).
    """
    global _LEGACY_WARNED

    explicit = os.environ.get("FCOP_PROJECT_DIR")
    if explicit:
        return Path(explicit).resolve(), "env:FCOP_PROJECT_DIR"

    legacy = os.environ.get("CODEFLOW_PROJECT_DIR")
    if legacy:
        if not _LEGACY_WARNED:
            sys.stderr.write(
                "[fcop] WARNING: CODEFLOW_PROJECT_DIR is deprecated; "
                "rename it to FCOP_PROJECT_DIR in your mcp.json.\n"
            )
            _LEGACY_WARNED = True
        return Path(legacy).resolve(), "env:CODEFLOW_PROJECT_DIR (deprecated)"

    try:
        cwd = Path.cwd().resolve()
    except Exception:
        cwd = Path(".").resolve()

    unsafe = _home_dirs()

    for cand in (cwd, *cwd.parents):
        if cand in unsafe:
            # Home / Users — never auto-bind here even if a marker matches.
            # Example: %USERPROFILE%\.cursor exists for every Cursor user
            # and used to trip up 0.4.1's bare ".cursor" marker.
            continue
        for marker, _label in _AUTO_MARKERS:
            if (cand / marker).exists():
                return cand, f"auto:{marker}"

    if cwd in unsafe:
        return (
            cwd,
            "cwd fallback (home dir — unsafe; call "
            "set_project_dir(\"<your project>\") or set FCOP_PROJECT_DIR)",
        )
    return cwd, "cwd fallback (no markers; consider setting FCOP_PROJECT_DIR)"


_STATE: dict = {"project_dir": None, "source": "uninitialized"}

# Module-level path constants. Kept as ordinary module globals (rather
# than behind __getattr__) because code *inside* this file references
# them as bare names — bare-name lookups hit `globals()` directly and
# bypass PEP-562 module __getattr__. `_rebind_paths()` below reassigns
# all seven atomically, so the 70-ish existing call sites keep working
# and still see fresh values after `set_project_dir`.
PROJECT_DIR: Path = Path(".").resolve()
AGENTS_DIR: Path = PROJECT_DIR / "docs" / "agents"
TASKS_DIR: Path = AGENTS_DIR / "tasks"
REPORTS_DIR: Path = AGENTS_DIR / "reports"
ISSUES_DIR: Path = AGENTS_DIR / "issues"
SHARED_DIR: Path = AGENTS_DIR / "shared"
LOG_DIR: Path = AGENTS_DIR / "log"


def _rebind_paths(project_dir: Path, source: str) -> None:
    """Point every path constant at ``project_dir`` and record ``source``."""
    global PROJECT_DIR, AGENTS_DIR, TASKS_DIR, REPORTS_DIR, ISSUES_DIR
    global SHARED_DIR, LOG_DIR
    PROJECT_DIR = project_dir
    AGENTS_DIR = project_dir / "docs" / "agents"
    TASKS_DIR = AGENTS_DIR / "tasks"
    REPORTS_DIR = AGENTS_DIR / "reports"
    ISSUES_DIR = AGENTS_DIR / "issues"
    SHARED_DIR = AGENTS_DIR / "shared"
    LOG_DIR = AGENTS_DIR / "log"
    _STATE["project_dir"] = project_dir
    _STATE["source"] = source


def _init_project_state() -> None:
    p, src = _resolve_project_dir()
    _rebind_paths(p, src)


_init_project_state()


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
    primary = AGENTS_DIR / "fcop.json"
    if primary.exists():
        return primary
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
        "welcome_title": "欢迎使用 FCoP 协作协议",
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
        "welcome_title": "Welcome to FCoP",
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


# ─── UNBOUND helpers ──────────────────────────────────────
#
# These two helpers back the `unbound_report` tool (FCoP v1.1 Rule 0).
# They intentionally only read **file names + minimal frontmatter** (sender /
# recipient / thread_key) — never the task body — so an UNBOUND agent cannot
# accidentally pick up content that would bias its self-identified role.

def _collect_active_threads(limit: int = 10) -> list[dict]:
    """Scan tasks/ + reports/ and group by `thread_key`.

    Returns up to `limit` entries, each with `{thread_key, last_file, status,
    sender, recipient}`. Reads only frontmatter keys listed above. Does NOT
    read task bodies.

    按 thread_key 去重，只读 frontmatter（不读正文），给 UNBOUND 汇报用。
    """
    groups: dict[str, list[dict]] = {}

    for d, is_report in ((TASKS_DIR, False), (REPORTS_DIR, True)):
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            if f.name.lower() == "readme.md":
                continue
            fm = _parse_frontmatter(f)
            if fm.get("protocol") != "fcop":
                continue
            tk = fm.get("thread_key") or fm.get("task_id") or f.stem
            groups.setdefault(tk, []).append({
                "filename": f.name,
                "sender": fm.get("sender", "?"),
                "recipient": fm.get("recipient", "?"),
                "mtime": f.stat().st_mtime,
                "is_report": is_report,
            })

    summary: list[dict] = []
    for tk, items in groups.items():
        items.sort(key=lambda x: x["mtime"], reverse=True)
        latest = items[0]
        if latest["is_report"] and latest["recipient"].upper() == "ADMIN":
            status = "已结案 / closed (report → ADMIN)"
        else:
            status = f"等 {latest['recipient']} / waiting for {latest['recipient']}"
        summary.append({
            "thread_key": tk,
            "last_file": latest["filename"],
            "status": status,
            "mtime": latest["mtime"],
        })
    summary.sort(key=lambda x: x["mtime"], reverse=True)
    return summary[:limit]


def _rule_file_hash(filename: str) -> str:
    """Short hash of a bundled rule file (e.g. ``fcop-rules.mdc`` or
    ``fcop-protocol.mdc``).

    Used in the UNBOUND report so ADMIN can tell at a glance whether two
    agent sessions are looking at the same version of a given rule file.
    Resolution order: deployed copy under ``.cursor/rules/`` → packaged
    data under ``fcop/_data/``.
    """
    candidate = PROJECT_DIR / ".cursor" / "rules" / filename
    if candidate.exists():
        try:
            h = hashlib.sha256(candidate.read_bytes()).hexdigest()[:12]
            return f".cursor/rules/{filename} (sha256:{h})"
        except Exception:
            pass
    pkg_bytes = _packaged_data_bytes(filename)
    if pkg_bytes is not None:
        h = hashlib.sha256(pkg_bytes).hexdigest()[:12]
        return f"fcop/_data/{filename} (sha256:{h})"
    return f"({filename} 未找到 / not found)"


# ─── Validation helpers ───────────────────────────────────

_ROLE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_RESERVED_ROLE_CODES = {"ADMIN", "SYSTEM"}


def _validate_role_code(code: str) -> str | None:
    """Return None if the role code is legal, else a plain-language error.

    Rules derived from the task filename grammar
    (``_TASK_FILENAME_RE``): role codes become path segments, so they
    must be ASCII-only, start with an uppercase letter, and contain only
    ``A-Z`` / ``0-9`` / ``_``. Dashes and dots would collide with the
    filename's own field separators.
    """
    if not code:
        return "角色代码不能为空 / role code cannot be empty"
    if not _ROLE_CODE_RE.match(code):
        return (
            f"角色代码 '{code}' 非法：必须大写英文字母开头，只能用 A-Z / 0-9 / _"
            f"（不允许中文、空格、-、. ）。建议用英文职能词（MANAGER / CODER）"
            f"或全大写拼音（JINGLI / CHENGXU）。\n"
            f"Role code '{code}' is invalid: must start with an uppercase "
            f"letter and use only A-Z / 0-9 / _ (no Chinese, spaces, '-', '.'). "
            f"Prefer English job-function words (MANAGER / CODER) or "
            f"uppercase Pinyin (JINGLI / CHENGXU)."
        )
    if code in _RESERVED_ROLE_CODES:
        return (
            f"角色代码 '{code}' 是 FCoP 保留字（ADMIN / SYSTEM），不能作为团队角色。\n"
            f"Role code '{code}' is reserved by FCoP (ADMIN / SYSTEM) and "
            f"cannot be used as a team role."
        )
    return None


def _validate_team_config(
    roles: list[str], leader: str, *, allow_single: bool = False
) -> str | None:
    """Validate the roles list + leader for ``create_custom_team`` / ``init_solo``.

    Returns None if the config is legal, else a plain-language error string.
    """
    if not roles:
        return "角色列表不能为空 / roles list cannot be empty"
    if not allow_single and len(roles) < 2:
        return (
            "至少需要 2 个角色；如果只想一个人做，请用 init_solo(...) 启动 Solo 模式。\n"
            "At least 2 roles required; for a single-role setup, use init_solo(...) "
            "to enter Solo mode instead."
        )
    seen = set()
    for r in roles:
        err = _validate_role_code(r)
        if err:
            return err
        if r in seen:
            return f"角色代码 '{r}' 重复 / role code '{r}' appears more than once"
        seen.add(r)
    if leader not in roles:
        return (
            f"leader '{leader}' 必须在角色列表里（当前列表：{', '.join(roles)}）。\n"
            f"leader '{leader}' must be one of the declared roles "
            f"(current: {', '.join(roles)})."
        )
    return None


# ─── MCP Tools ────────────────────────────────────────────


@mcp.tool
def set_project_dir(path: str) -> str:
    """Pin the project root for this MCP session.

    Useful when the MCP process was spawned with the wrong working
    directory — typical symptom: `unbound_report` shows a project path
    like `C:\\Users\\<you>` instead of the workspace you actually opened
    in Cursor. Calling this tool once re-binds every subsequent tool
    call (list_tasks, write_task, init_*, ...) to the given directory,
    **without** editing mcp.json or restarting Cursor.

    Safe to call while UNBOUND — re-pointing at a directory is not a
    role-claim and writes nothing. It only mutates in-process state.

    Args:
        path: absolute path to the project root (the directory that
            should contain `docs/agents/` and `.cursor/rules/`). The
            directory must exist; it does not need to be an already
            initialized FCoP project (you may call this *before*
            ``init_solo`` / ``init_project``).

    Returns:
        A short bilingual confirmation including the resolved absolute
        path and whether `docs/agents/fcop.json` is present.
    """
    if not path or not isinstance(path, str):
        return (
            "错误：path 不能为空，需要传入绝对路径 / "
            "error: path must be a non-empty absolute path string"
        )
    try:
        resolved = Path(path).expanduser().resolve()
    except Exception as exc:
        return f"错误：路径无法解析 / error resolving path: {exc}"
    if not resolved.exists():
        return (
            f"错误：路径不存在 / error: path does not exist: {resolved}\n"
            "请先创建目录，或传入一个已存在的绝对路径。\n"
            "Create the directory first, or pass an existing absolute path."
        )
    if not resolved.is_dir():
        return (
            f"错误：路径不是目录 / error: path is not a directory: {resolved}"
        )

    _rebind_paths(resolved, "tool:set_project_dir")

    cfg_present = (resolved / "docs" / "agents" / "fcop.json").exists()
    rules_present = (resolved / ".cursor" / "rules" / "fcop-rules.mdc").exists()

    return (
        f"已绑定项目根 / project root bound: `{resolved}`\n"
        f"- docs/agents/fcop.json present: {'yes' if cfg_present else 'no'}\n"
        f"- .cursor/rules/fcop-rules.mdc present: "
        f"{'yes' if rules_present else 'no'}\n\n"
        f"下一步 / next: 调用 `unbound_report()` 查看绑定后状态；"
        f"未初始化的话再调 `init_solo` / `init_project` / "
        f"`create_custom_team`。\n"
        f"Call `unbound_report()` to view post-bind state; if not yet "
        f"initialized, call `init_solo` / `init_project` / "
        f"`create_custom_team`."
    )


@mcp.tool
def unbound_report(lang: str = "zh") -> str:
    """**FCoP v1.1 Rule 0 — MUST be the FIRST tool you call in a new session.**

    Returns ONE of two reports depending on project state:

    1) **Initialization report** — when `docs/agents/fcop.json` is missing.
       Phase-1 of any FCoP install: project is not initialized yet. The
       report shows the detected project dir + resolution source, lists
       the available init modes (Solo / preset teams / custom), and asks
       ADMIN to pick an initialization option. **It does NOT ask for a
       role assignment**, because there is no team to be part of yet.

    2) **UNBOUND report** — when `fcop.json` is present. Phase-2: project
       initialized, this session has no role. Report shows project state
       + a role-assignment template for ADMIN.

    Do NOT improvise, summarize, or decorate the output; paste it back to
    ADMIN as-is and STOP.

    While UNBOUND (or uninitialized) you MUST NOT:
      - read task **bodies** (frontmatter metadata only)
      - write any file (tasks / reports / rules / configs) — except via
        the explicit init tools (`init_solo`, `init_project`,
        `create_custom_team`) when ADMIN asks for them
      - claim a role from context clues
      - dispatch follow-up tasks

    You transition to BOUND only when BOTH hold:
      a) `fcop.json` exists (initialized), and
      b) ADMIN says literally: "你是 {ROLE}，在 {team}，线程 {thread_key}（可选）"
         / "You are {ROLE} on {team}, thread {thread_key} (optional)"

    ──────────────────────────────────────────────────────────
    FCoP Rule 0 / Rule 1：新会话启动**必调**的第一个工具。

    按项目状态**自动选**两种报告之一：

    1) **初始化汇报（Initialization report）**——当 `docs/agents/fcop.json`
       不存在时。任何 FCoP 项目的第一阶段：还没初始化。报告展示项目路径 +
       路径来源，列出可选初始化方式（Solo / 预设团队 / 自定义），请 ADMIN
       **选一个初始化方式**。**此时不问角色**——团队都还没建，指什么派。

    2) **UNBOUND 汇报**——当 `fcop.json` 存在时。第二阶段：项目已初始化、
       本会话未指派角色。报告展示项目状态 + 请 ADMIN 给出角色指派。

    原样回给 ADMIN，别润色、别改写。

    UNBOUND 或未初始化期间**严禁**：读任务正文、写任何文件（除 ADMIN 明确
    要求时调 `init_solo`/`init_project`/`create_custom_team`）、从上下文推断
    角色、派发后续任务。

    进入 BOUND 必须同时满足：a) `fcop.json` 存在，b) ADMIN 明确说出"你是
    {ROLE}，在 {team}"。

    Args:
        lang: "zh" or "en" (default "zh")
    """
    is_en = lang.lower().startswith("en")

    cfg_path = _team_config_path_read()
    cfg_present = cfg_path is not None
    cfg: dict = {}
    if cfg_present and cfg_path is not None:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    mode = cfg.get("mode", "(未声明 / undeclared)")
    team = cfg.get("team") or cfg.get("team_name") or "(未声明 / undeclared)"
    roles = cfg.get("roles", [])
    if roles and isinstance(roles, list):
        role_codes = [str(r.get("code", "?")) if isinstance(r, dict) else str(r) for r in roles]
    else:
        role_codes = []

    rules_dir = PROJECT_DIR / ".cursor" / "rules"
    rule_files: list[str] = []
    if rules_dir.exists():
        rule_files = sorted(f.name for f in rules_dir.glob("*.mdc"))

    active = _collect_active_threads(limit=10)
    rules_ver = _rule_file_hash("fcop-rules.mdc")
    protocol_ver = _rule_file_hash("fcop-protocol.mdc")

    def _fmt_threads() -> list[str]:
        if not active:
            return ["  - (无活跃线程 / no active threads)"]
        out = []
        for t in active:
            out.append(
                f"  - thread_key: `{t['thread_key']}` · last: `{t['last_file']}` · {t['status']}"
            )
        return out

    path_source = _STATE.get("source", "unknown")

    # Phase 1 — project NOT initialized. Show Initialization report, NOT
    # UNBOUND. Do not ask for a role; ask ADMIN to pick an init mode.
    if not cfg_present:
        if is_en:
            lines = [
                "## Initialization report (phase 1 — not initialized)",
                "",
                "> Governed by the **FCoP protocol** — rules in "
                "`.cursor/rules/fcop-rules.mdc`, commentary in "
                "`.cursor/rules/fcop-protocol.mdc` (both alwaysApply).",
                "",
                f"- project: `{PROJECT_DIR}`",
                f"  - resolution source: {path_source}",
                "- fcop.json present: **no**  ← project is not initialized yet",
                f"- .cursor/rules/*.mdc: {rule_files if rule_files else '(none)'}",
                f"- fcop-rules.mdc (packaged): {rules_ver}",
                f"- fcop-protocol.mdc (packaged): {protocol_ver}",
                "",
                "## Next step — ADMIN, please pick an initialization mode",
                "",
                "No role assignment yet. First we need a team to belong to.",
                "Reply with ONE of (copy-paste is fine):",
                "",
                "- **Solo** (recommended first-timer): `init_solo(role=\"ME\")`",
                "  — one human wearing one role, simplest setup",
                "- **Preset team**: `init_project(team=\"dev-team\")`",
                "  — also: `media-team`, `mvp-team`",
                "- **Custom team**: `create_custom_team(team_name=..., "
                "roles=[...], leader=...)`",
                "  — validates role codes (uppercase, A–Z/0–9/_, not `ADMIN`/`SYSTEM`)",
                "",
                "After initialization finishes I will:",
                "1. write `docs/agents/fcop.json` + rules + `LETTER-TO-ADMIN.md`",
                "2. print a short confirmation + **point you to the letter**",
                "3. re-enter **UNBOUND** state, at which point you assign a role",
                "",
                "Until ADMIN picks, I will not read task bodies and will not "
                "write any files. (FCoP Rule 1)",
            ]
        else:
            lines = [
                "## 初始化汇报（第一阶段 —— 未初始化）",
                "",
                "> 本会话受 **FCoP 协议** 约束 —— 协议规则见 "
                "`.cursor/rules/fcop-rules.mdc`，协议解释见 "
                "`.cursor/rules/fcop-protocol.mdc`（均为 alwaysApply）。",
                "",
                f"- 项目路径：`{PROJECT_DIR}`",
                f"  - 路径来源：{path_source}",
                "- fcop.json 是否存在：**否**  ← 项目尚未初始化",
                f"- .cursor/rules/*.mdc：{rule_files if rule_files else '(无)'}",
                f"- fcop-rules.mdc（包内原件）：{rules_ver}",
                f"- fcop-protocol.mdc（包内原件）：{protocol_ver}",
                "",
                "## 下一步 —— 请 ADMIN 选一种初始化方式",
                "",
                "**此时不分配角色**：团队都还没建，没有角色可选。",
                "请回复下列任一种（复制粘贴即可）：",
                "",
                "- **Solo 模式**（强推，首次用选这个）：`init_solo(role=\"ME\")`",
                "  —— 一个人担一个角色，最简配置",
                "- **预设团队**：`init_project(team=\"dev-team\")`",
                "  —— 也可选 `media-team`、`mvp-team`",
                "- **自定义团队**：`create_custom_team(team_name=..., "
                "roles=[...], leader=...)`",
                "  —— 会校验角色代码（大写、A–Z/0–9/_、禁用 `ADMIN`/`SYSTEM`）",
                "",
                "初始化完成后我会：",
                "1. 写入 `docs/agents/fcop.json` + 规则文件 + `LETTER-TO-ADMIN.md`",
                "2. 打印简短的确认信息，并**告诉 ADMIN 去读那封信**",
                "3. 重新进入 **UNBOUND** 状态，到那时你才给我派角色",
                "",
                "在 ADMIN 选定之前，我不会读任务正文、不会写任何文件。"
                "（FCoP Rule 1）",
            ]
        return "\n".join(lines)

    # Phase 2 — project IS initialized. Standard UNBOUND report + role
    # assignment template.
    if is_en:
        lines = [
            "## UNBOUND report (phase 2 — initialized, no role yet)",
            "",
            "> Governed by the **FCoP protocol** — rules in "
            "`.cursor/rules/fcop-rules.mdc`, commentary in "
            "`.cursor/rules/fcop-protocol.mdc` (both alwaysApply).",
            "",
            f"- project: `{PROJECT_DIR}`",
            f"  - resolution source: {path_source}",
            "- fcop.json present: **yes**",
            f"  - mode: {mode}",
            f"  - team: {team}",
            f"  - declared roles: [{', '.join(role_codes) if role_codes else '(empty)'}]",
            f"- .cursor/rules/*.mdc: {rule_files if rule_files else '(none)'}",
            f"- fcop-rules.mdc: {rules_ver}",
            f"- fcop-protocol.mdc: {protocol_ver}",
            f"- active threads (grouped by thread_key, frontmatter only):",
            *_fmt_threads(),
            "",
            "## My identity status: **UNBOUND**",
            "",
            "## Awaiting ADMIN role assignment",
            "",
            "Please reply in the form:",
            "> You are {ROLE} on {team}, thread {thread_key} (optional)",
            "",
            "Example:",
            "> You are PM on dev-team, thread anti_hang_triage_20260421",
            "",
            "Until then I will not read task bodies, will not write files, "
            "and will not claim a role. (FCoP Rule 1)",
        ]
    else:
        lines = [
            "## UNBOUND 汇报（第二阶段 —— 已初始化，未指派角色）",
            "",
            "> 本会话受 **FCoP 协议** 约束 —— 协议规则见 "
            "`.cursor/rules/fcop-rules.mdc`，协议解释见 "
            "`.cursor/rules/fcop-protocol.mdc`（均为 alwaysApply）。",
            "",
            f"- 项目路径：`{PROJECT_DIR}`",
            f"  - 路径来源：{path_source}",
            "- fcop.json 是否存在：**是**",
            f"  - mode: {mode}",
            f"  - team: {team}",
            f"  - 已声明角色：[{', '.join(role_codes) if role_codes else '(空)'}]",
            f"- .cursor/rules/*.mdc：{rule_files if rule_files else '(无)'}",
            f"- fcop-rules.mdc：{rules_ver}",
            f"- fcop-protocol.mdc：{protocol_ver}",
            f"- 活跃线程（按 thread_key 去重，只读 frontmatter）：",
            *_fmt_threads(),
            "",
            "## 我的身份状态：**UNBOUND（未指派）**",
            "",
            "## 等待 ADMIN 分配角色",
            "",
            "请用以下格式告诉我身份：",
            "> 你是 {ROLE}，在 {team}，线程 {thread_key}（可选）",
            "",
            "例如：",
            "> 你是 PM，在 dev-team，线程 anti_hang_triage_20260421",
            "",
            "在此之前，我不会读任务正文、不会写文件、不会自认角色。"
            "（FCoP Rule 1）",
        ]

    return "\n".join(lines)


@mcp.tool
def init_project(team: str = "dev-team", lang: str = "zh") -> str:
    """Initialize an FCoP project structure with a team template.

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
            f"# FCoP 协作项目 / FCoP Collaboration Project\n\n"
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
        "mode": "team",
        "team": team,
        "team_name": name,
        "roles": [{"code": r["code"], "label": _role_label(r, lang)} for r in tmpl["roles"]],
        "leader": tmpl["leader"],
        "lang": lang,
        "created_at": _now(),
    }
    config_file = AGENTS_DIR / "fcop.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    leader = tmpl["leader"]
    welcome = TASKS_DIR / f"TASK-{_today()}-001-SYSTEM-to-{leader}.md"
    if not welcome.exists():
        welcome.write_text(
            f"---\nprotocol: fcop\nversion: 1\ntask_id: TASK-{_today()}-001\n"
            f"sender: SYSTEM\nrecipient: {leader}\ncreated_at: {_now()}\n"
            f"priority: normal\ntype: setup\n---\n\n"
            f"# {t('welcome_title', lang)}\n\n"
            f"{t('team_template', lang)}: **{name}**\n\n"
            f"{t('your_members', lang)}: {', '.join(codes)}\n\n"
            f"{t('welcome_body', lang)}\n",
            encoding="utf-8",
        )

    notes = _deploy_rules_to_project()
    letter_note = _deploy_letter_to_project(lang)
    if letter_note:
        notes.append(letter_note)

    return (
        f"Project initialized: {name}\n"
        f"Directories: tasks/, reports/, issues/, shared/, log/\n"
        f"{t('roles', lang)}:\n{_role_table(tmpl, lang)}\n"
        f"{t('leader', lang)}: {leader}\n"
        + ("\n".join(notes) + "\n" if notes else "")
        + _init_next_steps(team, lang)
    )


def _deploy_one_rule(filename: str, source_subdir: str = "rules") -> str:
    """Deploy a single bundled rules file into `<project>/.cursor/rules/`.

    Never overwrites an existing file (the user may have edited it locally).
    Returns a short human-readable status line; empty string on no-op.
    """
    target = PROJECT_DIR / ".cursor" / "rules" / filename
    if target.exists():
        return ""
    data = _packaged_data_bytes(filename)
    if data is None:
        # Dev fallback: read from repo's rules/ dir alongside src/
        src = Path(__file__).resolve().parent.parent.parent / source_subdir / filename
        if src.exists():
            try:
                data = src.read_bytes()
            except Exception:
                data = None
    if data is None:
        return f"({filename} 未释放：源文件不可用 / source not available)"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        try:
            rel = target.relative_to(PROJECT_DIR).as_posix()
        except ValueError:
            rel = str(target)
        return f"Deployed: {rel}"
    except Exception as exc:  # pragma: no cover - filesystem surprises
        return f"({filename} 未释放：{exc.__class__.__name__})"


def _deploy_rules_to_project() -> list[str]:
    """Deploy the FCoP ruleset to ``<project>/.cursor/rules/``.

    Two sibling files — protocol rules + protocol commentary:

    - ``fcop-rules.mdc`` — the protocol rules themselves.
    - ``fcop-protocol.mdc`` — the protocol commentary explaining how each
      rule applies in practice (file naming, YAML shape, directory layout,
      patrol triggers, etc.).

    Both are ``alwaysApply: true`` so any Cursor-hosted agent sees them in
    every session. Never-overwrite on deploy to respect local edits.
    """
    notes: list[str] = []
    for fn in ("fcop-rules.mdc", "fcop-protocol.mdc"):
        msg = _deploy_one_rule(fn)
        if msg:
            notes.append(msg)
    return notes


def _init_next_steps(team_display: str, lang: str) -> str:
    """Standard 'next steps' footer printed by every `init_*` tool.

    The user pointed out (correctly) that FCoP is a three-phase flow —
    install → initialize → assign role — and early versions let those
    phases blur together. This footer explicitly marks the boundary
    between phase 2 (initialization just finished) and phase 3 (ADMIN
    assigns a role), so ADMIN never has to guess what comes next.
    """
    is_en = lang.lower().startswith("en")
    if is_en:
        return (
            "\n---\n"
            "**Next steps (ADMIN, please do this in order):**\n\n"
            "1. **Open** `docs/agents/LETTER-TO-ADMIN.md` — team rules, "
            "role naming conventions, daily usage. This is the manual.\n"
            "2. **Call `unbound_report()` again** — you'll now get the "
            "phase-2 UNBOUND report (fcop.json is present), not the "
            "phase-1 initialization report.\n"
            "3. **Assign a role** by saying literally:\n"
            f"   > You are {{ROLE}} on {team_display}, thread {{thread_key}} (optional)\n\n"
            "Until you assign a role, the agent will not read task "
            "bodies and will not write task files. (FCoP Rule 1)"
        )
    return (
        "\n---\n"
        "**下一步（ADMIN 请按顺序做）：**\n\n"
        "1. **打开** `docs/agents/LETTER-TO-ADMIN.md` —— 团队规则、角色"
        "命名约定、日常使用方法，这就是使用说明书。\n"
        "2. **再调一次 `unbound_report()`** —— 这次会拿到第二阶段的 "
        "UNBOUND 报告（fcop.json 已存在），不再是第一阶段的初始化报告。\n"
        "3. **分配角色**，原话如下：\n"
        f"   > 你是 {{ROLE}}，在 {team_display}，线程 {{thread_key}}（可选）\n\n"
        "在你分配角色之前，Agent 不会读任务正文、不会写任务文件。"
        "（FCoP Rule 1）"
    )


def _deploy_letter_to_project(lang: str) -> str:
    """Drop the LETTER-TO-ADMIN manual into ``docs/agents/`` on first init.

    Picks the language-matched bundled file
    (``letter-to-admin.{lang}.md``) and writes it as
    ``docs/agents/LETTER-TO-ADMIN.md``. Never overwrites an existing file.
    """
    target = AGENTS_DIR / "LETTER-TO-ADMIN.md"
    if target.exists():
        return ""
    lang_key = lang.lower() if lang else "zh"
    if lang_key not in ("zh", "en"):
        lang_key = "zh"
    filename = f"letter-to-admin.{lang_key}.md"
    data = _packaged_data_bytes(filename)
    if data is None:
        src = Path(__file__).resolve().parent / "_data" / filename
        if src.exists():
            try:
                data = src.read_bytes()
            except Exception:
                data = None
    if data is None:
        return f"(LETTER-TO-ADMIN.md 未释放：{filename} 不可用 / source not available)"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        try:
            rel = target.relative_to(PROJECT_DIR).as_posix()
        except ValueError:
            rel = str(target)
        return f"Deployed: {rel}"
    except Exception as exc:  # pragma: no cover - filesystem surprises
        return f"(LETTER-TO-ADMIN.md 未释放：{exc.__class__.__name__})"


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
    leader_up = leader.strip().upper()
    err = _validate_team_config(role_list, leader_up, allow_single=False)
    if err:
        return err

    for d in [TASKS_DIR, REPORTS_DIR, ISSUES_DIR, SHARED_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    config = {
        "mode": "team",
        "team": "custom",
        "team_name": team_name,
        "roles": [{"code": r, "label": r} for r in role_list],
        "leader": leader_up,
        "lang": lang,
        "created_at": _now(),
    }
    config_file = AGENTS_DIR / "fcop.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = AGENTS_DIR / "README.md"
    readme.write_text(
        f"# FCoP — {team_name}\n\n"
        f"{t('roles', lang)}: {', '.join(role_list)}\n"
        f"{t('leader', lang)}: {leader_up}\n",
        encoding="utf-8",
    )

    welcome = TASKS_DIR / f"TASK-{_today()}-001-SYSTEM-to-{leader_up}.md"
    if not welcome.exists():
        welcome.write_text(
            f"---\nprotocol: fcop\nversion: 1\ntask_id: TASK-{_today()}-001\n"
            f"sender: SYSTEM\nrecipient: {leader_up}\ncreated_at: {_now()}\n"
            f"priority: normal\ntype: setup\n---\n\n"
            f"# {t('welcome_title', lang)}\n\n"
            f"{t('team_template', lang)}: **{team_name}**\n\n"
            f"{t('your_members', lang)}: {', '.join(role_list)}\n\n"
            f"{t('welcome_body', lang)}\n",
            encoding="utf-8",
        )

    notes = _deploy_rules_to_project()
    letter_note = _deploy_letter_to_project(lang)
    if letter_note:
        notes.append(letter_note)

    return (
        f"{t('custom_created', lang)}: {team_name}\n"
        f"{t('roles', lang)}: {', '.join(role_list)}\n"
        f"{t('leader', lang)}: {leader_up}\n"
        + ("\n".join(notes) + "\n" if notes else "")
        + _init_next_steps(team_name, lang)
    )


@mcp.tool
def init_solo(
    role_code: str = "ME",
    role_label: str = "",
    lang: str = "zh",
) -> str:
    """Initialize an FCoP project in **Solo mode** (one AI role, no dispatch).

    Solo mode is for projects where a single agent works directly with
    ADMIN. Rule 0.b still applies: the agent uses files to split itself
    into *proposer* and *reviewer*, even though there is no second role.

    Args:
        role_code: The single role code. Must be uppercase letters / digits /
            underscore, starting with a letter. Cannot be ``ADMIN`` or
            ``SYSTEM`` (reserved). Default: ``ME``.
        role_label: Display label for this role (e.g. ``"我自己"`` or
            ``"Me"``). Defaults to the role code if empty.
        lang: Output language (``zh`` or ``en``).
    """
    role_code_up = role_code.strip().upper() if role_code else ""
    err = _validate_role_code(role_code_up)
    if err:
        return err

    for d in [TASKS_DIR, REPORTS_DIR, ISSUES_DIR, SHARED_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    label = role_label.strip() or role_code_up
    display_name = "Solo"
    config = {
        "mode": "solo",
        "team": "solo",
        "team_name": display_name,
        "roles": [{"code": role_code_up, "label": label}],
        "leader": role_code_up,
        "lang": lang,
        "created_at": _now(),
    }
    config_file = AGENTS_DIR / "fcop.json"
    config_file.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    readme = AGENTS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# FCoP — Solo\n\n"
            f"Mode: **solo**\n\n"
            f"{t('roles', lang)}: {role_code_up} ({label})\n"
            f"{t('leader', lang)}: {role_code_up}\n",
            encoding="utf-8",
        )

    welcome = TASKS_DIR / f"TASK-{_today()}-001-SYSTEM-to-{role_code_up}.md"
    if not welcome.exists():
        welcome.write_text(
            f"---\nprotocol: fcop\nversion: 1\ntask_id: TASK-{_today()}-001\n"
            f"sender: SYSTEM\nrecipient: {role_code_up}\ncreated_at: {_now()}\n"
            f"priority: normal\ntype: setup\n---\n\n"
            f"# {t('welcome_title', lang)}\n\n"
            f"Mode: **solo** — {t('your_members', lang)}: {role_code_up} ({label})\n\n"
            f"{t('welcome_body', lang)}\n",
            encoding="utf-8",
        )

    notes = _deploy_rules_to_project()
    letter_note = _deploy_letter_to_project(lang)
    if letter_note:
        notes.append(letter_note)

    header = (
        "已初始化 Solo 模式项目（一个 AI 角色，直接对 ADMIN）。"
        if lang == "zh"
        else "Solo-mode project initialized (one AI role, talks to ADMIN directly)."
    )
    return (
        f"{header}\n"
        f"mode: solo\n"
        f"{t('roles', lang)}: {role_code_up} ({label})\n"
        f"{t('leader', lang)}: {role_code_up}\n"
        + ("\n".join(notes) + "\n" if notes else "")
        + _init_next_steps("solo", lang)
    )


@mcp.tool
def validate_team_config(roles: str, leader: str) -> str:
    """Dry-run validation for a custom team config.

    Use this **before** calling ``create_custom_team`` to catch illegal
    role codes (Chinese characters, dashes, reserved names, etc.)
    without writing anything to disk.

    Args:
        roles: Comma-separated role codes (e.g. ``"MANAGER,CODER,TESTER"``).
        leader: Leader role code; must be one of the roles.

    Returns:
        ``"OK"`` if valid, else a plain-language error explaining what is
        wrong and how to fix it.
    """
    role_list = [r.strip().upper() for r in roles.split(",") if r.strip()]
    leader_up = leader.strip().upper()
    err = _validate_team_config(role_list, leader_up, allow_single=False)
    if err:
        return err
    return (
        "OK — roles and leader are valid.\n"
        f"  roles: {', '.join(role_list)}\n"
        f"  leader: {leader_up}"
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


# FCoP 任务文件名语法:TASK-{YYYYMMDD}-{NNN}-{SENDER}-to-{RECIPIENT}.md
# sender 只含字母/数字/下划线/连字符;recipient 还允许点号(槽位分隔)。
_TASK_FILENAME_RE = re.compile(
    r"^TASK-\d{8}-\d{3}-([A-Za-z][A-Za-z0-9_-]*)-to-([A-Za-z][A-Za-z0-9_.-]*)\.md$"
)


@mcp.tool
def inspect_task(filename: str) -> str:
    """Validate a task file against FCoP grammar (schema + filename↔frontmatter).

    This is a **wrench**: it catches the deterministic violations that raw
    read_file + regex agents routinely miss — filename says `to-DEV` but
    frontmatter says `recipient: QA`, `protocol` field mistyped, required
    field missing. Returns PASS or a bulleted list of violations.

    FCoP 文件语法校验工具。专门捕捉"文件名和 frontmatter 不一致""协议字段拼错"
    "必填字段缺失"这类 agent 用 read_file + 正则容易漏掉的确定性错误。

    Args:
        filename: Task filename or relative path under tasks/
                  (e.g. TASK-20260418-015-PM-to-DEV.md or batch/sub.md)
    """
    fp = TASKS_DIR / filename
    if not fp.exists():
        return f"File not found: {filename}"

    violations: list[str] = []
    fm = _parse_frontmatter(fp)
    if not fm:
        return f"FAIL: {fp.name}\n  - No YAML frontmatter found (file must start with ---)"

    for req in ("protocol", "version", "sender", "recipient"):
        if not fm.get(req, "").strip():
            violations.append(f"Missing required field: {req}")

    # 别名归一化已经在 _parse_frontmatter 里做过,到这里还不是 'fcop'/'1' 就是真的错了
    if fm.get("protocol") and fm["protocol"] != "fcop":
        violations.append(
            f"protocol value '{fm['protocol']}' is not canonical — expected 'fcop' (or known alias)"
        )
    if fm.get("version") and fm["version"] != "1":
        violations.append(
            f"version value '{fm['version']}' unexpected — expected integer 1"
        )

    m = _TASK_FILENAME_RE.match(fp.name)
    if not m:
        violations.append(
            "Filename does not match TASK-YYYYMMDD-NNN-SENDER-to-RECIPIENT.md"
        )
    else:
        fn_sender = m.group(1).upper()
        fn_recipient = m.group(2).upper()
        fm_sender = fm.get("sender", "").strip().upper()
        fm_recipient = fm.get("recipient", "").strip().upper()
        if fm_sender and fm_sender != fn_sender:
            violations.append(
                f"Sender mismatch: filename='{fn_sender}' vs frontmatter='{fm_sender}'"
            )
        if fm_recipient and fm_recipient != fn_recipient:
            violations.append(
                f"Recipient mismatch: filename='{fn_recipient}' vs frontmatter='{fm_recipient}'"
            )

    if not violations:
        return f"PASS: {fp.name}"
    return f"FAIL: {fp.name}\n  - " + "\n  - ".join(violations)


@mcp.tool
def drop_suggestion(content: str, context: str = "") -> str:
    """Pressure valve for agents who disagree with the current FCoP protocol.

    Call this INSTEAD of editing `fcop-rules.mdc` / `fcop-protocol.mdc`
    yourself. Writes a timestamped Markdown file to `.fcop/proposals/` and
    returns. No IDs, no schema, no review workflow — just land your
    disagreement as a file and move on. Humans review asynchronously. The
    value of this tool is entirely in the Rules-level contract "use this,
    don't touch the rules files".

    协议不满的泄压阀。**不要自己去改 `fcop-rules.mdc` / `fcop-protocol.mdc`**,
    调这个就完了。

    Args:
        content: What you want to suggest, in your own words
        context: Optional pointer to a task/report/file that triggered this
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = PROJECT_DIR / ".fcop" / "proposals" / f"{ts}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"# Suggestion @ {ts}\n\n"
    if context:
        header += f"**Context**: {context}\n\n"
    path.write_text(header + content, encoding="utf-8", newline="\n")
    return f"Dropped: {path.relative_to(PROJECT_DIR).as_posix()}"


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

    if lang == "en":
        lines.append("  **solo** — Solo mode (one AI role, talks to ADMIN directly)")
        lines.append("    tool: init_solo(role_code=\"ME\", lang=\"en\")\n")
    else:
        lines.append("  **solo** — Solo 模式（单个 AI 角色，直接对 ADMIN 说话）")
        lines.append("    工具：init_solo(role_code=\"ME\", lang=\"zh\")\n")

    for key, tmpl in TEAM_TEMPLATES.items():
        name = _team_name(tmpl, lang)
        lines.append(f"  **{key}** — {name}")
        lines.append(f"    {t('roles', lang)}:")
        for r in tmpl["roles"]:
            lines.append(f"      {r['code']} — {_role_label(r, lang)}")
        lines.append(f"    {t('leader', lang)}: {tmpl['leader']}\n")

    if lang == "en":
        lines.append(
            "\nCustom: use `create_custom_team` to define your own roles."
            "\nValidate first with `validate_team_config` to check role codes."
        )
    else:
        lines.append(
            "\n自定义：使用 `create_custom_team` 定义你自己的角色。"
            "\n不确定角色代码是否合法？先用 `validate_team_config` 做一次干跑。"
        )
    return "\n".join(lines)


# ─── MCP Resources ────────────────────────────────────────


def _resource_status_impl() -> str:
    return get_team_status()


@mcp.resource("fcop://status")
def resource_status() -> str:
    """Current FCoP project collaboration status summary."""
    return _resource_status_impl()


def _resource_config_impl() -> str:
    path = _team_config_path_read()
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return '{"status": "not initialized"}'


@mcp.resource("fcop://config")
def resource_config() -> str:
    """Current FCoP project configuration (fcop.json)."""
    return _resource_config_impl()


def _read_packaged_rule(filename: str) -> str:
    """Return the text of a bundled rule file, preferring the project-deployed
    copy under ``.cursor/rules/`` over the in-package fallback.
    """
    deployed = PROJECT_DIR / ".cursor" / "rules" / filename
    if deployed.exists():
        try:
            return deployed.read_text(encoding="utf-8")
        except Exception:
            pass
    pkg = _packaged_data_bytes(filename)
    if pkg is not None:
        try:
            return pkg.decode("utf-8")
        except Exception:
            return pkg.decode("utf-8", errors="replace")
    return f"({filename} not available)"


@mcp.resource("fcop://rules")
def resource_rules() -> str:
    """FCoP protocol rules — the rules every agent must follow."""
    return _read_packaged_rule("fcop-rules.mdc")


@mcp.resource("fcop://protocol")
def resource_protocol() -> str:
    """FCoP protocol commentary — how each rule applies in practice
    (file naming, YAML shape, directory layout, patrol triggers).
    Companion file to ``fcop-rules.mdc``."""
    return _read_packaged_rule("fcop-protocol.mdc")


def _read_packaged_letter(lang: str) -> str:
    """Return the Letter-to-ADMIN manual for the given language."""
    lang_key = lang.lower() if lang else "zh"
    if lang_key not in ("zh", "en"):
        lang_key = "zh"
    filename = f"letter-to-admin.{lang_key}.md"
    deployed = AGENTS_DIR / "LETTER-TO-ADMIN.md"
    if deployed.exists() and lang_key == (_load_project_config() or {}).get("lang", "zh"):
        try:
            return deployed.read_text(encoding="utf-8")
        except Exception:
            pass
    pkg = _packaged_data_bytes(filename)
    if pkg is not None:
        try:
            return pkg.decode("utf-8")
        except Exception:
            return pkg.decode("utf-8", errors="replace")
    src = Path(__file__).resolve().parent / "_data" / filename
    if src.exists():
        try:
            return src.read_text(encoding="utf-8")
        except Exception:
            pass
    return f"({filename} not available)"


@mcp.resource("fcop://letter/zh")
def resource_letter_zh() -> str:
    """FCoP 致 ADMIN 的一封信 —— 中文说明书（自建角色 / Solo / 预设）。"""
    return _read_packaged_letter("zh")


@mcp.resource("fcop://letter/en")
def resource_letter_en() -> str:
    """A Letter from FCoP to ADMIN — English manual (custom / Solo / preset)."""
    return _read_packaged_letter("en")


# ─── Entry Point ──────────────────────────────────────────


def main() -> None:
    """CLI entry point for `fcop` / `python -m fcop`."""
    mcp.run()


if __name__ == "__main__":
    main()

