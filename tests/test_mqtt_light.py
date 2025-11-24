from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import paho.mqtt.client as mqtt


class _StubLogiLed:
    def __init__(self) -> None:
        self.led_dll = None

    def logi_led_init(self):  # pragma: no cover - stub keeps SDK optional during tests
        return True

    def logi_led_save_current_lighting(self):  # pragma: no cover - stubbed side effects
        return True

    def logi_led_restore_lighting(self):  # pragma: no cover - stubbed side effects
        return True

    def logi_led_shutdown(self):  # pragma: no cover - stubbed side effects
        return True

    def logi_led_set_lighting(self, *_args, **_kwargs):  # pragma: no cover - stubbed side effects
        return True


sys.modules["logipy"] = SimpleNamespace(logi_led=_StubLogiLed())


def _alert_payload(kind: str = "alert", **overrides: object) -> bytes:
    body: dict[str, object] = {"type": kind}
    body.update(overrides)
    return json.dumps(body, separators=(",", ":")).encode("utf-8")

from lightspeed.config import load_config
from lightspeed.lighting import apply_brightness
from lightspeed.mqtt import MqttLightingService, _extract_brightness, _extract_color_from_dict, _parse_color_command


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

        @staticmethod
        def apply_brightness(color, brightness):
            return tuple(int(channel * (brightness / 255)) for channel in color)

    from lightspeed import mqtt as mqtt_module

    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", _FakeLighting)

    payload = json.dumps({"color": {"r": 100, "g": 50, "b": 25}, "brightness": 128})
    rgb, base, brightness = _parse_color_command(payload, (0, 0, 0))
    assert rgb == (50, 25, 12)
    assert base == (100, 50, 25)
    assert brightness == 128


def test_parse_color_command_with_brightness_only_reuses_previous_color(monkeypatch):
    class _FakeLighting:
        @staticmethod
        def parse_color_string(value: str):
            raise ValueError("unexpected")

        @staticmethod
        def apply_brightness(color, brightness):
            return tuple(int(channel * (brightness / 255)) for channel in color)

    from lightspeed import mqtt as mqtt_module

    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", _FakeLighting)

    payload = json.dumps({"brightness": 64})
    rgb, base, brightness = _parse_color_command(payload, (200, 100, 50))
    expected = tuple(int(channel * (64 / 255)) for channel in (200, 100, 50))
    assert rgb == expected
    assert base == (200, 100, 50)
    assert brightness == 64


def test_apply_brightness_clamps_to_zero():
    assert apply_brightness((200, 100, 50), 0) == (0, 0, 0)


class _FakeController:
    def __init__(self) -> None:
        self.colors: list[tuple[int, int, int]] = []
        self.released = 0
        self.patterns: list[tuple] = []
        self.stop_calls = 0
        self.shutdown_calls = 0

    def start(self) -> None:  # pragma: no cover - no-op
        return None

    def set_static_color(self, rgb):  # pragma: no cover - deterministic list append
        self.colors.append(rgb)

    def start_pattern(self, frames, *_args, **_kwargs):  # pragma: no cover - deterministic capture
        self.patterns.append(frames)

    def release(self):  # pragma: no cover - track release calls
        self.released += 1

    def stop_pattern(self):  # pragma: no cover - track stop invocations
        self.stop_calls += 1

    def shutdown(self):  # pragma: no cover - no-op
        self.shutdown_calls += 1
        return None


class _FakeMqttMessage:
    def __init__(self, topic: str, payload: bytes) -> None:
        self.topic = topic
        self.payload = payload


class _FakeClient:
    def __init__(self, *_, **__):
        self.publish_calls: list[dict[str, object]] = []
        self.subscriptions: list[tuple[str, int]] = []
        self.will: dict[str, object] | None = None

    def username_pw_set(self, *_args, **_kwargs):  # pragma: no cover - unused in tests
        return None

    def will_set(self, topic: str, payload: str, qos: int, retain: bool):
        self.will = {"topic": topic, "payload": payload, "qos": qos, "retain": retain}

    def connect(self, *_args, **_kwargs):  # pragma: no cover - unused
        return 0

    def loop_start(self):  # pragma: no cover - unused
        return None

    def loop_stop(self):  # pragma: no cover - unused
        return None

    def disconnect(self):  # pragma: no cover - unused
        return None

    def subscribe(self, topic: str, qos: int):
        self.subscriptions.append((topic, qos))

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        self.publish_calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})

    def last_publish(self, topic: str) -> dict[str, object]:
        for entry in reversed(self.publish_calls):
            if entry["topic"] == topic:
                return entry
        raise AssertionError(f"Topic {topic} n'a pas été publié")


