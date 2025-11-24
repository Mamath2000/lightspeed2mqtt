"""MQTT service orchestrating lighting commands and discovery."""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Tuple

import paho.mqtt.client as mqtt

from lightspeed.config import ConfigProfile
from lightspeed.control_mode import ControlMode
from lightspeed.ha_contracts import iter_discovery_messages
from lightspeed.observability import build_health_payload, build_status_payload, override_log_context, override_reason

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from lightspeed.lighting import LightingController


_LIGHTING_MODULE: ModuleType | None = None
RGB = Tuple[int, int, int]


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
        if profile.mqtt.username:
            self.client.username_pw_set(profile.mqtt.username, profile.mqtt.password or None)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.will_set(
            profile.topics.status,
            payload=build_status_payload(self.control, state="offline", reason="lwt"),
            qos=1,
            retain=True,
        )

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
            self.profile.topics.alert,
            self.profile.topics.warning,
            self.profile.topics.auto,
        ):
            client.subscribe(topic, qos=1)
        logger.info("Connecté au broker")
        self._publish_status(reason="connected")
        self._publish_switch_state("ON" if self.control.pilot_switch else "OFF")
        self._publish_health("online")
        self._publish_discovery()

    def on_message(self, _client: mqtt.Client, _userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="ignore").strip()
        try:
            if topic == self.profile.topics.color:
                requested_state = _extract_light_state(payload)
                if requested_state == "OFF":
                    self._handle_light_off(reason="ha_light_off")
                    return
                if requested_state == "ON" and not self.control.light_on:
                    control = self.control.set_light_state(on=True)
                    self._update_control(control, reason="ha_light_on")
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
                logger.info("Couleur appliquée", extra={"color": color_to_apply})
            elif topic == self.profile.topics.alert:
                self._handle_override_command(kind="alert", payload=payload)
            elif topic == self.profile.topics.warning:
                self._handle_override_command(kind="warning", payload=payload)
            elif topic == self.profile.topics.auto:
                self._handle_pilot_switch(payload)
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
        payload = build_status_payload(self.control, state=state, reason=reason)
        self.client.publish(self.profile.topics.status, payload=payload, qos=1, retain=True)

    def _publish_health(self, status: str) -> None:
        payload = build_health_payload(
            self.profile,
            status=status,
            validated_at=self.validated_at,
            validation_status=self.validation_status,
            last_error=self.last_error,
        )
        self.client.publish(
            self.profile.observability.health_topic,
            payload=payload,
            qos=1,
            retain=True,
        )

    def _publish_discovery(self) -> None:
        for message in iter_discovery_messages(self.profile):
            self.client.publish(message.topic, payload=message.payload, qos=1, retain=message.retain)

    def _update_control(self, new_state: ControlMode, *, reason: str) -> None:
        self.control = new_state
        self._publish_status(reason=reason)

    def bootstrap_pilot_switch(self, enabled: bool) -> None:
        control = self.control.set_pilot_switch(enabled)
        self.control = control

    def _handle_pilot_switch(self, payload: str) -> None:
        desired = (payload or "").strip().upper()
        if desired == "ON":
            self._enter_pilot_mode()
        elif desired == "OFF":
            self._exit_pilot_mode()
        else:
            logger.warning("Commande pilot invalide", extra={"payload": payload})

    def _enter_pilot_mode(self) -> None:
        if self.control.pilot_switch:
            self._publish_switch_state("ON")
            return
        self._clear_override(resume_base=False, event="pilot_toggle")
        control = self.control.set_pilot_switch(True)
        if control.light_on:
            lighting = _lighting_module()
            lighting.reapply_cached_color(
                self.controller,
                control.last_command_color,
                control.last_brightness,
            )
        self._update_control(control, reason="pilot_enable")
        self._publish_switch_state("ON")
        logger.info("Mode pilot activé")

    def _exit_pilot_mode(self) -> None:
        if not self.control.pilot_switch:
            self._publish_switch_state("OFF")
            return
        self._clear_override(resume_base=False, event="pilot_toggle")
        lighting = _lighting_module()
        lighting.restore_logitech_control(self.controller)
        self.controller.shutdown()
        control = self.control.set_pilot_switch(False)
        self._update_control(control, reason="pilot_disable")
        self._publish_switch_state("OFF")
        logger.info("Mode pilot désactivé, Logitech reprend la main")

    def _publish_switch_state(self, payload: str) -> None:
        if not self._connected:
            return
        self.client.publish(self.profile.topics.auto_state, payload=payload, qos=1, retain=True)

    def _handle_light_off(self, *, reason: str) -> None:
        self._clear_override(resume_base=False, event="light_off")
        lighting = _lighting_module()
        lighting.restore_logitech_control(self.controller)
        control = self.control.set_light_state(on=False)
        self._update_control(control, reason=reason)

    def _handle_override_command(self, *, kind: str, payload: str) -> None:
        duration = self._resolve_override_duration(kind, payload)
        if duration is None:
            return
        self._clear_override(resume_base=False, event="replaced")
        lighting = _lighting_module()
        frames = (
            lighting.alert_frames(self.profile)
            if kind == "alert"
            else lighting.warning_frames(self.profile)
        )
        timer = self._timer_factory(duration, self._complete_override, args=(kind,))
        timer.daemon = True
        timer.start()
        control = self.control.start_override(
            kind=kind,
            duration_seconds=duration,
            timer_handle=timer,
        )
        self.controller.start_pattern(frames)
        logger.info(
            "Override %s démarrée", kind,
            extra=override_log_context(kind, action="start", duration=duration),
        )
        self._update_control(control, reason=override_reason(kind, "start"))

    def _complete_override(self, kind: str) -> None:
        cleared = self._clear_override(resume_base=True, event="complete")
        if cleared:
            logger.info("Override %s terminée", kind, extra=override_log_context(kind, action="complete"))

    def _resolve_override_duration(self, kind: str, payload: str) -> int | None:
        base_duration = self.profile.effects.override_duration_seconds
        if not payload:
            return base_duration
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return base_duration
        if isinstance(data, dict) and "duration" in data:
            raw_value = data["duration"]
            try:
                requested = int(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "Durée override invalide",
                    extra=override_log_context(kind, action="invalid_duration", invalid_value=raw_value),
                )
                return None
            if requested < 1 or requested > 300:
                logger.warning(
                    "Durée override hors limites",
                    extra=override_log_context(kind, action="invalid_duration", duration=requested),
                )
                return None
            return requested
        return base_duration

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