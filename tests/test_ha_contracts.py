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
    assert payload["availability"][0]["topic"] == profile.topics.lwt
    components = payload["components"]
    color = components["color_light"]
    assert color["platform"] == "light"
    assert color["command_topic"] == profile.topics.color
    assert color["state_topic"] == profile.topics.color_state
    assert color["brightness_command_topic"] == profile.topics.brightness
    assert color["brightness_state_topic"] == profile.topics.brightness_state
    power = components["power_switch"]
    assert power["command_topic"] == profile.topics.power
    assert power["state_topic"] == profile.topics.power_state
    assert power["payload_on"] == "ON"
    assert power["payload_off"] == "OFF"
    mode = components["mode_switch"]
    assert mode["command_topic"] == profile.topics.mode
    assert mode["state_topic"] == profile.topics.mode_state
    assert mode["payload_on"] == "pilot"
    assert mode["payload_off"] == "logi"
    alert_button = components["alert_button"]
    assert alert_button["command_topic"] == profile.topics.alert
    assert json.loads(alert_button["payload_press"]) == {"type": "alert"}
    warning_button = components["warning_button"]
    assert warning_button["command_topic"] == profile.topics.alert
    assert json.loads(warning_button["payload_press"]) == {"type": "warning"}
    status_sensor = components["status_binary_sensor"]
    assert status_sensor["state_topic"] == profile.topics.status
    assert status_sensor["value_template"] == "{{ value_json.state }}"
    assert status_sensor["json_attributes_topic"] == profile.topics.status
    availability_sensor = components["availability_sensor"]
    assert availability_sensor["state_topic"] == profile.topics.lwt
    assert availability_sensor["payload_on"] == "online"
    assert availability_sensor["payload_off"] == "offline"
    mode_sensor = components["mode_sensor"]
    assert mode_sensor["state_topic"] == profile.topics.mode_state
    info_button = components["info_button"]
    assert info_button["command_topic"] == profile.topics.alert
    assert json.loads(info_button["payload_press"]) == {"type": "info"}
    availability = payload["availability"][0]
    assert availability["topic"] == profile.topics.lwt
    assert availability["payload_on"] == "online"
    assert availability["payload_off"] == "offline"
