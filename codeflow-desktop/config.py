"""
CodeFlow Nudger 配置模块
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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

    hotkeys: dict[str, tuple] = field(default_factory=lambda: {
        "PM":  ("ctrl", "alt", "1"),
        "DEV": ("ctrl", "alt", "2"),
        "QA":  ("ctrl", "alt", "3"),
        "OPS": ("ctrl", "alt", "4"),
    })

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
