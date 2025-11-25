from __future__ import annotations

from pathlib import Path

from lightspeed.config import load_config


def test_config_example_loads_successfully():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config.example.yaml"
    profile = load_config(config_path, env={"MQTT_PASSWORD": "example"})

    assert profile.mqtt.host == "localhost"
    assert profile.mqtt.password == "example"
    assert profile.topics.base == "lightspeed/alerts"
    assert profile.topics.state_topic == f"{profile.topics.base}/status"
    assert profile.topics.command_topic == f"{profile.topics.base}/switch"
    assert profile.topics.rgb_command_topic == f"{profile.topics.base}/rgb/set"
    assert profile.topics.brightness_command_topic == f"{profile.topics.base}/brightness/set"
    assert profile.topics.mode_command_topic == f"{profile.topics.base}/mode/set"
    assert profile.topics.alert_command_topic == f"{profile.topics.base}/alert"
    assert profile.topics.warn_command_topic == f"{profile.topics.base}/warn"
    assert profile.topics.info_command_topic == f"{profile.topics.base}/info"
    assert profile.topics.lwt == f"{profile.topics.base}/lwt"
    assert profile.effects.override_duration_seconds == 10
