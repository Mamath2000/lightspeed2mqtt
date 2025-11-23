from __future__ import annotations

from pathlib import Path

from lightspeed.config import load_config


def test_config_example_loads_successfully():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config.example.yaml"
    profile = load_config(config_path, env={"MQTT_PASSWORD": "example"})

    assert profile.mqtt.host == "localhost"
    assert profile.mqtt.password == "example"
    assert profile.topics.color == f"{profile.topics.base}/color"
    assert profile.observability.health_topic == "lightspeed/alerts/health"
