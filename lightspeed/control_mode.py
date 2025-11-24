"""Control mode and override helpers for MQTT lighting orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

RGB = Tuple[int, int, int]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Mode(str, Enum):
    PILOT = "pilot"
    OFF = "off"
    OVERRIDE_ALERT = "override_alert"
    OVERRIDE_WARNING = "override_warning"


@dataclass(frozen=True)
class OverrideAction:
    kind: str
    duration_seconds: int
    started_at: datetime
    timer_handle: Any | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"alert", "warning"}:
            raise ValueError("kind must be 'alert' or 'warning'")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

    @property
    def mode(self) -> Mode:
        return Mode.OVERRIDE_ALERT if self.kind == "alert" else Mode.OVERRIDE_WARNING

    @property
    def expires_at(self) -> datetime:
        return self.started_at + timedelta(seconds=self.duration_seconds)

    def with_timer(self, handle: Any | None) -> OverrideAction:
        return OverrideAction(
            kind=self.kind,
            duration_seconds=self.duration_seconds,
            started_at=self.started_at,
            timer_handle=handle,
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


_UNSET = object()


@dataclass(frozen=True)
class ControlMode:
    state: Mode
    pilot_switch: bool
    light_on: bool
    last_command_color: RGB
    last_brightness: int
    updated_at: datetime
    override: Optional[OverrideAction] = None

    @classmethod
    def bootstrap(
        cls,
        *,
        default_color: RGB,
        pilot_switch: bool = True,
        light_on: bool = True,
    ) -> ControlMode:
        timestamp = _now()
        return cls(
            state=_derive_state(pilot_switch, light_on, None),
            pilot_switch=pilot_switch,
            light_on=light_on,
            last_command_color=default_color,
            last_brightness=255,
            updated_at=timestamp,
            override=None,
        )

    def record_color_command(
        self,
        *,
        base_color: RGB,
        brightness: Optional[int],
        timestamp: Optional[datetime] = None,
    ) -> ControlMode:
        return self._evolve(
            last_command_color=base_color,
            last_brightness=_clamp_brightness(brightness, fallback=self.last_brightness),
            light_on=True,
            timestamp=timestamp,
        )

    def set_pilot_switch(self, enabled: bool, *, timestamp: Optional[datetime] = None) -> ControlMode:
        return self._evolve(pilot_switch=enabled, timestamp=timestamp)

    def set_light_state(self, *, on: bool, timestamp: Optional[datetime] = None) -> ControlMode:
        return self._evolve(light_on=on, timestamp=timestamp)

    def start_override(
        self,
        *,
        kind: str,
        duration_seconds: int,
        timer_handle: Any | None = None,
        timestamp: Optional[datetime] = None,
    ) -> ControlMode:
        started_at = timestamp or _now()
        action = OverrideAction(
            kind=kind,
            duration_seconds=duration_seconds,
            started_at=started_at,
            timer_handle=timer_handle,
        )
        return self._evolve(override=action, timestamp=started_at)

    def clear_override(self, *, timestamp: Optional[datetime] = None) -> ControlMode:
        return self._evolve(override=None, timestamp=timestamp)

    def snapshot(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "mode": self.state.value,
            "pilot_switch": "ON" if self.pilot_switch else "OFF",
            "light_state": "ON" if self.light_on else "OFF",
            "updated_at": self.updated_at.isoformat(),
            "last_color": self.last_command_color,
            "last_brightness": self.last_brightness,
        }
        if self.override:
            data["override"] = self.override.to_payload()
        return data

    def _evolve(
        self,
        *,
        pilot_switch: Any = _UNSET,
        light_on: Any = _UNSET,
        override: Any = _UNSET,
        last_command_color: Any = _UNSET,
        last_brightness: Any = _UNSET,
        timestamp: Optional[datetime] = None,
    ) -> ControlMode:
        pilot_value: bool = self.pilot_switch if pilot_switch is _UNSET else bool(pilot_switch)
        light_value: bool = self.light_on if light_on is _UNSET else bool(light_on)
        override_value: OverrideAction | None
        if override is _UNSET:
            override_value = self.override
        else:
            override_value = override
        color_value: RGB = self.last_command_color if last_command_color is _UNSET else last_command_color
        brightness_value: int = (
            self.last_brightness if last_brightness is _UNSET else _clamp_brightness(last_brightness, fallback=self.last_brightness)
        )
        new_state = _derive_state(pilot_value, light_value, override_value)
        return ControlMode(
            state=new_state,
            pilot_switch=pilot_value,
            light_on=light_value,
            last_command_color=color_value,
            last_brightness=brightness_value,
            updated_at=timestamp or _now(),
            override=override_value,
        )


def _derive_state(pilot_switch: bool, light_on: bool, override: Optional[OverrideAction]) -> Mode:
    if override:
        return override.mode
    if pilot_switch and light_on:
        return Mode.PILOT
    return Mode.OFF


def _clamp_brightness(value: Optional[int], *, fallback: int) -> int:
    if value is None:
        return fallback
    return max(0, min(255, int(value)))
