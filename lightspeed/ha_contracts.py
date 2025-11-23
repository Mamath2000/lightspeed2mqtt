"""Home Assistant discovery payload generators."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from lightspeed.config import ConfigProfile

DISCOVERY_PREFIX = "homeassistant"


@dataclass(frozen=True)
class DiscoveryMessage:
    topic: str
    payload: str
    retain: bool = True


def _device_descriptor(profile: ConfigProfile) -> dict:
    device = profile.home_assistant
    return {
        "identifiers": [f"lightspeed2mqtt:{device.device_id}"],
        "name": device.device_name,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "sw_version": profile.schema_revision(),
    }


def iter_discovery_messages(profile: ConfigProfile) -> Iterable[DiscoveryMessage]:
    device = _device_descriptor(profile)
    availability = [{"topic": profile.topics.status}]
    components = {
        "color_light": {
            "platform": "light",
            "unique_id": f"{profile.home_assistant.device_id}_color",
            "object_id": f"{profile.home_assistant.device_id}_color",
            "name": f"{device['name']} Couleur",
            "schema": "json",
            "command_topic": profile.topics.color,
            "supported_color_modes": ["rgb"],
            "optimistic": True,
            "availability": availability,
        },
        "alert_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_alert",
            "object_id": f"{profile.home_assistant.device_id}_alert",
            "name": f"{device['name']} Alert",
            "command_topic": profile.topics.alert,
            "payload_press": "ON",
            "availability": availability,
        },
        "warning_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_warning",
            "object_id": f"{profile.home_assistant.device_id}_warning",
            "name": f"{device['name']} Warning",
            "command_topic": profile.topics.warning,
            "payload_press": "ON",
            "availability": availability,
        },
        "auto_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_auto",
            "object_id": f"{profile.home_assistant.device_id}_auto",
            "name": f"{device['name']} Auto",
            "command_topic": profile.topics.auto,
            "payload_press": "ON",
            "availability": availability,
        },
        "status_binary_sensor": {
            "platform": "binary_sensor",
            "unique_id": f"{profile.home_assistant.device_id}_status",
            "object_id": f"{profile.home_assistant.device_id}_status",
            "name": f"{device['name']} Statut",
            "state_topic": profile.topics.status,
            "payload_on": "online",
            "payload_off": "offline",
            "availability": availability,
        },
    }

    payload = {
        "device": device,
        "origin": {"name": device["name"]},
        "components": components,
    }
    topic = f"{DISCOVERY_PREFIX}/device/{profile.home_assistant.device_id}/config"
    return [DiscoveryMessage(topic=topic, payload=json.dumps(payload, separators=(",", ":")))]
