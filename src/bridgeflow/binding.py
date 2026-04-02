from __future__ import annotations

from datetime import datetime, timedelta
import secrets
import string

from bridgeflow.config import PatrolConfig


BIND_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now() -> datetime:
    return datetime.now()


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _new_code(length: int = 6) -> str:
    return "".join(secrets.choice(BIND_ALPHABET) for _ in range(length))


def has_active_bind_code(config: PatrolConfig) -> bool:
    if not config.pending_bind_code or not config.pending_bind_expires_at:
        return False
    expires_at = _parse(config.pending_bind_expires_at)
    return expires_at is not None and expires_at >= _now()


def public_bind_state(config: PatrolConfig) -> dict:
    return {
        "status": config.bind_status,
        "machine_code": config.machine_code,
        "bound_mobile_device_id": config.bound_mobile_device_id,
        "bound_mobile_device_name": config.bound_mobile_device_name,
        "bound_at": config.bound_at,
        "has_pending_code": has_active_bind_code(config),
        "pending_bind_expires_at": config.pending_bind_expires_at if has_active_bind_code(config) else "",
        "pending_mobile_device_id": config.pending_mobile_device_id,
        "pending_mobile_device_name": config.pending_mobile_device_name,
        "bind_code_ttl_seconds": config.bind_code_ttl_seconds,
    }


def private_bind_state(config: PatrolConfig) -> dict:
    data = public_bind_state(config)
    data["pending_bind_code"] = config.pending_bind_code if has_active_bind_code(config) else ""
    data["last_bind_code_issued_at"] = config.last_bind_code_issued_at
    return data


def issue_bind_code(
    config: PatrolConfig,
    *,
    mobile_device_id: str = "",
    mobile_device_name: str = "",
) -> dict:
    now = _now()
    code = _new_code()
    expires_at = now + timedelta(seconds=config.bind_code_ttl_seconds)
    config.update_bind(
        status="pending",
        pending_bind_code=code,
        pending_bind_expires_at=_fmt(expires_at),
        pending_mobile_device_id=mobile_device_id.strip(),
        pending_mobile_device_name=mobile_device_name.strip(),
        last_bind_code_issued_at=_fmt(now),
    )
    return private_bind_state(config)


def approve_bind(
    config: PatrolConfig,
    *,
    bind_code: str,
    mobile_device_id: str,
    mobile_device_name: str,
) -> dict:
    bind_code = bind_code.strip().upper()
    if not bind_code:
        raise ValueError("绑定码不能为空")
    if not mobile_device_id.strip():
        raise ValueError("mobile_device_id 不能为空")
    if not has_active_bind_code(config):
        raise ValueError("当前没有可用的绑定码")
    if bind_code != config.pending_bind_code.strip().upper():
        raise ValueError("绑定码不正确")

    now = _now()
    config.update_bind(
        status="bound",
        bound_mobile_device_id=mobile_device_id.strip(),
        bound_mobile_device_name=mobile_device_name.strip(),
        bound_at=_fmt(now),
        pending_bind_code="",
        pending_bind_expires_at="",
        pending_mobile_device_id="",
        pending_mobile_device_name="",
    )
    return public_bind_state(config)


def clear_binding(config: PatrolConfig) -> dict:
    config.update_bind(
        status="unbound",
        bound_mobile_device_id="",
        bound_mobile_device_name="",
        bound_at="",
        pending_bind_code="",
        pending_bind_expires_at="",
        pending_mobile_device_id="",
        pending_mobile_device_name="",
    )
    return public_bind_state(config)
