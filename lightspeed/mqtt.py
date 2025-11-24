"""MQTT service orchestrating lighting commands and discovery."""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Deque, Dict, Tuple

import paho.mqtt.client as mqtt

from lightspeed.config import ConfigProfile
from lightspeed.control_mode import ControlMode, Mode, mode_payload_from_switch, parse_mode_payload
from lightspeed.ha_contracts import iter_discovery_messages
from lightspeed.observability import (
    configure_last_will,
    override_log_context,
    override_reason,
    publish_availability,
    publish_health,
    publish_status,
)

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from lightspeed.lighting import LightingController


_LIGHTING_MODULE: ModuleType | None = None
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class AlertCommand:
    kind: str
    duration: int


def _lighting_module() -> ModuleType:
    global _LIGHTING_MODULE
    if _LIGHTING_MODULE is None:
        from lightspeed import lighting as lighting_module  # Local import to defer logipy load

        _LIGHTING_MODULE = lighting_module
    return _LIGHTING_MODULE


def _parse_color_command(payload: str, base_color: RGB) -> Tuple[RGB, RGB, int | None]:
    lighting = _lighting_module()
    if not payload:
        return base_color, base_color, None

    brightness: int | None = None
    color_value: RGB | None = None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        color_value = _extract_color_from_dict(data)
        brightness = _extract_brightness(data)
    elif isinstance(data, list) and len(data) == 3:
        color_value = tuple(int(channel) for channel in data)  # type: ignore[assignment]

    if color_value is None:
        try:
            color_value = lighting.parse_color_string(payload)
        except ValueError:
            color_value = None

    new_base = color_value or base_color
    rgb = new_base
    if brightness is not None:
        rgb = lighting.apply_brightness(rgb, brightness)
    return rgb, new_base, brightness


def _extract_light_state(payload: str) -> str | None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        state_value = data.get("state")
        if isinstance(state_value, str):
            upper = state_value.strip().upper()
            if upper in {"ON", "OFF"}:
                return upper
    return None


def _extract_color_from_dict(data: dict) -> RGB | None:
    color_section = data.get("color")
    if isinstance(color_section, dict):
        try:
            return tuple(int(color_section[key]) for key in ("r", "g", "b"))  # type: ignore[return-value]
        except (KeyError, TypeError, ValueError):
            pass
    if all(axis in data for axis in ("r", "g", "b")):
        try:
            return tuple(int(data[axis]) for axis in ("r", "g", "b"))  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    rgb_color = data.get("rgb_color")
    if isinstance(rgb_color, list) and len(rgb_color) == 3:
        try:
            return tuple(int(channel) for channel in rgb_color)  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    return None


def _extract_brightness(data: dict) -> int | None:
    if "brightness" in data:
        try:
            return int(data["brightness"])
        except (TypeError, ValueError):
            return None
    if "brightness_pct" in data:
        try:
            pct = float(data["brightness_pct"])
        except (TypeError, ValueError):
            return None
        pct = max(0.0, min(100.0, pct))
        return int(round((pct / 100.0) * 255))
    return None


def _percent_to_byte(value: int) -> int:
    value = max(0, min(100, int(value)))
    return int(round((value / 100) * 255))


def _byte_to_percent(value: int) -> int:
    value = max(0, min(255, int(value)))
    return int(round((value / 255) * 100))


logger = logging.getLogger(__name__)


