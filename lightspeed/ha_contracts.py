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
    ha = profile.home_assistant
    topics = profile.topics
    
    availability = [
        {
            "topic": topics.lwt,
            "payload_available": "online",
            "payload_not_available": "offline",
        }
    ]
    
    components = {
        "light": {
            "platform": "light",
            "unique_id": f"{ha.device_id}_light",
            "object_id": f"{ha.device_id}_light",
            "name": f"{device['name']} Éclairage",
            "optimistic": False,
            "state_topic": topics.state_topic,
            "state_value_template": "{{ value_json.state }}",
            "command_topic": topics.command_topic,
            "payload_on": "on",
            "payload_off": "off",
            "rgb_command_topic": topics.rgb_command_topic,
            "rgb_value_template": "{{ value_json.rgb | join(',') }}",
            "brightness_command_topic": topics.brightness_command_topic,
            "brightness_value_template": "{{ value_json.brightness }}",
        },
        "status_sensor": {
            "platform": "binary_sensor",
            "unique_id": f"{ha.device_id}_status",
            "object_id": f"{ha.device_id}_status",
            "name": f"{device['name']} Statut",
            "state_topic": topics.state_topic,
            "payload_on": "on",
            "payload_off": "off",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": topics.state_topic,
        },
        "mode_switch": {
            "platform": "switch",
            "unique_id": f"{ha.device_id}_mode",
            "object_id": f"{ha.device_id}_mode",
            "name": f"{device['name']} Mode",
            "command_topic": topics.mode_command_topic,
            "state_topic": topics.state_topic,
            "value_template": "{{ value_json.mode }}",
            "payload_on": "pilot",
            "payload_off": "auto",
        },
        "alert_button": {
            "platform": "button",
            "unique_id": f"{ha.device_id}_alert",
            "object_id": f"{ha.device_id}_alert",
            "name": f"{device['name']} Alert",
            "command_topic": topics.alert_command_topic,
            "payload_press": "press",
            "icon": "mdi:alert",
        },
        "warn_button": {
            "platform": "button",
            "unique_id": f"{ha.device_id}_warn",
            "object_id": f"{ha.device_id}_warn",
            "name": f"{device['name']} Warn",
            "command_topic": topics.warn_command_topic,
            "payload_press": "press",
            "icon": "mdi:alert-circle",
        },
        "info_button": {
            "platform": "button",
            "unique_id": f"{ha.device_id}_info",
            "object_id": f"{ha.device_id}_info",
            "name": f"{device['name']} Info",
            "command_topic": topics.info_command_topic,
            "payload_press": "press",
            "icon": "mdi:information",
        },
    }
    
    payload = {
        "device": device,
        "origin": {"name": device["name"]},
        "components": components,
        "availability": availability,
    }
    
    topic = f"{DISCOVERY_PREFIX}/device/{ha.device_id}/config"
    
    return [DiscoveryMessage(topic=topic, payload=json.dumps(payload, separators=(",", ":")))]
