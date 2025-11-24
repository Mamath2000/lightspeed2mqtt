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
    availability = [
        {
            "topic": profile.topics.lwt,
            "payload_on": "online",
            "payload_off": "offline",
        }
    ]
    alert_payload = json.dumps({"type": "alert"}, separators=(",", ":"))
    warning_payload = json.dumps({"type": "warning"}, separators=(",", ":"))
    info_payload = json.dumps({"type": "info"}, separators=(",", ":"))
    components = {
        "color_light": {
            "platform": "light",
            "unique_id": f"{profile.home_assistant.device_id}_color",
            "object_id": f"{profile.home_assistant.device_id}_color",
            "name": f"{device['name']} Couleur",
            "schema": "json",
            "command_topic": profile.topics.color,
            "state_topic": profile.topics.color_state,
            "brightness_command_topic": profile.topics.brightness,
            "brightness_state_topic": profile.topics.brightness_state,
            "supported_color_modes": ["rgb"],
            "optimistic": True,
        },
        "alert_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_alert",
            "object_id": f"{profile.home_assistant.device_id}_alert",
            "name": f"{device['name']} Alert",
            "command_topic": profile.topics.alert,
            "payload_press": alert_payload,
        },
        "warning_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_warning",
            "object_id": f"{profile.home_assistant.device_id}_warning",
            "name": f"{device['name']} Warning",
            "command_topic": profile.topics.alert,
            "payload_press": warning_payload,
        },
        "info_button": {
            "platform": "button",
            "unique_id": f"{profile.home_assistant.device_id}_info",
            "object_id": f"{profile.home_assistant.device_id}_info",
            "name": f"{device['name']} Info",
            "command_topic": profile.topics.alert,
            "payload_press": info_payload,
        },
        "power_switch": {
            "platform": "switch",
            "unique_id": f"{profile.home_assistant.device_id}_power",
            "object_id": f"{profile.home_assistant.device_id}_power",
            "name": f"{device['name']} Power",
            "command_topic": profile.topics.power,
            "state_topic": profile.topics.power_state,
            "payload_on": "ON",
            "payload_off": "OFF",
        },
        "mode_switch": {
            "platform": "switch",
            "unique_id": f"{profile.home_assistant.device_id}_mode",
            "object_id": f"{profile.home_assistant.device_id}_mode",
            "name": f"{device['name']} Mode",
            "command_topic": profile.topics.mode,
            "state_topic": profile.topics.mode_state,
            "payload_on": "pilot",
            "payload_off": "logi",
        },
        "status_binary_sensor": {
            "platform": "binary_sensor",
            "unique_id": f"{profile.home_assistant.device_id}_status",
            "object_id": f"{profile.home_assistant.device_id}_status",
            "name": f"{device['name']} Statut",
            "state_topic": profile.topics.status,
            "payload_on": "online",
            "payload_off": "offline",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": profile.topics.status,
        },
        "availability_sensor": {
            "platform": "binary_sensor",
            "unique_id": f"{profile.home_assistant.device_id}_availability",
            "object_id": f"{profile.home_assistant.device_id}_availability",
            "name": f"{device['name']} Disponibilité",
            "state_topic": profile.topics.lwt,
            "payload_on": "online",
            "payload_off": "offline",
        },
        "mode_sensor": {
            "platform": "sensor",
            "unique_id": f"{profile.home_assistant.device_id}_mode_state",
            "object_id": f"{profile.home_assistant.device_id}_mode_state",
            "name": f"{device['name']} Mode actuel",
            "state_topic": profile.topics.mode_state,
        },
    }

    payload = {
        "device": device,
        "origin": {"name": device["name"]},
        "components": components,
        "availability": availability,
    }
    topic = f"{DISCOVERY_PREFIX}/device/{profile.home_assistant.device_id}/config"
    return [DiscoveryMessage(topic=topic, payload=json.dumps(payload, separators=(",", ":")))]