class MqttLightingService:
    def __init__(self, controller: "LightingController", profile: ConfigProfile, *, validated_at: datetime) -> None:
        self.controller = controller
        self.profile = profile
        self.validated_at = validated_at
        self.stop_event = threading.Event()
        self.last_error: str | None = None
        self.validation_status = "passed"
        self.control = ControlMode.bootstrap(default_color=profile.lighting.default_color)
        self._connected = False
        self.client = mqtt.Client(client_id=profile.mqtt.client_id, clean_session=True)
        self._timer_factory = threading.Timer
        self._local_echo: Dict[str, Deque[str]] = {}
        if profile.mqtt.username:
            self.client.username_pw_set(profile.mqtt.username, profile.mqtt.password or None)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        configure_last_will(self.client, self.profile)

    def start(self) -> None:
        self.controller.start()
        self.controller.set_static_color(self.profile.lighting.default_color)
        self.control = self.control.record_color_command(
            base_color=self.profile.lighting.default_color,
            brightness=255,
        )
        logger.info(
            "Connexion MQTT",
            extra={"host": self.profile.mqtt.host, "port": self.profile.mqtt.port},
        )
        self.client.connect(
            self.profile.mqtt.host,
            self.profile.mqtt.port,
            keepalive=self.profile.mqtt.keepalive,
        )
        self.client.loop_start()

    def stop(self) -> None:
        self.stop_event.set()

    def loop_forever(self) -> None:
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)
        finally:
            if self._connected:
                self._publish_status(state="offline", reason="shutdown")
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            self.controller.shutdown()

    def on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int) -> None:
        if rc != 0:
            logger.error("Connexion MQTT refusée", extra={"code": rc})
            return
        self._connected = True
        for topic in (
            self.profile.topics.color,
            self.profile.topics.brightness,
            self.profile.topics.power,
            self.profile.topics.mode,
            self.profile.topics.alert,
        ):
            client.subscribe(topic, qos=1)
        logger.info("Connecté au broker")
        self._publish_availability("online")
        self._publish_status(reason="connected")
        self._publish_mode_state()
        self._publish_power_state("ON" if self.control.light_on else "OFF")
        self._publish_brightness_state(_byte_to_percent(self.control.last_brightness))
        self._publish_color_state(self.control.last_command_color, self.control.last_brightness)
        self._publish_health("online")
        self._publish_discovery()

    def on_message(self, _client: mqtt.Client, _userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="ignore").strip()
        try:
            if self._consume_local_echo(topic, payload):
                return
            if topic == self.profile.topics.power:
                self._handle_power_command(payload)
            elif topic == self.profile.topics.mode:
                self._handle_mode_command(payload)
            elif topic == self.profile.topics.color:
                requested_state = _extract_light_state(payload)
                if requested_state == "OFF":
                    self._handle_power_command("OFF")
                    return
                if requested_state == "ON" and not self.control.light_on:
                    control = self.control.set_light_state(on=True)
                    self._update_control(control, reason="ha_light_on")
                    self._publish_power_state("ON")
                if not self.control.pilot_switch:
                    logger.info("Commande couleur ignorée (pilot OFF)")
                    self._publish_status(reason="color_ignored_pilot_off")
                    return
                if not self.control.light_on:
                    logger.info("Commande couleur ignorée (light OFF)")
                    self._publish_status(reason="color_ignored_light_off")
                    return
                lighting = _lighting_module()
                rgb, base_color, brightness = _parse_color_command(payload, self.control.last_command_color)
                if self.control.override:
                    override_kind = self.control.override.kind
                    updated = self.control.record_color_command(
                        base_color=base_color,
                        brightness=brightness,
                    )
                    self._update_control(updated, reason=override_reason(override_kind, "color_cached"))
                    logger.info(
                        "Commande couleur mise en cache (override actif)",
                        extra=override_log_context(override_kind, action="color_cached"),
                    )
                    return
                if brightness is None:
                    color_to_apply = lighting.apply_brightness(rgb, self.control.last_brightness)
                else:
                    color_to_apply = rgb
                self.controller.set_static_color(color_to_apply)
                updated = self.control.record_color_command(
                    base_color=base_color,
                    brightness=brightness,
                )
                self._update_control(updated, reason="color_command")
                self._publish_power_state("ON")
                self._publish_color_state(updated.last_command_color, updated.last_brightness)
                self._publish_brightness_state(_byte_to_percent(updated.last_brightness))
                logger.info("Couleur appliquée", extra={"color": color_to_apply})
            elif topic == self.profile.topics.brightness:
                self._handle_brightness_command(payload)
            elif topic == self.profile.topics.alert:
                command = self._parse_alert_command(payload)
                if command:
                    self._handle_override_command(command)
            else:
                logger.debug("Topic ignoré", extra={"topic": topic})
            self.last_error = None
            self._publish_health("online")
        except Exception as exc:  # pragma: no cover - defensive logging
            self.last_error = str(exc)
            logger.exception("Erreur MQTT", extra={"topic": topic})
            self._publish_health("error")

    def _publish_status(self, *, state: str = "online", reason: str | None = None) -> None:
        if not self._connected:
            return
        publish_status(self.client, self.profile, self.control, state=state, reason=reason)
        if state == "offline":
            self._publish_availability("offline")

    def _publish_health(self, status: str) -> None:
        publish_health(
            self.client,
            self.profile,
            status=status,
            validated_at=self.validated_at,
            validation_status=self.validation_status,
            last_error=self.last_error,
        )

    def _publish_availability(self, state: str) -> None:
        if not self._connected:
            return
        publish_availability(self.client, self.profile, state)

    def _publish_power_state(self, payload: str) -> None:
        if not self._connected:
            return
        self.client.publish(self.profile.topics.power_state, payload=payload, qos=1, retain=True)

    def _publish_mode_state(self, payload: str | None = None) -> None:
        if not self._connected:
            return
        normalized = (payload or "").strip().lower()
        if normalized not in {Mode.PILOT.value, Mode.LOGI.value}:
            normalized = mode_payload_from_switch(self.control.pilot_switch)
        self._record_local_publish(self.profile.topics.mode, normalized)
        self.client.publish(self.profile.topics.mode, payload=normalized, qos=1, retain=True)
        self.client.publish(self.profile.topics.mode_state, payload=normalized, qos=1, retain=True)

    def _publish_color_state(self, color: RGB, brightness: int) -> None:
        if not self._connected:
            return
        payload = json.dumps(
            {
                "state": "ON" if self.control.light_on else "OFF",
                "color": {"r": color[0], "g": color[1], "b": color[2]},
                "brightness": brightness,
            },
            separators=(",", ":"),
        )
        self.client.publish(self.profile.topics.color_state, payload=payload, qos=1, retain=True)

    def _publish_brightness_state(self, brightness_pct: int) -> None:
        if not self._connected:
            return
        brightness_pct = max(0, min(100, brightness_pct))
        payload = json.dumps({"brightness": brightness_pct}, separators=(",", ":"))
        self.client.publish(self.profile.topics.brightness_state, payload=payload, qos=1, retain=True)

    def _record_local_publish(self, topic: str, payload: str) -> None:
        queue = self._local_echo.setdefault(topic, deque())
        queue.append(payload)

    def _consume_local_echo(self, topic: str, payload: str) -> bool:
        queue = self._local_echo.get(topic)
        if not queue:
            return False
        if queue[0] == payload:
            queue.popleft()
            if not queue:
                self._local_echo.pop(topic, None)
            return True
        return False

    def _publish_discovery(self) -> None:
        for message in iter_discovery_messages(self.profile):
            self.client.publish(message.topic, payload=message.payload, qos=1, retain=message.retain)

    def _update_control(self, new_state: ControlMode, *, reason: str) -> None:
        self.control = new_state
        self._publish_status(reason=reason)

    def bootstrap_pilot_switch(self, enabled: bool) -> None:
        control = self.control.set_pilot_switch(enabled)
        self.control = control

    def _handle_power_command(self, payload: str) -> None:
        desired = (payload or "").strip().upper()
        if desired not in {"ON", "OFF"}:
            logger.warning("Commande power invalide", extra={"payload": payload})
            self._publish_power_state("ON" if self.control.light_on else "OFF")
            return
        if desired == "ON":
            updated = self.control.set_light_state(on=True)
            if updated.pilot_switch:
                lighting = _lighting_module()
                color_to_apply = lighting.apply_brightness(updated.last_command_color, updated.last_brightness)
                self.controller.set_static_color(color_to_apply)
            self._update_control(updated, reason="power_on")
            self._publish_power_state("ON")
            self._publish_brightness_state(_byte_to_percent(updated.last_brightness))
            self._publish_color_state(updated.last_command_color, updated.last_brightness)
        else:
            self._handle_light_off(reason="power_off")

    def _handle_brightness_command(self, payload: str) -> None:
        value = self._parse_brightness_payload(payload)
        if value is None:
            logger.warning("Commande brightness invalide", extra={"payload": payload})
            return
        if not self.control.pilot_switch:
            logger.info("Commande brightness ignorée (pilot OFF)")
            self._publish_status(reason="brightness_ignored_pilot_off")
            return
        lighting = _lighting_module()
        byte_value = _percent_to_byte(value)
        color_to_apply = lighting.apply_brightness(self.control.last_command_color, byte_value)
        self.controller.set_static_color(color_to_apply)
        updated = self.control.record_color_command(
            base_color=self.control.last_command_color,
            brightness=byte_value,
        )
        self._update_control(updated, reason="brightness_command")
        self._publish_power_state("ON")
        self._publish_brightness_state(value)
        self._publish_color_state(updated.last_command_color, updated.last_brightness)

    def _parse_brightness_payload(self, payload: str) -> int | None:
        if not payload:
            return None
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = None
        raw_value: object
        if isinstance(data, dict) and "brightness" in data:
            raw_value = data["brightness"]
        else:
            raw_value = payload
        try:
            value = int(raw_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if not 0 <= value <= 100:
            return None
        return value

    def _parse_alert_command(self, payload: str) -> AlertCommand | None:
        default_duration = self.profile.effects.override_duration_seconds
        if not payload:
            return AlertCommand(kind="alert", duration=default_duration)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Commande alert invalide", extra={"payload": payload})
            return None
        if not isinstance(data, dict):
            logger.warning("Commande alert invalide", extra={"payload": payload})
            return None
        type_value = data.get("type", "alert")
        if isinstance(type_value, str):
            normalized = type_value.strip().lower() or "alert"
        else:
            logger.warning("Commande alert invalide", extra={"payload": payload})
            return None
        if normalized == "info":
            normalized = "alert"
        if normalized not in {"alert", "warning"}:
            logger.warning("Commande alert invalide", extra={"payload": payload})
            return None
        duration_value = data.get("duration")
        if duration_value is None:
            duration = default_duration
        else:
            try:
                duration = int(duration_value)
            except (TypeError, ValueError):
                logger.warning(
                    "Durée override invalide",
                    extra=override_log_context(normalized, action="invalid_duration", invalid_value=duration_value),
                )
                return None
            if duration < 1 or duration > 300:
                logger.warning(
                    "Durée override hors limites",
                    extra=override_log_context(normalized, action="invalid_duration", duration=duration),
                )
                return None
        return AlertCommand(kind=normalized, duration=duration)

    def _handle_mode_command(self, payload: str) -> None:
        desired = parse_mode_payload(payload)
        if desired is None:
            logger.warning("Commande mode invalide", extra={"payload": payload})
            self._publish_mode_state()
            return
        if desired is Mode.PILOT:
            self._enter_pilot_mode()
        else:
            self._exit_pilot_mode()

    def _enter_pilot_mode(self) -> None:
        if self.control.pilot_switch:
            self._publish_mode_state("pilot")
            if not self.control.light_on:
                self._handle_power_command("ON")
            else:
                self._publish_power_state("ON")
            return
        self._clear_override(resume_base=False, event="pilot_toggle")
        control = self.control.set_pilot_switch(True)
        self._update_control(control, reason="pilot_enable")
        self._publish_mode_state("pilot")
        self._handle_power_command("ON")
        logger.info("Mode pilot activé")

    def _exit_pilot_mode(self) -> None:
        if not self.control.pilot_switch:
            self._publish_mode_state("logi")
            if self.control.light_on:
                self._handle_power_command("OFF")
            else:
                self._publish_power_state("OFF")
            return
        self._handle_light_off(reason="pilot_disable")
        self.controller.shutdown()
        control = self.control.set_pilot_switch(False)
        self._update_control(control, reason="pilot_disable")
        self._publish_mode_state("logi")
        logger.info("Mode pilot désactivé, Logitech reprend la main")

    def _handle_light_off(self, *, reason: str) -> None:
        self._clear_override(resume_base=False, event="light_off")
        lighting = _lighting_module()
        lighting.restore_logitech_control(self.controller)
        control = self.control.set_light_state(on=False)
        self._update_control(control, reason=reason)
        self._publish_power_state("OFF")
        self._publish_brightness_state(_byte_to_percent(control.last_brightness))
        self._publish_color_state(control.last_command_color, control.last_brightness)

    def _handle_override_command(self, command: AlertCommand) -> None:
        self._clear_override(resume_base=False, event="replaced")
        lighting = _lighting_module()
        frames = (
            lighting.alert_frames(self.profile)
            if command.kind == "alert"
            else lighting.warning_frames(self.profile)
        )
        timer = self._timer_factory(command.duration, self._complete_override, args=(command.kind,))
        timer.daemon = True
        timer.start()
        control = self.control.start_override(
            kind=command.kind,
            duration_seconds=command.duration,
            timer_handle=timer,
        )
        self.controller.start_pattern(frames)
        logger.info(
            "Override %s démarrée", command.kind,
            extra=override_log_context(command.kind, action="start", duration=command.duration),
        )
        self._update_control(control, reason=override_reason(command.kind, "start"))

    def _complete_override(self, kind: str) -> None:
        cleared = self._clear_override(resume_base=True, event="complete")
        if cleared:
            logger.info("Override %s terminée", kind, extra=override_log_context(kind, action="complete"))

    def _clear_override(self, *, resume_base: bool, event: str) -> bool:
        override = self.control.override
        if not override:
            return False
        timer = override.timer_handle
        if timer and hasattr(timer, "cancel"):
            try:
                timer.cancel()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Annulation du timer override impossible", exc_info=True)
        self.controller.stop_pattern()
        control = self.control.clear_override()
        if resume_base:
            lighting = _lighting_module()
            if control.pilot_switch and control.light_on:
                lighting.reapply_cached_color(
                    self.controller,
                    control.last_command_color,
                    control.last_brightness,
                )
            else:
                lighting.restore_logitech_control(self.controller)
        self._update_control(control, reason=override_reason(override.kind, event))
        logger.info(
            "Override %s arrêtée (%s)",
            override.kind,
            event,
            extra=override_log_context(override.kind, action=event),
        )
        return True