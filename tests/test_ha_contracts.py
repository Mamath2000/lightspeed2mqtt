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
    
    # Vérifier la structure device
    assert "device" in payload
    assert payload["device"]["name"] == "Foo Device"
    assert "components" in payload
    
    # Vérifier le composant light
    light = payload["components"]["light"]
    assert light["platform"] == "light"
    assert light["unique_id"] == "foo_light"
    assert light["state_topic"] == "foo/bar/status"
    assert light["command_topic"] == "foo/bar/switch"
    assert light["rgb_command_topic"] == "foo/bar/rgb/set"
    assert light["brightness_command_topic"] == "foo/bar/brightness/set"
    # Les effets ne sont plus sur le light
    assert "effect" not in light
    assert "effect_command_topic" not in light
    
    # Vérifier le composant status_sensor
    status = payload["components"]["status_sensor"]
    assert status["platform"] == "binary_sensor"
    assert status["unique_id"] == "foo_status"
    
    # Vérifier le composant mode_switch
    mode = payload["components"]["mode_switch"]
    assert mode["platform"] == "switch"
    assert mode["unique_id"] == "foo_mode"
    assert mode["command_topic"] == "foo/bar/mode/set"
    
    # Vérifier les 3 boutons d'alerte
    alert_btn = payload["components"]["alert_button"]
    assert alert_btn["platform"] == "button"
    assert alert_btn["command_topic"] == "foo/bar/alert"
    
    warn_btn = payload["components"]["warn_button"]
    assert warn_btn["platform"] == "button"
    assert warn_btn["command_topic"] == "foo/bar/warn"
    
    info_btn = payload["components"]["info_button"]
    assert info_btn["platform"] == "button"
    assert info_btn["command_topic"] == "foo/bar/info"
