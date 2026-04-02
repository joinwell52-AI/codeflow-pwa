from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import socket
import sys
import uuid
from pathlib import Path

from bridgeflow.binding import approve_bind, clear_binding, issue_bind_code, private_bind_state, public_bind_state
from bridgeflow.config import DEFAULT_CONFIG_NAME, DEFAULT_FIXED_ROLES, load_config
from bridgeflow.desktop.executor import execute_desktop_action
from bridgeflow.desktop.patrol import patrol_once, print_doctor_result, run_doctor
from bridgeflow.desktop.runner import start_desktop_bridge
from bridgeflow.task_writer import write_admin_task, write_role_reply


def _default_project_root() -> Path:
    return Path.cwd()


def _slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    clean = clean.strip("-").lower()
    return clean or "bridgeflow-pc"


def _build_machine_code(hostname: str) -> str:
    seed = f"{hostname}-{uuid.getnode()}".encode("utf-8", errors="ignore")
    digest = hashlib.sha1(seed).hexdigest()[:12].upper()
    return f"BF-{digest}"


def _print_bind_state(state: dict) -> None:
    print(f"绑定状态：{state.get('status', '')}")
    print(f"机器码：{state.get('machine_code', '')}")
    if state.get("pending_bind_code"):
        print(f"一次性绑定码：{state['pending_bind_code']}")
    if state.get("pending_bind_expires_at"):
        print(f"绑定码过期时间：{state['pending_bind_expires_at']}")
    if state.get("pending_mobile_device_id") or state.get("pending_mobile_device_name"):
        print(f"待确认手机：{state.get('pending_mobile_device_name', '')} {state.get('pending_mobile_device_id', '')}".strip())
    if state.get("bound_mobile_device_id") or state.get("bound_mobile_device_name"):
        print(f"已绑定手机：{state.get('bound_mobile_device_name', '')} {state.get('bound_mobile_device_id', '')}".strip())
    if state.get("bound_at"):
        print(f"绑定时间：{state['bound_at']}")


def _print_action_result(result: dict) -> None:
    print(f"动作：{result.get('action', '')}")
    print(f"结果：{'成功' if result.get('ok') else '失败'}")
    print(f"说明：{result.get('message', '')}")
    print(f"窗口数：{result.get('window_count', 0)}")
    print(f"目标窗口：{result.get('target_title', '')}")
    if result.get("typed_text"):
        print(f"发送文本：{result['typed_text']}")
    print(f"dry-run：{result.get('dry_run', False)}")


def cmd_init(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or _default_project_root()).resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    target = project_root / DEFAULT_CONFIG_NAME
    example = Path(__file__).resolve().parent / "data" / DEFAULT_CONFIG_NAME
    if target.exists() and not args.force:
        # 即使配置已存在，也允许用参数覆盖指定字段
        raw = json.loads(target.read_text(encoding="utf-8-sig"))
        changed = False
        if getattr(args, "relay_url", None):
            raw.setdefault("relay", {})["url"] = args.relay_url
            changed = True
        if getattr(args, "room_key", None):
            raw.setdefault("relay", {})["room_key"] = args.room_key
            changed = True
        if changed:
            target.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已更新配置：{target}")
        else:
            print(f"配置已存在：{target}")
        return 0

    hostname = socket.gethostname() or "BridgeFlow-PC"
    raw = json.loads(example.read_text(encoding="utf-8-sig"))
    raw["project"]["root_dir"] = str(project_root)
    raw.setdefault("device", {})
    raw["device"]["device_id"] = f"{_slug(hostname)}-pc"
    raw["device"]["device_name"] = f"{hostname} AI执行机"
    raw["device"].setdefault("owner_role", "PM01")
    raw["device"]["machine_code"] = _build_machine_code(hostname)
    if getattr(args, "relay_url", None):
        raw.setdefault("relay", {})["url"] = args.relay_url
    if getattr(args, "room_key", None):
        raw.setdefault("relay", {})["room_key"] = args.room_key

    raw.setdefault("ai_team", {})
    raw["ai_team"]["fixed_roles"] = DEFAULT_FIXED_ROLES[:]
    raw["ai_team"]["cursor_only"] = True

    raw.setdefault("bind", {})
    raw["bind"].setdefault("status", "unbound")
    raw["bind"].setdefault("bound_mobile_device_id", "")
    raw["bind"].setdefault("bound_mobile_device_name", "")
    raw["bind"].setdefault("bound_at", "")
    raw["bind"].setdefault("bind_code_ttl_seconds", 600)
    raw["bind"].setdefault("pending_bind_code", "")
    raw["bind"].setdefault("pending_bind_expires_at", "")
    raw["bind"].setdefault("pending_mobile_device_id", "")
    raw["bind"].setdefault("pending_mobile_device_name", "")
    raw["bind"].setdefault("last_bind_code_issued_at", "")

    raw.setdefault("runtime", {})
    raw["runtime"].setdefault("runtime_dir", ".bridgeflow/runtime")
    raw["runtime"].setdefault("status_dir", ".bridgeflow/runtime/status")
    raw["runtime"].setdefault("task_details_dir", ".bridgeflow/runtime/task_details")
    raw["runtime"].setdefault("idle_seconds", 180)
    raw["runtime"].setdefault("stale_task_seconds", 900)

    target.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    config = load_config(target)
    config.ensure_runtime_dirs()

    # 安装 .cursor/rules/ mdc 角色规则文件
    rules_src = Path(__file__).resolve().parent / "data" / "rules"
    rules_dst = project_root / ".cursor" / "rules"
    if rules_src.exists():
        rules_dst.mkdir(parents=True, exist_ok=True)
        import shutil
        for mdc in rules_src.glob("*.mdc"):
            shutil.copy2(mdc, rules_dst / mdc.name)
        print(f"已安装 Cursor 规则：{rules_dst}")

    print(f"已生成配置：{target}")
    print(f"设备ID：{config.device_id}")
    print(f"机器码：{config.machine_code}")
    print(f"运行态目录：{config.runtime_dir}")
    return 0


