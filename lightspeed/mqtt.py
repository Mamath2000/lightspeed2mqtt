"""MQTT service orchestrating lighting commands and discovery."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt

from lightspeed.config import ConfigProfile
from lightspeed.ha_contracts import iter_discovery_messages
from lightspeed.observability import build_health_payload

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from lightspeed.lighting import LightingController


_LIGHTING_MODULE: ModuleType | None = None


def _lighting_module() -> ModuleType:
    global _LIGHTING_MODULE
    if _LIGHTING_MODULE is None:
        from lightspeed import lighting as lighting_module  # Local import to defer logipy load

        _LIGHTING_MODULE = lighting_module
    return _LIGHTING_MODULE

logger = logging.getLogger(__name__)


class MqttLightingService:
    def __init__(self, controller: "LightingController", profile: ConfigProfile, *, validated_at: datetime) -> None:
        self.controller = controller
        self.profile = profile
        self.validated_at = validated_at
        self.stop_event = threading.Event()
        self.last_error: str | None = None
        self.validation_status = "passed"
        self.client = mqtt.Client(client_id=profile.mqtt.client_id, clean_session=True)
        if profile.mqtt.username:
            self.client.username_pw_set(profile.mqtt.username, profile.mqtt.password or None)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.will_set(profile.topics.status, payload="offline", qos=1, retain=True)

    def start(self) -> None:
        self.controller.start()
        self.controller.set_static_color(self.profile.lighting.default_color)
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
            self.client.loop_stop()
            self.client.disconnect()
            self.controller.shutdown()

    def on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int) -> None:
        if rc != 0:
            logger.error("Connexion MQTT refusée", extra={"code": rc})
            return
        for topic in (
            self.profile.topics.color,
            self.profile.topics.alert,
            self.profile.topics.warning,
            self.profile.topics.auto,
        ):
            client.subscribe(topic, qos=1)
        logger.info("Connecté au broker")
        self._publish_status("online")
        self._publish_health("online")
        self._publish_discovery()

    def on_message(self, _client: mqtt.Client, _userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="ignore").strip()
        try:
            if topic == self.profile.topics.color:
                lighting = _lighting_module()
                color = lighting.parse_color_string(payload) if payload else self.profile.lighting.default_color
                if not color:
                    raise ValueError("Couleur manquante pour topic couleur")
                self.controller.set_static_color(color)
                logger.info("Couleur appliquée", extra={"color": color})
            elif topic == self.profile.topics.alert:
                lighting = _lighting_module()
                self.controller.start_pattern(lighting.alert_frames(self.profile))
                logger.info("Pattern alerte actif")
            elif topic == self.profile.topics.warning:
                lighting = _lighting_module()
                self.controller.start_pattern(lighting.warning_frames(self.profile))
                logger.info("Pattern warning actif")
            elif topic == self.profile.topics.auto:
                self.controller.release()
                logger.info("Mode automatique restauré")
            else:
                logger.debug("Topic ignoré", extra={"topic": topic})
            self.last_error = None
            self._publish_health("online")
        except Exception as exc:  # pragma: no cover - defensive logging
            self.last_error = str(exc)
            logger.exception("Erreur MQTT", extra={"topic": topic})
            self._publish_health("error")

    def _publish_status(self, payload: str) -> None:
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