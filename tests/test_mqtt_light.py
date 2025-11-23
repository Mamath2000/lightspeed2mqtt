from __future__ import annotations

import json

from lightspeed.mqtt import (
    _apply_brightness,
    _extract_brightness,
    _extract_color_from_dict,
    _parse_color_command,
)


def test_extract_color_from_json_dict():
    data = {"color": {"r": 120, "g": 20, "b": 10}}
    rgb = _extract_color_from_dict(data)
    assert rgb == (120, 20, 10)


def test_extract_brightness_pct():
    data = {"brightness_pct": 50}
    value = _extract_brightness(data)
    assert value == 128


def test_parse_color_command_applies_brightness(monkeypatch):
    # Ensure _lighting_module().parse_color_string is available without importing logipy
    class _FakeLighting:
        @staticmethod
        def parse_color_string(value: str):
            return (10, 20, 30)

    from lightspeed import mqtt as mqtt_module

    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", _FakeLighting)

    payload = json.dumps({"color": {"r": 100, "g": 50, "b": 25}, "brightness": 128})
    rgb, base = _parse_color_command(payload, (0, 0, 0))
    assert rgb == (50, 25, 12)
    assert base == (100, 50, 25)


def test_parse_color_command_with_brightness_only_reuses_previous_color(monkeypatch):
    class _FakeLighting:
        @staticmethod
        def parse_color_string(value: str):
            raise ValueError("unexpected")

    from lightspeed import mqtt as mqtt_module

    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", _FakeLighting)

    payload = json.dumps({"brightness": 64})
    rgb, base = _parse_color_command(payload, (200, 100, 50))
    assert rgb == _apply_brightness((200, 100, 50), 64)
    assert base == (200, 100, 50)


def test_apply_brightness_clamps_to_zero():
    assert _apply_brightness((200, 100, 50), 0) == (0, 0, 0)
