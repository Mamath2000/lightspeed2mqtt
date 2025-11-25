from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lightspeed.control_mode import ControlMode, Mode, parse_mode_payload


def test_bootstrap_defaults_to_pilot():
    state = ControlMode.bootstrap(default_color=(0, 128, 255))

    assert state.state is Mode.PILOT
    assert state.last_command_color == (0, 128, 255)
    assert state.last_brightness == 255
    assert state.light_on is True
    assert state.pilot_switch is True


def test_record_color_updates_cache():
    state = ControlMode.bootstrap(default_color=(10, 20, 30))
    updated = state.record_color_command(base_color=(50, 60, 70), brightness=120)

    assert updated.last_command_color == (50, 60, 70)
    assert updated.last_brightness == 120
    assert updated.state is Mode.PILOT
    assert updated.updated_at >= state.updated_at


def test_set_light_state_toggles_off_then_on():
    state = ControlMode.bootstrap(default_color=(0, 0, 0))
    off_state = state.set_light_state(on=False)

    assert off_state.state is Mode.PILOT
    assert off_state.light_on is False

    on_state = off_state.set_light_state(on=True)
    assert on_state.state is Mode.PILOT
    assert on_state.light_on is True


def test_start_override_then_clear():
    state = ControlMode.bootstrap(default_color=(1, 2, 3))
    now = datetime.now(timezone.utc)
    override_state = state.start_override(kind="alert", duration_seconds=5, timestamp=now)

    assert override_state.state is Mode.OVERRIDE_ALERT
    assert override_state.override is not None
    assert override_state.override.started_at == now

    cleared = override_state.clear_override()
    assert cleared.state is Mode.PILOT
    assert cleared.override is None


def test_invalid_override_kind_raises():
    state = ControlMode.bootstrap(default_color=(1, 2, 3))
    with pytest.raises(ValueError):
        state.start_override(kind="foo", duration_seconds=5)


def test_set_mode_updates_pilot_switch():
    state = ControlMode.bootstrap(default_color=(1, 1, 1))
    logi_state = state.set_mode(Mode.LOGI)
    assert logi_state.pilot_switch is False
    assert logi_state.state is Mode.LOGI

    pilot_state = logi_state.set_mode(Mode.PILOT)
    assert pilot_state.pilot_switch is True
    assert pilot_state.state is Mode.PILOT


def test_parse_mode_payload_accepts_valid_values():
    assert parse_mode_payload("pilot") is Mode.PILOT
    assert parse_mode_payload(" LOGI ") is Mode.LOGI
    assert parse_mode_payload("invalid") is None
    assert parse_mode_payload("") is None
