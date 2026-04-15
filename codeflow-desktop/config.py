"""
CodeFlow Nudger 配置模块
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Lightweight i18n helper shared by all codeflow-desktop modules.
# Usage:
#     from config import _T, set_lang
#     set_lang("en")               # once at startup
#     msg = _T("cursor_not_found") # returns the string for current lang
#     msg = _T("file_missing", path=p)  # supports {path} placeholder
# ---------------------------------------------------------------------------

_LANG: str = "zh"

_I18N: dict[str, dict[str, str]] = {
    # ── cursor_embed ──
    "file_not_found":           {"zh": "文件不存在: {path}",              "en": "File not found: {path}"},
    "pyautogui_missing":        {"zh": "未安装 pyautogui",               "en": "pyautogui not installed"},
    "url_empty":                {"zh": "url 为空",                       "en": "URL is empty"},
    "cursor_win_not_found":     {"zh": "未找到 Cursor 主窗口",           "en": "Cursor main window not found"},
    "restart_no_exe":           {"zh": "重启失败：未找到 Cursor 可执行文件",  "en": "Restart failed: Cursor executable not found"},
    "restart_fail":             {"zh": "重启失败: {msg}",                "en": "Restart failed: {msg}"},
    "cdp_restart_timeout":      {"zh": "CDP 重启后等待 Cursor 窗口超时",  "en": "Timeout waiting for Cursor window after CDP restart"},
    "no_win_no_launch":         {"zh": "未找到 Cursor 窗口且不允许启动",  "en": "Cursor window not found and launch disabled"},
    "cursor_exe_not_found":     {"zh": "未找到 Cursor 可执行文件",        "en": "Cursor executable not found"},
    "launch_fail":              {"zh": "启动 Cursor 失败: {msg}",        "en": "Failed to launch Cursor: {msg}"},
    "wait_cursor_timeout":      {"zh": "等待 Cursor 窗口超时",           "en": "Timeout waiting for Cursor window"},
    # ── cursor_cdp ──
    "cdp_no_target":            {"zh": "未找到 CDP 目标（Cursor 未以 --remote-debugging-port 启动）",
                                 "en": "No CDP target (Cursor not started with --remote-debugging-port)"},
    "cdp_no_ws_url":            {"zh": "CDP 目标无 WebSocket URL",       "en": "CDP target has no WebSocket URL"},
    "cdp_ws_fail":              {"zh": "CDP WebSocket 连接失败: {url}",   "en": "CDP WebSocket connection failed: {url}"},
    "cdp_empty_result":         {"zh": "CDP 提取返回空结果",              "en": "CDP extraction returned empty"},
    "cdp_extract_error":        {"zh": "CDP 提取异常: {err}",            "en": "CDP extraction error: {err}"},
    # ── cursor_vision ──
    "ocr_no_text":              {"zh": "OCR 未识别到文字",                "en": "OCR found no text"},
    "screenshot_fail":          {"zh": "截图失败",                        "en": "Screenshot failed"},
    # ── web_panel API messages ──
    "panel_file_missing":       {"zh": "面板文件丢失",                    "en": "Panel file missing"},
    "cdp_unavailable":          {"zh": "CDP 不可用或未找到目标",           "en": "CDP unavailable or target not found"},
    "nudger_not_started":       {"zh": "nudger 未启动",                   "en": "Nudger not started"},
    "read_fail":                {"zh": "读取失败: {err}",                 "en": "Read failed: {err}"},
    "patrol_started":           {"zh": "巡检已启动",                      "en": "Patrol started"},
    "patrol_stopped":           {"zh": "巡检已停止",                      "en": "Patrol stopped"},
    "callback_not_registered":  {"zh": "回调未注册",                      "en": "Callback not registered"},
    "exiting":                  {"zh": "正在退出",                        "en": "Exiting"},
    "update_not_ready":         {"zh": "新版本尚未下载完成",              "en": "New version download not finished"},
    "updating_restart":         {"zh": "正在更新，程序将自动重启…",        "en": "Updating; the app will restart…"},
    "restarting":               {"zh": "正在重启…",                       "en": "Restarting…"},
    "reset_done":               {"zh": "已重置，请重新配置项目目录和团队",  "en": "Reset complete; reconfigure project directory and team"},
    "unknown_team":             {"zh": "未知团队: {name}",                "en": "Unknown team: {name}"},
    "project_dir_not_set":      {"zh": "项目目录未设置",                  "en": "Project directory not set"},
    "config_saved":             {"zh": "配置已保存",                      "en": "Settings saved"},
    "key_regenerated":          {"zh": "密钥已重新生成，所有设备需重新扫码",  "en": "Room key regenerated; all devices must scan again"},
    "unbound":                  {"zh": "已解绑: {name}",                  "en": "Unbound: {name}"},
    "path_empty":               {"zh": "路径不能为空",                    "en": "Path cannot be empty"},
    "dir_not_exist":            {"zh": "目录不存在: {path}",              "en": "Directory does not exist: {path}"},
    "switched_to":              {"zh": "已切换到: {path}",                "en": "Switched to: {path}"},
    "select_fail":              {"zh": "选择失败: {err}",                 "en": "Selection failed: {err}"},
    "nothing_selected":         {"zh": "未选择",                          "en": "Nothing selected"},
    "file_select_fail":         {"zh": "文件选择失败: {err}",             "en": "File selection failed: {err}"},
    "no_file_selected":         {"zh": "未选择文件",                      "en": "No file selected"},
    "file_not_exist":           {"zh": "文件不存在: {path}",              "en": "File does not exist: {path}"},
    "saved":                    {"zh": "已保存: {path}",                  "en": "Saved: {path}"},
    "missing_role_param":       {"zh": "缺少 role 参数",                  "en": "Missing role parameter"},
    "calibrate_timeout":        {"zh": "20 秒内未捕获到点击，请重试",      "en": "No click captured within 20s; try again"},
    "calibrate_recorded":       {"zh": "已记录",                          "en": "Recorded"},
    "listen_not_started":       {"zh": "未启动监听",                      "en": "Listening not started"},
    "nudger_not_ready":         {"zh": "Nudger 未就绪",                   "en": "Nudger not ready"},
    "cursor_win_not_found_s":   {"zh": "未找到 Cursor 窗口",             "en": "Cursor window not found"},
    "ocr_not_found_role":       {"zh": "OCR未找到 {role}，请确认侧栏可见",  "en": "OCR did not find {role}; ensure the sidebar is visible"},
    "role_files_copied":        {"zh": "角色文件已拷贝",                  "en": "Role files copied"},
    "missing_path_or_name":     {"zh": "缺少 path 或 name",              "en": "Missing path or name"},
    "installed":                {"zh": "已安装：{name}",                  "en": "Installed: {name}"},
    "install_fail":             {"zh": "安装失败: {err}",                 "en": "Install failed: {err}"},
    "unknown_repo":             {"zh": "未知仓库: {repo}",                "en": "Unknown repository: {repo}"},
    "no_external_dir":          {"zh": "无法确定 external/ 目录，请先设置项目目录",
                                 "en": "Cannot resolve external/; set project directory first"},
    "git_not_found":            {"zh": "未检测到 git，请先安装 Git for Windows：https://git-scm.com/download/win",
                                 "en": "Git not detected; install Git for Windows: https://git-scm.com/download/win"},
    "download_fail_all":        {"zh": "下载失败（已尝试直连和镜像）: {err}",
                                 "en": "Download failed (tried direct and mirrors): {err}"},
    "git_cmd_not_found":        {"zh": "未找到 git 命令，请先安装 Git",    "en": "git command not found; install Git first"},
    "operation_fail":           {"zh": "操作失败: {err}",                 "en": "Operation failed: {err}"},
    # ── web_panel preflight ──
    "pf_project_dir":           {"zh": "项目目录",                        "en": "Project directory"},
    "pf_not_set":               {"zh": "未设置",                          "en": "Not set"},
    "pf_dir_structure":         {"zh": "目录结构",                        "en": "Directory structure"},
    "pf_missing_subdirs":       {"zh": "缺少子目录",                      "en": "Missing subdirectories"},
    "pf_team_config":           {"zh": "团队配置",                        "en": "Team configuration"},
    "pf_not_initialized":       {"zh": "未初始化",                        "en": "Not initialized"},
    "pf_rules_skills_ready":    {"zh": "rules + skills + 角色文档 已就绪",  "en": "rules + skills + role docs ready"},
    "pf_rules_ready_docs_miss": {"zh": "rules 就绪，角色文档缺失",        "en": "rules ready; role docs missing"},
    "pf_not_copied":            {"zh": "未拷贝到项目",                    "en": "Not copied to project"},
    "pf_role_files":            {"zh": "角色文件",                        "en": "Role files"},
    "pf_cursor_window":         {"zh": "Cursor 窗口",                    "en": "Cursor window"},
    "pf_cursor_not_found":      {"zh": "未找到 Cursor，请先打开（或手动指定路径）",
                                 "en": "Cursor not found; open it first (or set path manually)"},
    "pf_ocr_not_mapped":        {"zh": "未执行 OCR 映射",                "en": "OCR mapping not run"},
    "pf_select_team_first":     {"zh": "请先选择团队（团队配置未就绪）",    "en": "Select a team first (team config not ready)"},
    "pf_ocr_lang":              {"zh": "OCR 语言包",                      "en": "OCR language packs"},
    "pf_ocr_scan_error":        {"zh": "OCR 扫描异常（坐标记录仍有效）",   "en": "OCR scan error (saved coordinates still valid)"},
    "pf_nudger_not_ready":      {"zh": "Nudger 未就绪，仅显示角色列表（可手动定位）",
                                 "en": "Nudger not ready; showing role list only (manual positioning)"},
    "pf_agent_mapping":         {"zh": "Agent 映射",                      "en": "Agent mapping"},
    # ── web_panel Tk dialogs ──
    "dlg_select_project":       {"zh": "选择项目文件夹",                  "en": "Select project folder"},
    "dlg_select_cursor":        {"zh": "选择 Cursor.exe",                "en": "Select Cursor.exe"},
    "dlg_executables":          {"zh": "可执行文件",                      "en": "Executable files"},
    "dlg_all_files":            {"zh": "所有文件",                        "en": "All files"},
    # ── web_panel TEAM_TEMPLATES ──
    "team_dev":                 {"zh": "软件开发团队",                    "en": "Software Development Team"},
    "role_pm":                  {"zh": "项目经理",                        "en": "Project Manager"},
    "role_dev":                 {"zh": "开发工程师",                      "en": "Developer"},
    "role_qa":                  {"zh": "测试工程师",                      "en": "QA Engineer"},
    "role_ops":                 {"zh": "运维工程师",                      "en": "Operations Engineer"},
    "team_media":               {"zh": "自媒体团队",                      "en": "Content / Media Team"},
    "role_collector":           {"zh": "素材采集",                        "en": "Asset Collection"},
    "role_writer":              {"zh": "拟题提纲",                        "en": "Topic & Outline"},
    "role_editor":              {"zh": "润色编辑",                        "en": "Editing & Polish"},
    "role_publisher":           {"zh": "审核发行",                        "en": "Review & Publishing"},
    "team_mvp":                 {"zh": "创业MVP团队",                    "en": "Startup MVP Team"},
    "role_builder":             {"zh": "快速原型",                        "en": "Rapid Prototyping"},
    "role_designer":            {"zh": "产品设计",                        "en": "Product Design"},
    "role_marketer":            {"zh": "增长运营",                        "en": "Growth & Marketing"},
    "role_researcher":          {"zh": "市场调研",                        "en": "Market Research"},
    "team_qa":                  {"zh": "专项测试团队",                    "en": "Dedicated QA Team"},
    "role_lead_qa":             {"zh": "测试负责人",                      "en": "QA Lead"},
    "role_tester":              {"zh": "功能测试",                        "en": "Functional Testing"},
    "role_auto_tester":         {"zh": "自动化测试",                      "en": "Automation Testing"},
    "role_perf_tester":         {"zh": "性能测试",                        "en": "Performance Testing"},
    # ── web_panel test_all steps ──
    "test_no_roles":            {"zh": "未读到角色配置，请先完成预检",      "en": "No roles found; complete preflight first"},
    "test_no_cursor":           {"zh": "未找到 Cursor 窗口",             "en": "Cursor window not found"},
    # ── nudger patrol_trace ──
    "tr_cdp_active":            {"zh": "CDP 巡检模式已激活（精度100%、延迟<100ms）",
                                 "en": "CDP patrol mode on (~100% accuracy, <100 ms latency)"},
    "tr_reload_stuck":          {"zh": "已执行 Reload Window（卡住恢复）", "en": "Reload Window executed (stuck recovery)"},
    "tr_focus_fail":            {"zh": "无法聚焦 Cursor 窗口",           "en": "Failed to focus Cursor window"},
    "tr_sent_cdp":              {"zh": "已向 Agent 输入框发送（CDP）",     "en": "Message sent to Agent input (CDP)"},
    "tr_sent":                  {"zh": "已向 Agent 输入框发送",           "en": "Message sent to Agent input"},
    "tr_switch_paste_fail":     {"zh": "切换 Tab 或粘贴发送失败",         "en": "Failed to switch tab or paste/send"},
    "tr_nonstandard_files":     {"zh": "tasks/ 中存在非标准命名的 .md，不参与自动催办配对",
                                 "en": "Non-standard .md in tasks/; skipped for auto-nudge pairing"},
    "tr_scan_done":             {"zh": "已扫描 tasks/ 全部标准任务",       "en": "Scanned all standard tasks in tasks/"},
    "tr_open_queued":           {"zh": "未闭环任务已加入催办队列",         "en": "Open tasks queued for nudge"},
    "tr_watcher_on":            {"zh": "已启用目录监听，新 .md 会打断轮询等待",
                                 "en": "Directory watch on; new .md wakes poll"},
    "tr_agent_busy":            {"zh": "Agent 正忙，下一轮再试",          "en": "Agent busy; retry next round"},
    "tr_max_retries":           {"zh": "同一文件重试次数用尽，停止催办",    "en": "Max retries for this file; stopping nudge"},
    "tr_cooldown":              {"zh": "该收件人冷却中，下一轮再试",       "en": "Cooldown active; retry next round"},
    "tr_processing":            {"zh": "处理文件",                        "en": "Processing file"},
    "tr_parse_fail":            {"zh": "文件名无法解析收件人，跳过",       "en": "Cannot parse recipient from filename; skip"},
    "tr_human_skip":            {"zh": "人工/ADMIN 类收件人不自动催办",    "en": "Human/ADMIN recipient; no auto nudge"},
    "tr_cursor_found":          {"zh": "已找到 Cursor 窗口",             "en": "Cursor window found"},
    "tr_nudge_done":            {"zh": "该任务文件已完成催办闭环",         "en": "Nudge completed for this task file"},
    "tr_no_cursor":             {"zh": "未找到 Cursor 窗口，无法催办",    "en": "Cursor window not found; cannot nudge"},
    "tr_auto_continue":         {"zh": "检测到「等待确认」类文案，已自动发送继续",
                                 "en": "Waiting-for-confirmation detected; sent Continue"},
    "tr_stuck_nudge":           {"zh": "对长时间无报告的任务发催促",       "en": "Nudging task with no report for a long time"},
    "tr_stuck_sent":            {"zh": "卡住任务催促已发送",              "en": "Stuck-task nudge sent"},
    "tr_greet_skip":            {"zh": "打招呼跳过：无 Cursor 窗口",      "en": "Greeting skipped: no Cursor window"},
    "tr_greet_start":           {"zh": "开始向各 Agent 打招呼",           "en": "Starting greetings to all Agents"},
    "tr_greeting":              {"zh": "正在打招呼",                      "en": "Greeting in progress"},
    "tr_greet_cdp":             {"zh": "打招呼已发送（CDP）",             "en": "Greeting sent (CDP)"},
    "tr_sidebar_miss":          {"zh": "第{n}次侧栏未找到角色，重试",      "en": "Attempt {n}: role not in sidebar; retrying"},
    "tr_switch_miss":           {"zh": "第{n}次未确认切换，重试",          "en": "Attempt {n}: switch not confirmed; retrying"},
    "tr_greet_sent":            {"zh": "打招呼已发送",                    "en": "Greeting sent"},
    "tr_greet_fail":            {"zh": "打招呼3次失败，跳过该角色",        "en": "Greeting failed after 3 attempts; skip role"},
    "tr_patrol_on":             {"zh": "巡检已启动",                      "en": "Patrol started"},
    "tr_patrol_on_detail":      {"zh": "已接手未完成任务队列；将轮询新文件并做 idle/stuck 检测",
                                 "en": "Queued open tasks; polling; idle/stuck checks active"},
    "tr_greet_error":           {"zh": "启动时各 Agent 问候异常",         "en": "Greeting error on startup"},
    "tr_patrol_off":            {"zh": "巡检已停止：不再处理新文件与自动 kick",
                                 "en": "Patrol stopped: no new files or auto-kick"},
    "tr_anomaly_reload":        {"zh": "检测到 Cursor 异常，自动 Reload Window",
                                 "en": "Cursor anomaly detected; Reload Window"},
    "tr_relay_focus":           {"zh": "手机/面板请求：聚焦 Cursor",       "en": "Mobile/panel action: focus Cursor"},
    "tr_relay_focus_fail":      {"zh": "手机/面板请求：聚焦 Cursor 失败",   "en": "Mobile/panel action: focus Cursor failed"},
    "tr_relay_restart":         {"zh": "手机/面板请求：重启巡检进程",       "en": "Mobile/panel action: restart patrol"},
    "tr_relay_notify":          {"zh": "中继下发：尝试通知 Cursor",        "en": "Relay: notifying Cursor"},
    # ── nudger return messages ──
    "cursor_focused":           {"zh": "Cursor 已聚焦",                  "en": "Cursor focused"},
    "patrol_already_running":   {"zh": "巡检已在运行",                    "en": "Patrol already running"},
    "patrol_not_running":       {"zh": "巡检未在运行",                    "en": "Patrol not running"},
    "patrol_restarted":         {"zh": "巡检已重启",                      "en": "Patrol restarted"},
    "unknown_action":           {"zh": "未知动作: {action}",              "en": "Unknown action: {action}"},
    "vision_not_loaded":        {"zh": "cursor_vision 模块未加载",        "en": "cursor_vision module not loaded"},
}


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = lang


def get_lang() -> str:
    return _LANG


def _T(key: str, **kwargs: object) -> str:
    """Return the localized string for *key*, formatted with *kwargs*."""
    entry = _I18N.get(key)
    if entry is None:
        return key
    text = entry.get(_LANG) or entry.get("zh") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


@dataclass
class NudgerConfig:
    project_dir: Path = field(default_factory=lambda: Path.cwd())
    relay_url: str = "wss://ai.chedian.cc/codeflow/ws/"
    room_key: str = ""
    device_id: str = "codeflow-nudger"
    # 巡检主循环：扫描 tasks/reports/issues 的间隔（秒）
    poll_interval: float = 5.0
    nudge_cooldown: float = 15.0
    lang: str = "zh"
    # 查找 Cursor 窗口（预检与催办共用）
    find_cursor_max_attempts: int = 4
    find_cursor_retry_delay_s: float = 0.12
    # 每 N 轮主循环执行一次：idle 自动「继续」/ 卡住任务催促
    idle_check_every_n: int = 6
    stuck_check_every_n: int = 30
    # 任务「卡住」判定（秒）：tasks/ 下某 .md 自上次修改起超过 stuck_threshold 视为可能卡住；
    # 超过 timeout_threshold 视为超时；同一任务两次自动催促至少间隔 auto_nudge_interval_s。
    task_stuck_threshold_s: float = 600.0   # 10 分钟
    task_timeout_threshold_s: float = 1200.0  # 20 分钟
    auto_nudge_interval_s: float = 300.0  # 5 分钟（同一 TASK 编号重复催促的最小间隔）
    # 后续催办（非首次身份确认）短句；空字符串则使用内置默认
    patrol_ping_zh: str = ""
    patrol_ping_en: str = ""
    # 自动催促卡住任务前：执行「Developer: Reload Window」以恢复卡死 UI（Windows）
    stuck_reload_window: bool = True
    stuck_reload_min_age_s: float = 600.0  # 任务「久未闭环」至少这么久才触发 reload（与 stuck 阈值对齐）
    stuck_reload_once_per_task: bool = True  # 每个 TASK 编号仅 reload 一次，避免反复刷窗口
    reload_window_wait_s: float = 12.0  # reload 后等待 Cursor 就绪再发短句催办
    # 若已安装 watchdog，则监听目录 .md 变更并打断睡眠，加快响应新文件
    use_file_watcher: bool = True
    # 主循环：在 poll_interval 基础上再叠加 [min,max] 秒随机等待，打散与 Cursor 的同步节奏
    patrol_sleep_jitter_s: tuple[float, float] = (0.4, 2.5)
    # 每次成功向 Agent 发送一条消息（催办/卡住/idle kick/打招呼）后额外随机等待 [min,max] 秒
    post_send_jitter_s: tuple[float, float] = (0.25, 1.8)
    # 启动并打开面板浏览器后，自动尝试 Windows 左右分屏（Cursor 左、面板右，见 win_snap）
    auto_snap_on_launch: bool = True
    # 实验性：Cursor ACP/JSON-RPC HTTP 端点（若已配置且调用成功，则不再用系统浏览器 + win_snap）
    cursor_acp_endpoint: str = ""
    cursor_acp_layout: str = "split-right"
    cursor_acp_width_ratio: float = 0.35
    # 启动后面板：优先在 Cursor 内 Simple Browser 打开 18765（失败再系统浏览器 + 分屏）
    open_panel_in_cursor: bool = True
    launch_cursor_if_absent: bool = True
    cursor_exe_path: str = ""

    input_offset: tuple[float, float] = (0.80, 55)

    @property
    def agents_dir(self) -> Path:
        return self.project_dir / "docs" / "agents"

    @property
    def tasks_dir(self) -> Path:
        return self.agents_dir / "tasks"

    @property
    def reports_dir(self) -> Path:
        return self.agents_dir / "reports"

    @property
    def issues_dir(self) -> Path:
        return self.agents_dir / "issues"

    @property
    def log_dir(self) -> Path:
        return self.agents_dir / "log"
