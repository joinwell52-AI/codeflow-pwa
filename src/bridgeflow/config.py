from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_NAME = "bridgeflow_config.json"
DEFAULT_FIXED_ROLES = ["ADMIN01", "PM01", "DEV01", "QA01"]


@dataclass
class PatrolConfig:
    raw: dict
    path: Path

    @property
    def relay_url(self) -> str:
        return str(self.raw.get("relay", {}).get("url", "")).strip()

    @property
    def room_key(self) -> str:
        return str(self.raw.get("relay", {}).get("room_key", "")).strip()

    @property
    def shared_secret(self) -> str:
        return str(self.raw.get("relay", {}).get("shared_secret", "")).strip()

    @property
    def device_id(self) -> str:
        return str(self.raw.get("device", {}).get("device_id", "")).strip()

    @property
    def device_name(self) -> str:
        return str(self.raw.get("device", {}).get("device_name", "")).strip()

    @property
    def owner_role(self) -> str:
        return str(self.raw.get("device", {}).get("owner_role", "")).strip()

    @property
    def machine_code(self) -> str:
        return str(self.raw.get("device", {}).get("machine_code", "")).strip()

    @property
    def device_label(self) -> str:
        return self.device_name or self.device_id or "未命名设备"

    @property
    def bind_status(self) -> str:
        return str(self.raw.get("bind", {}).get("status", "unbound")).strip() or "unbound"

    @property
    def bound_mobile_device_id(self) -> str:
        return str(self.raw.get("bind", {}).get("bound_mobile_device_id", "")).strip()

    @property
    def bound_mobile_device_name(self) -> str:
        return str(self.raw.get("bind", {}).get("bound_mobile_device_name", "")).strip()

    @property
    def bound_at(self) -> str:
        return str(self.raw.get("bind", {}).get("bound_at", "")).strip()

    @property
    def bind_code_ttl_seconds(self) -> int:
        return int(self.raw.get("bind", {}).get("bind_code_ttl_seconds", 600))

    @property
    def pending_bind_code(self) -> str:
        return str(self.raw.get("bind", {}).get("pending_bind_code", "")).strip()

    @property
    def pending_bind_expires_at(self) -> str:
        return str(self.raw.get("bind", {}).get("pending_bind_expires_at", "")).strip()

    @property
    def pending_mobile_device_id(self) -> str:
        return str(self.raw.get("bind", {}).get("pending_mobile_device_id", "")).strip()

    @property
    def pending_mobile_device_name(self) -> str:
        return str(self.raw.get("bind", {}).get("pending_mobile_device_name", "")).strip()

    @property
    def last_bind_code_issued_at(self) -> str:
        return str(self.raw.get("bind", {}).get("last_bind_code_issued_at", "")).strip()

    @property
    def project_root(self) -> Path:
        root = self.raw.get("project", {}).get("root_dir", ".")
        return Path(root).expanduser().resolve()

    @property
    def tasks_dir(self) -> Path:
        rel = self.raw.get("project", {}).get("tasks_dir", "docs/agents/tasks")
        return (self.project_root / rel).resolve()

    @property
    def reports_dir(self) -> Path:
        rel = self.raw.get("project", {}).get("reports_dir", "docs/agents/reports")
        return (self.project_root / rel).resolve()

    @property
    def issues_dir(self) -> Path:
        rel = self.raw.get("project", {}).get("issues_dir", "docs/agents/issues")
        return (self.project_root / rel).resolve()

    @property
    def templates_dir(self) -> Path:
        rel = self.raw.get("patrol", {}).get("templates_dir", "ops/patrol_templates")
        return (self.project_root / rel).resolve()

    @property
    def runtime_dir(self) -> Path:
        rel = self.raw.get("runtime", {}).get("runtime_dir", ".bridgeflow/runtime")
        return (self.project_root / rel).resolve()

    @property
    def status_dir(self) -> Path:
        rel = self.raw.get("runtime", {}).get("status_dir", ".bridgeflow/runtime/status")
        return (self.project_root / rel).resolve()

    @property
    def task_details_dir(self) -> Path:
        rel = self.raw.get("runtime", {}).get("task_details_dir", ".bridgeflow/runtime/task_details")
        return (self.project_root / rel).resolve()

    @property
    def heartbeat_file(self) -> Path:
        return self.status_dir / "heartbeat.json"

    @property
    def device_status_file(self) -> Path:
        return self.status_dir / "device_status.json"

    @property
    def task_index_file(self) -> Path:
        return self.status_dir / "task_index.json"

    @property
    def last_activity_file(self) -> Path:
        return self.status_dir / "last_activity.json"

    @property
    def admin_sender(self) -> str:
        return str(self.raw.get("admin", {}).get("sender", "ADMIN01")).strip()

    @property
    def admin_target(self) -> str:
        return str(self.raw.get("admin", {}).get("target", "PM01")).strip()

    @property
    def default_priority(self) -> str:
        return str(self.raw.get("admin", {}).get("default_priority", "P1")).strip()

    @property
    def patrol_message(self) -> str:
        return str(self.raw.get("patrol", {}).get("message", "巡检")).strip()

    @property
    def patrol_poll_interval(self) -> int:
        return int(self.raw.get("patrol", {}).get("poll_interval", 10))

    @property
    def patrol_check_delay(self) -> int:
        return int(self.raw.get("patrol", {}).get("check_delay", 15))

    @property
    def patrol_max_retry(self) -> int:
        return int(self.raw.get("patrol", {}).get("max_retry", 3))

    @property
    def patrol_confidence(self) -> float:
        return float(self.raw.get("patrol", {}).get("confidence", 0.7))

    @property
    def all_worker_chats(self) -> list[str]:
        return list(self.raw.get("patrol", {}).get("all_worker_chats", []))

    @property
    def role_to_chat(self) -> dict[str, str]:
        return dict(self.raw.get("patrol", {}).get("role_to_chat", {}))

    @property
    def roles(self) -> dict[str, dict]:
        raw_roles = self.raw.get("roles", {})
        return {str(key).strip(): dict(value) for key, value in raw_roles.items()}

    @property
    def fixed_roles(self) -> list[str]:
        raw_roles = self.raw.get("ai_team", {}).get("fixed_roles", DEFAULT_FIXED_ROLES)
        items = [str(item).strip() for item in raw_roles if str(item).strip()]
        return items or DEFAULT_FIXED_ROLES[:]

    @property
    def cursor_only(self) -> bool:
        return self.raw.get("ai_team", {}).get("cursor_only", True) is not False

    @property
    def idle_seconds(self) -> int:
        return int(self.raw.get("runtime", {}).get("idle_seconds", 180))

    @property
    def stale_task_seconds(self) -> int:
        return int(self.raw.get("runtime", {}).get("stale_task_seconds", 900))

    @property
    def sendable_roles(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for role_name in self.fixed_roles:
            meta = self.roles.get(role_name, {})
            if role_name == self.admin_sender:
                continue
            display_names = list(meta.get("display_names", []))
            label = display_names[0] if display_names else role_name
            items.append({"role": role_name, "label": label})
        if not any(item["role"] == self.admin_target for item in items):
            items.insert(0, {"role": self.admin_target, "label": self.admin_target})
        return items

    def validate_device(self) -> None:
        missing = []
        if not self.device_id:
            missing.append("device.device_id")
        if not self.device_name:
            missing.append("device.device_name")
        if not self.owner_role:
            missing.append("device.owner_role")
        if not self.machine_code:
            missing.append("device.machine_code")
        if missing:
            raise ValueError(f"配置缺少设备身份字段: {', '.join(missing)}")

    def validate_roles(self) -> None:
        missing = [role for role in self.fixed_roles if role not in self.roles]
        if missing:
            raise ValueError(f"配置缺少固定角色定义: {', '.join(missing)}")

    def ensure_runtime_dirs(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.issues_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self.task_details_dir.mkdir(parents=True, exist_ok=True)

    def save(self, raw: dict[str, Any] | None = None) -> None:
        self.path.write_text(json.dumps(raw or self.raw, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_bind(self, **kwargs: Any) -> None:
        bind = dict(self.raw.get("bind", {}))
        bind.update(kwargs)
        self.raw["bind"] = bind
        self.save()


def load_config(path: str | Path) -> PatrolConfig:
    cfg_path = Path(path).expanduser().resolve()
    raw = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    return PatrolConfig(raw=raw, path=cfg_path)
