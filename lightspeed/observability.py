"""Logging helpers and health payload builders."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from lightspeed.config import ConfigProfile

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