def _write_config(tmp_path, content: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_path


def _build_profile(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: localhost
          client_id: alerts
        topics:
          base: foo/bar
        home_assistant:
          device_id: foo
          device_name: Foo Device
          manufacturer: TestCo
          model: RevA
        lighting:
          default_color: "#112233"
          lock_file: lock.bin
        palettes: {}
        logitech:
          profile_backup: backup.json
        observability:
                    health_topic: foo/bar/health
                    log_level: INFO
        """,
    )
    return load_config(config_path)


def _make_service(tmp_path, monkeypatch):
    from lightspeed import mqtt as mqtt_module

    monkeypatch.setattr(mqtt_module.mqtt, "Client", _FakeClient)
    profile = _build_profile(tmp_path)
    controller: Any = _FakeController()
    service = MqttLightingService(controller, profile, validated_at=datetime.now(timezone.utc))
    return service


def _client(service: MqttLightingService) -> _FakeClient:
    return cast(_FakeClient, service.client)


def _client_for_callback(client: _FakeClient) -> mqtt.Client:
    return cast(mqtt.Client, client)


def _payload(entry: dict[str, object]) -> str:
    return cast(str, entry["payload"])


def _controller(service: MqttLightingService) -> _FakeController:
    return cast(_FakeController, service.controller)


def _drain_initial_mode_echo(service: MqttLightingService, client: _FakeClient) -> None:
    retained = _FakeMqttMessage(service.profile.topics.mode, b"pilot")
    service.on_message(_client_for_callback(client), None, retained)


def _connect_service(service: MqttLightingService) -> _FakeClient:
    client = _client(service)
    service.on_connect(_client_for_callback(client), None, None, 0)
    _drain_initial_mode_echo(service, client)
    return client


class _FakeTimer:
    def __init__(self, interval: int, func, args: tuple, kwargs: dict) -> None:
        self.interval = interval
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cancelled = False

    def start(self) -> None:  # pragma: no cover - timer manually triggered in tests
        return None

    def cancel(self) -> None:  # pragma: no cover - deterministic flag
        self.cancelled = True

    def trigger(self) -> None:
        if not self.cancelled:
            self.func(*self.args, **self.kwargs)
            self.cancelled = True


def _install_fake_timer(monkeypatch, timers):
    from lightspeed import mqtt as mqtt_module

    def _factory(interval, func, args=None, kwargs=None):
        timer = _FakeTimer(interval, func, tuple(args or ()), dict(kwargs or {}))
        timers.append(timer)
        return timer

    monkeypatch.setattr(mqtt_module.threading, "Timer", _factory)


class _OverrideLighting:
    def __init__(self) -> None:
        self.reapplied: list[tuple[tuple[int, int, int], int]] = []
        self.restored = 0

    def alert_frames(self, _profile):  # pragma: no cover - deterministic tuple
        return (("alert",),)

    def warning_frames(self, _profile):  # pragma: no cover - deterministic tuple
        return (("warning",),)

    def reapply_cached_color(self, controller: _FakeController, base_color, brightness):
        self.reapplied.append((base_color, brightness))
        controller.set_static_color(apply_brightness(base_color, brightness))

    def restore_logitech_control(self, controller: _FakeController):
        self.restored += 1
        controller.release()


def test_bootstrap_pilot_switch_updates_initial_state(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    service.bootstrap_pilot_switch(False)

    assert service.control.pilot_switch is False
    assert service.control.light_on is True


def test_pilot_switch_state_republished_on_connect(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)

    mode_command = client.last_publish(service.profile.topics.mode)
    assert mode_command["payload"] == "pilot"
    assert mode_command["retain"] is True

    mode_state = client.last_publish(service.profile.topics.mode_state)
    assert mode_state["payload"] == "pilot"
    assert mode_state["retain"] is True


def test_pilot_switch_off_updates_control_and_status(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    message = _FakeMqttMessage(service.profile.topics.mode, b"logi")
    service.on_message(_client_for_callback(client), None, message)

    assert controller.released == 1
    assert controller.shutdown_calls == 1
    assert service.control.pilot_switch is False
    mode_state = client.last_publish(service.profile.topics.mode_state)
    assert mode_state["payload"] == "logi"
    assert client.last_publish(service.profile.topics.mode)["payload"] == "logi"
    status_payload = client.last_publish(service.profile.topics.status)
    assert json.loads(_payload(status_payload))["mode"] == "logi"


def test_pilot_switch_on_replays_cached_color(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    # Simulate cached color and pilot OFF state
    service.control = service.control.record_color_command(base_color=(10, 20, 30), brightness=200)
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.mode, b"logi"))

    controller.colors.clear()
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.mode, b"pilot"))

    assert service.control.pilot_switch is True
    assert service.control.light_on is True
    assert client.last_publish(service.profile.topics.mode_state)["payload"] == "pilot"
    assert client.last_publish(service.profile.topics.mode)["payload"] == "pilot"
    color_state = json.loads(_payload(client.last_publish(service.profile.topics.color_state)))
    assert color_state["color"] == {"r": 10, "g": 20, "b": 30}
    assert color_state["brightness"] == 200
    assert color_state["state"] == "ON"


def test_light_off_command_releases_control(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    payload = json.dumps({"state": "OFF"})
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.color, payload.encode("utf-8")))

    assert controller.released == 1
    assert service.control.light_on is False
    status_payload = json.loads(_payload(client.last_publish(service.profile.topics.status)))
    assert status_payload["mode"] == "pilot"


def test_light_on_without_color_replays_cached_values(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    color_payload = json.dumps(
        {
            "state": "ON",
            "color": {"r": 100, "g": 50, "b": 25},
            "brightness": 128,
        }
    )
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.color, color_payload.encode("utf-8")))
    service.on_message(
        _client_for_callback(client),
        None,
        _FakeMqttMessage(service.profile.topics.color, json.dumps({"state": "OFF"}).encode("utf-8")),
    )

    controller.colors.clear()
    service.on_message(
        _client_for_callback(client),
        None,
        _FakeMqttMessage(service.profile.topics.color, json.dumps({"state": "ON"}).encode("utf-8")),
    )

    assert controller.colors[-1] == (50, 25, 12)
    assert service.control.light_on is True


def test_color_commands_ignored_when_pilot_off(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.mode, b"logi"))
    controller.colors.clear()

    color_payload = json.dumps(
        {
            "state": "ON",
            "color": {"r": 0, "g": 255, "b": 0},
        }
    )
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.color, color_payload.encode("utf-8")))

    assert controller.colors == []


def test_color_commands_ignored_when_light_off(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)

    service.on_message(
        _client_for_callback(client),
        None,
        _FakeMqttMessage(service.profile.topics.color, json.dumps({"state": "OFF"}).encode("utf-8")),
    )
    controller.colors.clear()

    color_payload = json.dumps({"color": {"r": 255, "g": 0, "b": 0}})
    service.on_message(_client_for_callback(client), None, _FakeMqttMessage(service.profile.topics.color, color_payload.encode("utf-8")))

    assert controller.colors == []


def _setup_override_env(monkeypatch, tmp_path):
    from lightspeed import mqtt as mqtt_module

    override_lighting = _OverrideLighting()
    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", override_lighting)
    timers: list[_FakeTimer] = []
    _install_fake_timer(monkeypatch, timers)
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)
    controller = _controller(service)
    return service, controller, override_lighting, timers


def test_client_sets_last_will(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _client(service)

    assert client.will == {
        "topic": service.profile.topics.lwt,
        "payload": "offline",
        "qos": 1,
        "retain": True,
    }


def test_availability_online_published_on_connect(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)

    availability = client.last_publish(service.profile.topics.lwt)
    assert availability["payload"] == "online"
    assert availability["retain"] is True


def test_offline_status_updates_availability(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    client = _connect_service(service)

    service._publish_status(state="offline", reason="test")

    availability = client.last_publish(service.profile.topics.lwt)
    assert availability["payload"] == "offline"
    assert availability["retain"] is True


def test_alert_override_runs_until_timer_and_restores_color(monkeypatch, tmp_path):
    service, controller, override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, _alert_payload("alert"))
    )

    assert controller.patterns[-1] == (("alert",),)
    assert service.control.state.value == "override_alert"
    assert len(timers) == 1

    timers[0].trigger()

    assert service.control.override is None
    assert controller.stop_calls == 1
    assert override_lighting.reapplied[-1] == (service.control.last_command_color, service.control.last_brightness)


def test_warning_override_replaces_alert(monkeypatch, tmp_path):
    service, controller, override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, _alert_payload("alert"))
    )
    first_timer = timers[0]
    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, _alert_payload("warning"))
    )

    assert first_timer.cancelled is True
    assert controller.patterns[-1] == (("warning",),)
    assert service.control.state.value == "override_warning"
    assert len(timers) == 2

    timers[1].trigger()

    assert override_lighting.reapplied
    assert service.control.override is None


def test_override_cancels_when_pilot_switch_changes(monkeypatch, tmp_path):
    service, controller, override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, _alert_payload("alert"))
    )
    message = _FakeMqttMessage(service.profile.topics.mode, b"logi")
    service.on_message(_client_for_callback(_client(service)), None, message)

    assert timers[0].cancelled is True
    assert service.control.override is None
    assert service.control.state.value == "logi"
    assert controller.stop_calls == 1
    assert controller.released >= 1
    assert override_lighting.reapplied == []


def test_info_payload_maps_to_alert(monkeypatch, tmp_path):
    service, controller, override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, _alert_payload("info"))
    )

    assert controller.patterns[-1] == (("alert",),)
    assert timers[-1].interval == service.profile.effects.override_duration_seconds


def test_alert_payload_requires_json(monkeypatch, tmp_path):
    service, controller, _override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    service.on_message(
        _client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, b"alert")
    )

    assert controller.patterns == []
    assert timers == []


def test_alert_payload_rejects_out_of_bounds_duration(monkeypatch, tmp_path):
    service, controller, _override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    payload = _alert_payload("alert", duration=400)
    service.on_message(_client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, payload))

    assert controller.patterns == []
    assert timers == []


def test_alert_payload_applies_custom_duration(monkeypatch, tmp_path):
    service, controller, _override_lighting, timers = _setup_override_env(monkeypatch, tmp_path)

    payload = _alert_payload("warning", duration=15)
    service.on_message(_client_for_callback(_client(service)), None, _FakeMqttMessage(service.profile.topics.alert, payload))

    assert controller.patterns[-1] == (("warning",),)
    assert timers[-1].interval == 15
