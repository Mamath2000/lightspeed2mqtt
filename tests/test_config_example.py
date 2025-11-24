from __future__ import annotations

from pathlib import Path

from lightspeed.config import load_config


def test_config_example_loads_successfully():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config.example.yaml"
    profile = load_config(config_path, env={"MQTT_PASSWORD": "example"})

    assert profile.mqtt.host == "localhost"
    assert profile.mqtt.password == "example"
    assert profile.topics.power == f"{profile.topics.base}/power"
    assert profile.topics.power_state == f"{profile.topics.power}/state"
    assert profile.topics.mode == f"{profile.topics.base}/mode"
    assert profile.topics.mode_state == f"{profile.topics.mode}/state"
    assert profile.topics.color == f"{profile.topics.base}/color"
    assert profile.topics.color_state == f"{profile.topics.color}/state"
    assert profile.topics.brightness == f"{profile.topics.base}/brightness"
    assert profile.topics.brightness_state == f"{profile.topics.brightness}/state"
    assert profile.topics.alert == f"{profile.topics.base}/alert"
    assert profile.topics.lwt == f"{profile.topics.base}/lwt"
    assert profile.effects.override_duration_seconds == 10
    assert profile.observability.health_topic == profile.topics.status
