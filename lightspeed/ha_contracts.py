"""Home Assistant discovery payload generators."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List

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
    messages: List[DiscoveryMessage] = []

    light_payload = {
        "name": f"{device['name']} Couleur",
        "unique_id": f"{profile.home_assistant.device_id}_color",
        "command_topic": profile.topics.color,
        "command_template": '{"r": {{ red }}, "g": {{ green }}, "b": {{ blue }}}',
        "supported_color_modes": ["rgb"],
        "optimistic": True,
        "availability": availability,
        "device": device,
    }
    messages.append(_build_message("light", light_payload))

    for kind, topic in (("alert", profile.topics.alert), ("warning", profile.topics.warning)):
        payload = {
            "name": f"{device['name']} {kind}",
            "unique_id": f"{profile.home_assistant.device_id}_{kind}",
            "command_topic": topic,
            "payload_press": "ON",
            "availability": availability,
            "device": device,
        }
        messages.append(_build_message("button", payload))

    auto_payload = {
        "name": f"{device['name']} Auto",
        "unique_id": f"{profile.home_assistant.device_id}_auto",
        "command_topic": profile.topics.auto,
        "payload_press": "ON",
        "availability": availability,
        "device": device,
    }
    messages.append(_build_message("button", auto_payload))

    status_payload = {
        "name": f"{device['name']} Statut",
        "unique_id": f"{profile.home_assistant.device_id}_status",
        "state_topic": profile.topics.status,
        "payload_on": "online",
        "payload_off": "offline",
        "availability": availability,
        "device": device,
    }
    messages.append(_build_message("binary_sensor", status_payload))

    return messages


def _build_message(component: str, payload: dict) -> DiscoveryMessage:
    unique_id = payload["unique_id"]
    topic = f"{DISCOVERY_PREFIX}/{component}/{unique_id}/config"
    return DiscoveryMessage(topic=topic, payload=json.dumps(payload, separators=(",", ":")))
