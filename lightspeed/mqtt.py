"""MQTT service orchestrating lighting commands and discovery."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Tuple

import paho.mqtt.client as mqtt

from lightspeed.config import ConfigProfile
from lightspeed.control_mode import ControlMode
from lightspeed.ha_contracts import iter_discovery_messages
from lightspeed.observability import (
    configure_last_will,
    publish_availability,
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


logger = logging.getLogger(__name__)


class MqttLightingService:
    def __init__(self, controller: "LightingController", profile: ConfigProfile, *, validated_at: datetime) -> None:
        self.controller = controller
        self.profile = profile
        self.validated_at = validated_at
        self.stop_event = threading.Event()
        self.last_error: str | None = None
        self.control = ControlMode.bootstrap(default_color=profile.lighting.default_color)
        # Initialiser avec un état par défaut (lumière on, couleur par défaut, brightness max)
        self.control = self.control.set_light_state(on=True).record_color_command(
            base_color=profile.lighting.default_color,
            brightness=255,
        )
        self._connected = False
        self.client = mqtt.Client(client_id=profile.mqtt.client_id, clean_session=True)
        self._timer_factory = threading.Timer
        if profile.mqtt.username:
            self.client.username_pw_set(profile.mqtt.username, profile.mqtt.password or None)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        configure_last_will(self.client, self.profile)

    def bootstrap_from_retained(self, state: dict) -> None:
        """Initialise l'état depuis un message retained."""
        try:
            # Extraire l'état
            is_on = state.get("state", "off").lower() == "on"
            rgb = state.get("rgb", list(self.profile.lighting.default_color))
            brightness = state.get("brightness", 255)
            mode = state.get("mode", "pilot").lower()
            
            # Valider et convertir RGB
            if isinstance(rgb, list) and len(rgb) == 3:
                color = tuple(int(c) for c in rgb)
            else:
                color = self.profile.lighting.default_color
            
            # Valider brightness
            brightness = max(0, min(255, int(brightness)))
            
            # Valider et appliquer le mode
            pilot_mode = (mode == "pilot")
            
            # Mettre à jour l'état interne
            self.control = self.control.set_pilot_switch(pilot_mode).set_light_state(on=is_on).record_color_command(
                base_color=color,
                brightness=brightness,
            )
            
            logger.info(
                "État bootstrappé",
                extra={"state": "on" if is_on else "off", "rgb": color, "brightness": brightness, "mode": mode}
            )
        except Exception as exc:
            logger.warning("Échec du bootstrap depuis retained", extra={"error": str(exc)})

    def start(self) -> None:
        self.controller.start()
        
        # Appliquer l'état actuel au clavier seulement si en mode pilot
        if self.control.pilot_switch:
            if self.control.light_on:
                lighting = _lighting_module()
                color_to_apply = lighting.apply_brightness(
                    self.control.last_command_color,
                    self.control.last_brightness
                )
                self.controller.set_static_color(color_to_apply)
                logger.info("Clavier initialisé (pilot mode)", extra={"color": color_to_apply})
            else:
                self.controller.set_static_color((0, 0, 0))
                logger.info("Clavier éteint (pilot mode)")
        else:
            logger.info("Mode auto, contrôle Logitech actif")
        
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
                self._publish_availability("offline")
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            self.controller.shutdown()

    def on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int) -> None:
        if rc != 0:
            logger.error("Connexion MQTT refusée", extra={"code": rc})
            return
        self._connected = True
        
        # S'abonner aux topics de commande
        client.subscribe(self.profile.topics.command_topic, qos=1)
        client.subscribe(self.profile.topics.rgb_command_topic, qos=1)
        client.subscribe(self.profile.topics.brightness_command_topic, qos=1)
        client.subscribe(self.profile.topics.alert_command_topic, qos=1)
        client.subscribe(self.profile.topics.warn_command_topic, qos=1)
        client.subscribe(self.profile.topics.info_command_topic, qos=1)
        client.subscribe(self.profile.topics.mode_command_topic, qos=1)
        
        logger.info("Connecté au broker")
        self._publish_availability("online")
        self._publish_light_state()
        # self._publish_mode_state()  # Suppression : ne publie plus le mode seul sur state_topic
        self._publish_discovery()

    def on_message(self, _client: mqtt.Client, _userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="ignore").strip()
        try:
            if topic == self.profile.topics.command_topic:
                self._handle_switch_command(payload)
            elif topic == self.profile.topics.rgb_command_topic:
                self._handle_rgb_command(payload)
            elif topic == self.profile.topics.brightness_command_topic:
                self._handle_brightness_command(payload)
            elif topic == self.profile.topics.alert_command_topic:
                self._handle_alert_button()
            elif topic == self.profile.topics.warn_command_topic:
                self._handle_warn_button()
            elif topic == self.profile.topics.info_command_topic:
                self._handle_info_button()
            elif topic == self.profile.topics.mode_command_topic:
                self._handle_mode_command(payload)
            else:
                logger.debug("Topic ignoré", extra={"topic": topic})
            self.last_error = None
        except Exception as exc:  # pragma: no cover - defensive logging
            self.last_error = str(exc)
            logger.exception("Erreur MQTT", extra={"topic": topic})

    def _publish_light_state(self) -> None:
        """Publie l'état complet de la lumière sur state_topic."""
        if not self._connected:
            return
        
        payload = json.dumps({
            "state": "on" if self.control.light_on else "off",
            "rgb": list(self.control.last_command_color),
            "brightness": self.control.last_brightness,
            "mode": "pilot" if self.control.pilot_switch else "auto",
        }, separators=(",", ":"))
        
        self.client.publish(
            self.profile.topics.state_topic,
            payload=payload,
            qos=1,
            retain=True
        )

    # _publish_mode_state supprimé : le mode est inclus dans l'état complet publié par _publish_light_state

    def _handle_switch_command(self, payload: str) -> None:
        """Gère les commandes on/off sur command_topic."""
        desired = payload.strip().lower()
        if desired not in {"on", "off"}:
            logger.warning("Commande switch invalide", extra={"payload": payload})
            self._publish_light_state()
            return
        
        if desired == "on":
            updated = self.control.set_light_state(on=True)
            self.control = updated
            
            # Appliquer physiquement seulement si en mode pilot
            if self.control.pilot_switch:
                lighting = _lighting_module()
                color_to_apply = lighting.apply_brightness(
                    updated.last_command_color,
                    updated.last_brightness
                )
                self.controller.set_static_color(color_to_apply)
                logger.info("Lumière allumée", extra={"color": color_to_apply})
            else:
                logger.info("Lumière allumée (état uniquement, mode auto)")
        else:
            updated = self.control.set_light_state(on=False)
            self.control = updated
            
            # Appliquer physiquement seulement si en mode pilot
            if self.control.pilot_switch:
                self.controller.stop_pattern()
                self.controller.set_static_color((0, 0, 0))
                logger.info("Lumière éteinte")
            else:
                logger.info("Lumière éteinte (état uniquement, mode auto)")
        
        self._publish_light_state()

    def _handle_rgb_command(self, payload: str) -> None:
        """Gère les commandes RGB sur rgb_command_topic."""
        if not self.control.light_on:
            logger.info("Commande RGB ignorée (light OFF)")
            return
        
        if not self.control.pilot_switch:
            logger.info("Commande RGB ignorée (mode auto)")
            return
        
        lighting = _lighting_module()
        try:
            rgb = lighting.parse_color_string(payload)
        except ValueError as exc:
            logger.warning("Commande RGB invalide", extra={"payload": payload, "error": str(exc)})
            return
        
        # Si un effet est actif, on cache la couleur
        if self.control.override:
            updated = self.control.record_color_command(
                base_color=rgb,
                brightness=self.control.last_brightness,
            )
            self.control = updated
            logger.info("Couleur mise en cache (effet actif)", extra={"rgb": rgb})
            return
        
        # Applique la couleur avec la luminosité actuelle
        color_to_apply = lighting.apply_brightness(rgb, self.control.last_brightness)
        self.controller.set_static_color(color_to_apply)
        
        updated = self.control.record_color_command(
            base_color=rgb,
            brightness=self.control.last_brightness,
        )
        self.control = updated
        self._publish_light_state()
        logger.info("Couleur RGB appliquée", extra={"rgb": rgb})

    def _handle_brightness_command(self, payload: str) -> None:
        """Gère les commandes de luminosité sur brightness_command_topic."""
        if not self.control.light_on:
            logger.info("Commande brightness ignorée (light OFF)")
            return
        
        if not self.control.pilot_switch:
            logger.info("Commande brightness ignorée (mode auto)")
            return
        
        brightness = None
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                brightness = int(data.get("brightness", 255))
            elif isinstance(data, (int, float)):
                brightness = int(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            try:
                brightness = int(payload)
            except (ValueError, TypeError):
                logger.warning("Commande brightness invalide", extra={"payload": payload})
                return
        
        if brightness is None:
            logger.warning("Commande brightness invalide", extra={"payload": payload})
            return
        
        brightness = max(0, min(255, brightness))
        
        # Si un effet est actif, on cache la luminosité
        if self.control.override:
            updated = self.control.record_color_command(
                base_color=self.control.last_command_color,
                brightness=brightness,
            )
            self.control = updated
            logger.info("Luminosité mise en cache (effet actif)", extra={"brightness": brightness})
            return
        
        # Applique la luminosité
        lighting = _lighting_module()
        color_to_apply = lighting.apply_brightness(self.control.last_command_color, brightness)
        self.controller.set_static_color(color_to_apply)
        
        updated = self.control.record_color_command(
            base_color=self.control.last_command_color,
            brightness=brightness,
        )
        self.control = updated
        self._publish_light_state()
        logger.info("Luminosité appliquée", extra={"brightness": brightness})

    def _handle_alert_button(self) -> None:
        """Déclenche une alerte visuelle Alert (rouge clignotant)."""
        duration = self.profile.effects.override_duration_seconds
        self._handle_override_command(AlertCommand(kind="alert", duration=duration))
        logger.info("⚠️ Alerte visuelle déclenchée")

    def _handle_warn_button(self) -> None:
        """Déclenche une alerte visuelle Warn (orange clignotant)."""
        duration = self.profile.effects.override_duration_seconds
        self._handle_override_command(AlertCommand(kind="warning", duration=duration))
        logger.info("⚠️ Avertissement visuel déclenché")

    def _handle_info_button(self) -> None:
        """Déclenche une alerte visuelle Info (palette info)."""
        duration = self.profile.effects.override_duration_seconds
        self._handle_override_command(AlertCommand(kind="info", duration=duration))
        logger.info("ℹ️ Info visuelle déclenchée")

    def _handle_mode_command(self, payload: str) -> None:
        """Gère les commandes de mode (pilot/auto) depuis mode_command_topic."""
        mode = payload.strip().lower()
        
        if mode not in {"pilot", "auto"}:
            logger.warning("Commande mode invalide", extra={"payload": payload})
            self._publish_mode_state()
            return
        
        desired_pilot = (mode == "pilot")
        
        if desired_pilot == self.control.pilot_switch:
            # Pas de changement
            self._publish_mode_state()
            return
        
        if desired_pilot:
            self._enter_pilot_mode()
        else:
            self._exit_pilot_mode()

    def _enter_pilot_mode(self) -> None:
        """Active le mode pilot - le programme pilote le clavier."""
        updated = self.control.set_pilot_switch(True)
        self.control = updated
        
        # Synchroniser le clavier avec l'état actuel de la light
        if self.control.light_on:
            lighting = _lighting_module()
            color_to_apply = lighting.apply_brightness(
                self.control.last_command_color,
                self.control.last_brightness
            )
            self.controller.set_static_color(color_to_apply)
            logger.info("Mode pilot activé, clavier synchronisé", extra={"color": color_to_apply})
        else:
            self.controller.set_static_color((0, 0, 0))
            logger.info("Mode pilot activé, clavier éteint")
        
        self._publish_light_state()

    def _exit_pilot_mode(self) -> None:
        """Désactive le mode pilot - rend la main au logiciel Logitech."""
        updated = self.control.set_pilot_switch(False)
        self.control = updated
        
        # Arrêter tout pattern en cours et rendre la main
        self.controller.stop_pattern()
        lighting = _lighting_module()
        lighting.restore_logitech_control(self.controller)
        
        logger.info("Mode pilot désactivé, contrôle rendu à Logitech")
        self._publish_light_state()

    def _publish_availability(self, state: str) -> None:
        if not self._connected:
            return
        publish_availability(self.client, self.profile, state)

    def _publish_discovery(self) -> None:
        for message in iter_discovery_messages(self.profile):
            self.client.publish(message.topic, payload=message.payload, qos=1, retain=message.retain)

    def _handle_override_command(self, command: AlertCommand) -> None:
        """Démarre un effet (alert, warning ou info) avec logs détaillés sur les frames."""
        self._clear_override(resume_base=False, event="replaced")
        lighting = _lighting_module()
        if command.kind == "alert":
            frames = lighting.alert_frames(self.profile)
        elif command.kind == "warning":
            frames = lighting.warning_frames(self.profile)
        elif command.kind == "info":
            frames = lighting.info_frames(self.profile)
        else:
            logger.warning(f"Type d'effet inconnu: {command.kind}")
            return
        # Log détaillé sur les frames utilisées
        logger.debug(
            "Palette utilisée pour %s: %s",
            command.kind,
            [
                {"color": f"#{r:02X}{g:02X}{b:02X}", "duration": d}
                for (r, g, b), d in frames
            ]
        )
        timer = self._timer_factory(command.duration, self._complete_override, args=(command.kind,))
        timer.daemon = True
        timer.start()
        control = self.control.start_override(
            kind=command.kind,
            duration_seconds=command.duration,
            timer_handle=timer,
        )
        logger.debug("Lancement du pattern sur le contrôleur: %r", frames)
        self.controller.start_pattern(frames)
        logger.info("Effet %s démarré", command.kind, extra={"duration": command.duration})
        self.control = control

    def _complete_override(self, kind: str) -> None:
        """Appelé quand un effet se termine."""
        cleared = self._clear_override(resume_base=True, event="complete")
        if cleared:
            logger.info("Effet %s terminé", kind)
            self._publish_light_state()

    def _clear_override(self, *, resume_base: bool, event: str) -> bool:
        """Arrête l'effet en cours."""
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
        
        # Réappliquer l'état selon le mode
        if resume_base:
            if control.pilot_switch:
                # Mode pilot : appliquer la couleur du light
                if control.light_on:
                    lighting = _lighting_module()
                    lighting.reapply_cached_color(
                        self.controller,
                        control.last_command_color,
                        control.last_brightness,
                    )
                else:
                    self.controller.set_static_color((0, 0, 0))
            else:
                # Mode auto : rendre la main à Logitech
                lighting = _lighting_module()
                lighting.restore_logitech_control(self.controller)
        
        self.control = control
        logger.info("Effet %s arrêté (%s)", override.kind, event)
        return True