from __future__ import annotations

import json

from lightspeed.control_mode import ControlMode
from lightspeed.observability import build_status_payload


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
    assert payload["mode"] == "off"
    assert payload["light_state"] == "OFF"
