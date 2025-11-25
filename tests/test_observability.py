from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from lightspeed.control_mode import ControlMode
from lightspeed.observability import build_status_payload, publish_availability, publish_status


def test_build_status_payload_includes_mode_metadata():
    control = ControlMode.bootstrap(default_color=(10, 20, 30))
    override = control.start_override(kind="warning", duration_seconds=5)
    payload = json.loads(build_status_payload(override, state="online", reason="event"))

    assert payload["state"] == "online"
    assert payload["mode"] == "override_warning"
    assert payload["pilot_switch"] == "ON"
    assert payload["light_state"] == "ON"
    assert payload["override"]["kind"] == "warning"
    assert payload["reason"] == "event"


def test_build_status_payload_offline_state():
    control = ControlMode.bootstrap(default_color=(0, 0, 0))
    control = control.set_light_state(on=False)
    payload = json.loads(build_status_payload(control, state="offline"))

    assert payload["state"] == "offline"
    assert payload["mode"] == "pilot"
    assert payload["light_state"] == "OFF"


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def publish(self, topic: str, payload: str, qos: int, retain: bool):  # pragma: no cover - exercised via tests
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})


def _fake_profile(*, status: str = "base/status", health: str | None = None, lwt: str = "base/lwt"):
    topics = SimpleNamespace(status=status, lwt=lwt)
    observability = SimpleNamespace()
    return SimpleNamespace(
        topics=topics,
        observability=observability,
        source_path=Path("config.yaml"),
        schema_revision=lambda: "test",
    )


def test_publish_status_targets_status_topic():
    client = _FakeClient()
    profile = _fake_profile()
    control = ControlMode.bootstrap(default_color=(1, 2, 3))

    publish_status(client, profile, control, state="online", reason="boot")

    call = client.calls[-1]
    assert call["topic"] == profile.topics.status
    assert call["retain"] is True
    assert call["qos"] == 1
    assert json.loads(call["payload"])["reason"] == "boot"

    call = client.calls[-1]
    assert call["topic"] == profile.topics.status
    assert call["retain"] is True
    assert call["qos"] == 1


def test_publish_availability_targets_lwt_topic():
    client = _FakeClient()
    profile = _fake_profile()

    publish_availability(client, profile, "online")

    call = client.calls[-1]
    assert call["topic"] == profile.topics.lwt
    assert call["payload"] == "online"
    assert call["retain"] is True