def cmd_write_admin_task(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    written = write_admin_task(
        config,
        args.text,
        recipient=args.recipient,
        priority=args.priority,
        attachments=args.attachments or [],
        thread_key=args.thread_key,
    )
    print(f"已写入：{written.path}")
    print(f"线程：{written.thread_key}")
    return 0


def cmd_write_reply(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    written = write_role_reply(
        config,
        args.text,
        sender=args.sender,
        recipient=args.recipient,
        priority=args.priority,
        attachments=args.attachments or [],
        thread_key=args.thread_key,
    )
    print(f"已写入：{written.path}")
    print(f"线程：{written.thread_key}")
    return 0


def cmd_bind_status(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _print_bind_state(private_bind_state(config))
    return 0


def cmd_bind_code(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    state = issue_bind_code(
        config,
        mobile_device_id=args.mobile_device_id,
        mobile_device_name=args.mobile_device_name,
    )
    _print_bind_state(state)
    return 0


def cmd_approve_bind(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    state = approve_bind(
        config,
        bind_code=args.code,
        mobile_device_id=args.mobile_device_id,
        mobile_device_name=args.mobile_device_name,
    )
    _print_bind_state(state)
    return 0


def cmd_unbind(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    state = clear_binding(config)
    _print_bind_state(state)
    return 0


def cmd_desktop_action(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = execute_desktop_action(config, args.action, dry_run=args.dry_run).to_dict()
    _print_action_result(result)
    return 0 if result.get("ok") else 1


def cmd_relay_connect(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    asyncio.run(start_desktop_bridge(config))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    import webbrowser
    from bridgeflow.dashboard.server import DASHBOARD_PORT, start_dashboard, update_status
    from bridgeflow.env_check import check_env

    config = load_config(args.config)

    # 环境检测
    print("=" * 52)
    print("  BridgeFlow PC 执行机")
    print("=" * 52)
    env = check_env()
    print(f"  操作系统  : {env.os_name} {env.os_version[:30]}")
    print(f"  Python    : {env.python_version}  {'✓' if env.python_ok else '✗ 需要 >=3.10'}")
    print(f"  Cursor    : {'✓ ' + ('运行中' if env.cursor_running else '已安装') if env.cursor_installed else '✗ 未检测到，请安装 https://cursor.com'}")
    print(f"  设备ID    : {config.device_id}")
    print(f"  机器码    : {config.machine_code}")
    print(f"  中继      : {config.relay_url}")
    print("=" * 52)

    # 启动本地仪表盘
    start_dashboard(config)
    url = f"http://localhost:{DASHBOARD_PORT}"
    print(f"\n  仪表盘已启动：{url}")
    print("  正在打开浏览器…\n")
    webbrowser.open(url)

    # 启动桥接主循环
    from bridgeflow.desktop.runner import start_desktop_bridge

    def on_connected():
        update_status(relay_connected=True)
        print(f"  [BridgeFlow] ✓ 已连接中继 {config.relay_url}")

    def on_disconnected(exc):
        update_status(relay_connected=False)
        print(f"  [BridgeFlow] 断线，重连中… ({exc})")

    asyncio.run(start_desktop_bridge(config,
                                     on_connected=on_connected,
                                     on_disconnected=on_disconnected))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    config.validate_roles()
    config.ensure_runtime_dirs()
    result = run_doctor(config)
    print_doctor_result(result)
    return 0 if result.tasks_dir_exists and result.reports_dir_exists else 1


def cmd_patrol_once(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    targets = sorted(patrol_once(config))
    if not targets:
        print("本轮未发现需要巡检的目标。")
        return 0
    print("本轮目标：")
    for item in targets:
        print(f"- {item}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bridgeflow", description="BridgeFlow 人机协作桥接与团队巡检工具")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="生成默认 bridgeflow_config.json")
    init_p.add_argument("--project-root", default="")
    init_p.add_argument("--force", action="store_true")
    init_p.add_argument("--relay-url", default="", help="中继服务器地址，覆盖默认值")
    init_p.add_argument("--room-key", default="", help="房间号，覆盖默认值")
    init_p.set_defaults(func=cmd_init)

    bind_status_p = sub.add_parser("bind-status", help="查看当前绑定状态")
    bind_status_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    bind_status_p.set_defaults(func=cmd_bind_status)

    bind_code_p = sub.add_parser("bind-code", help="生成一次性绑定码")
    bind_code_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    bind_code_p.add_argument("--mobile-device-id", default="")
    bind_code_p.add_argument("--mobile-device-name", default="")
    bind_code_p.set_defaults(func=cmd_bind_code)

    approve_bind_p = sub.add_parser("approve-bind", help="确认手机绑定")
    approve_bind_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    approve_bind_p.add_argument("--code", required=True)
    approve_bind_p.add_argument("--mobile-device-id", required=True)
    approve_bind_p.add_argument("--mobile-device-name", default="")
    approve_bind_p.set_defaults(func=cmd_approve_bind)

    unbind_p = sub.add_parser("unbind", help="解除当前绑定")
    unbind_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    unbind_p.set_defaults(func=cmd_unbind)

    action_p = sub.add_parser("desktop-action", help="执行 PC 端桌面动作")
    action_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    action_p.add_argument("--action", choices=["focus_cursor", "inspect", "start_work"], required=True)
    action_p.add_argument("--dry-run", action="store_true")
    action_p.set_defaults(func=cmd_desktop_action)

    write_p = sub.add_parser("write-admin-task", help="直接生成 ADMIN01 -> PM01 任务文件")
    write_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    write_p.add_argument("--text", required=True)
    write_p.add_argument("--recipient", default="")
    write_p.add_argument("--priority", default="")
    write_p.add_argument("--thread-key", default="")
    write_p.add_argument("--attachments", nargs="*")
    write_p.set_defaults(func=cmd_write_admin_task)

    reply_p = sub.add_parser("write-reply", help="直接生成 PM/DEV/QA -> ADMIN01 回执文件")
    reply_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    reply_p.add_argument("--sender", required=True, help="发送角色，如 PM01/DEV01/QA01")
    reply_p.add_argument("--recipient", default="ADMIN01")
    reply_p.add_argument("--text", required=True)
    reply_p.add_argument("--priority", default="")
    reply_p.add_argument("--thread-key", default="")
    reply_p.add_argument("--attachments", nargs="*")
    reply_p.set_defaults(func=cmd_write_reply)

    relay_p = sub.add_parser("relay-connect", help="连接中继并启动桌面桥接")
    relay_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    relay_p.set_defaults(func=cmd_relay_connect)

    doctor_p = sub.add_parser("doctor", help="检查目录、模板和 pyautogui 环境")
    doctor_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    doctor_p.set_defaults(func=cmd_doctor)

    patrol_p = sub.add_parser("patrol-once", help="扫描当前任务/报告并输出本轮巡检目标")
    patrol_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    patrol_p.set_defaults(func=cmd_patrol_once)

    run_p = sub.add_parser("run", help="启动桌面桥接主循环")
    run_p.add_argument("--config", default=DEFAULT_CONFIG_NAME)
    run_p.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
