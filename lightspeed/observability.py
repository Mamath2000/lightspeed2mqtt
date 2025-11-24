"""Logging helpers and health payload builders."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from lightspeed.config import ConfigProfile

if TYPE_CHECKING:  # pragma: no cover - typing only
    from lightspeed.control_mode import ControlMode

_LOG_CONFIGURED = False


def configure_logging(level: str) -> None:
    global _LOG_CONFIGURED
    if not _LOG_CONFIGURED:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        logging.getLogger("paho.mqtt.client").setLevel(logging.WARNING)
        _LOG_CONFIGURED = True
    else:
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))


def build_health_payload(
    profile: ConfigProfile,
    *,
    status: str,
    validated_at: datetime,
    validation_status: str,
    last_error: Optional[str] = None,
) -> str:
    data = {
        "status": status,
        "config_path": str(profile.source_path),
        "schema_revision": profile.schema_revision(),
        "validated_at": validated_at.astimezone(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation_status,
    }
    if last_error:
        data["last_error"] = last_error
    return json.dumps(data, separators=(",", ":"))


def build_status_payload(
    control: "ControlMode",
    *,
    state: str,
    reason: Optional[str] = None,
) -> str:
    payload = {
        "state": state,
        "mode": control.state.value,
        "pilot_switch": "ON" if control.pilot_switch else "OFF",
        "light_state": "ON" if control.light_on else "OFF",
        "updated_at": control.updated_at.astimezone(timezone.utc).isoformat(),
        "last_color": control.last_command_color,
        "last_brightness": control.last_brightness,
    }
    if control.override:
        payload["override"] = control.override.to_payload()
    if reason:
        payload["reason"] = reason
    return json.dumps(payload, separators=(",", ":"))


def override_reason(kind: str, action: str) -> str:
    subject = (kind or "override").strip() or "override"
    return f"{subject}_{action}"


def override_log_context(
    kind: str,
    *,
    action: str,
    duration: Optional[int] = None,
    invalid_value: Any | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "override_kind": kind,
        "override_action": action,
    }
    if duration is not None:
        context["override_duration"] = duration
    if invalid_value is not None:
        context["override_invalid_value"] = invalid_value
    return context
