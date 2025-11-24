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
    assert message.topic == f"homeassistant/light/{profile.home_assistant.device_id}/config"

    payload = json.loads(message.payload)
    assert payload["name"] == "Lightspeed"
    assert payload["optimistic"] is False
    assert payload["state_topic"] == "foo/bar/status"
    assert payload["state_value_template"] == "{{ value_json.state }}"
    assert payload["command_topic"] == "foo/bar/switch"
    assert payload["payload_on"] == "on"
    assert payload["payload_off"] == "off"
    assert payload["rgb_command_topic"] == "foo/bar/rgb/set"
    assert payload["rgb_value_template"] == "{{ value_json.rgb | join(',') }}"
    assert payload["brightness_command_topic"] == "foo/bar/brightness/set"
    assert payload["brightness_value_template"] == "{{ value_json.brightness }}"
    assert payload["effect"] is True
    assert payload["effect_command_topic"] == "foo/bar/effect/set"
    assert payload["effect_list"] == ["None", "Alert", "Warn", "Info"]
    assert payload["effect_state_topic"] == "foo/bar/status"
    assert payload["effect_value_template"] == "{{ value_json.effect }}"
    assert payload["unique_id"] == "foo"
    assert payload["object_id"] == "foo"
    assert payload["device"]["name"] == "Foo Device"
