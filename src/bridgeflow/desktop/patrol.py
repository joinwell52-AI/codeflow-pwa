from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from bridgeflow.config import PatrolConfig
from bridgeflow.file_watcher import decide_notify_targets, scan_markdown_files


@dataclass
class PatrolDoctorResult:
    tasks_dir_exists: bool
    reports_dir_exists: bool
    templates_dir_exists: bool
    template_count: int
    missing_templates: list[str]
    pyautogui_available: bool


def run_doctor(config: PatrolConfig) -> PatrolDoctorResult:
    missing = []
    template_count = 0
    if config.templates_dir.exists():
        template_count = len(list(config.templates_dir.glob("*.png")))
    for name in config.all_worker_chats:
        if not (config.templates_dir / f"{name}.png").exists():
            missing.append(f"{name}.png")
    if not (config.templates_dir / "generating.png").exists():
        missing.append("generating.png")

    try:
        import pyautogui  # noqa: F401
        pyautogui_available = True
    except Exception:
        pyautogui_available = False

    return PatrolDoctorResult(
        tasks_dir_exists=config.tasks_dir.exists(),
        reports_dir_exists=config.reports_dir.exists(),
        templates_dir_exists=config.templates_dir.exists(),
        template_count=template_count,
        missing_templates=missing,
        pyautogui_available=pyautogui_available,
    )


def print_doctor_result(result: PatrolDoctorResult) -> None:
    print("=== BridgeFlow doctor ===")
    print(f"tasks 目录: {'OK' if result.tasks_dir_exists else '缺失'}")
    print(f"reports 目录: {'OK' if result.reports_dir_exists else '缺失'}")
    print(f"templates 目录: {'OK' if result.templates_dir_exists else '缺失'}")
    print(f"模板数量: {result.template_count}")
    print(f"pyautogui: {'可用' if result.pyautogui_available else '未安装/不可用'}")
    if result.missing_templates:
        print("缺失模板:")
        for item in result.missing_templates:
            print(f"- {item}")
    else:
        print("模板检查: OK")


def patrol_once(config: PatrolConfig) -> set[str]:
    current_tasks = scan_markdown_files(config.tasks_dir)
    current_reports = scan_markdown_files(config.reports_dir)
    return decide_notify_targets(current_tasks, current_reports, config.role_to_chat)


def monitor_targets(config: PatrolConfig, callback) -> None:
    known_tasks = scan_markdown_files(config.tasks_dir)
    known_reports = scan_markdown_files(config.reports_dir)

    while True:
        time.sleep(config.patrol_poll_interval)
        current_tasks = scan_markdown_files(config.tasks_dir)
        current_reports = scan_markdown_files(config.reports_dir)
        new_tasks = current_tasks - known_tasks
        new_reports = current_reports - known_reports
        if new_tasks or new_reports:
            callback(new_tasks, new_reports, decide_notify_targets(new_tasks, new_reports, config.role_to_chat))
            known_tasks = current_tasks
            known_reports = current_reports
