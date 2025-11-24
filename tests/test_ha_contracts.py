from __future__ import annotations

import json
import textwrap

from lightspeed.config import load_config
from lightspeed.ha_contracts import iter_discovery_messages


def _write_config(tmp_path, content: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_path


def test_iter_discovery_messages_publishes_single_device_payload(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: broker.local
          client_id: alerts
        topics:
          base: foo/bar
        home_assistant:
          device_id: foo
          device_name: Foo Device
          manufacturer: TestCo
          model: RevA
        lighting:
          default_color: "#336699"
          lock_file: lock.bin
        palettes:
          alert:
            frames:
            - color: "#FF0000"
              duration_ms: 100
          warning:
            frames:
            - color: "#FFFF00"
              duration_ms: 100
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )
    profile = load_config(config_path)

    messages = list(iter_discovery_messages(profile))

    assert len(messages) == 1
    message = messages[0]
    assert message.topic == f"homeassistant/device/{profile.home_assistant.device_id}/config"

    payload = json.loads(message.payload)
    assert payload["device"]["name"] == "Foo Device"
    components = payload["components"]
    color = components["color_light"]
    assert color["platform"] == "light"
    assert color["command_topic"] == profile.topics.color
    pilot = components["pilot_switch"]
    assert pilot["platform"] == "switch"
    assert pilot["command_topic"] == profile.topics.auto
    assert pilot["state_topic"] == profile.topics.auto_state
    assert pilot["payload_on"] == "ON"
    assert pilot["payload_off"] == "OFF"
    assert "auto_button" not in components
    status_sensor = components["status_binary_sensor"]
    assert status_sensor["state_topic"] == profile.topics.status
    assert status_sensor["value_template"] == "{{ value_json.state }}"
    assert status_sensor["json_attributes_topic"] == profile.topics.status
