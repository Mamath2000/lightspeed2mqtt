"""CLI entrypoint for the Logitech LED middleware."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Mapping, Optional, Sequence, Tuple

from lightspeed.config import ConfigError, ConfigProfile, load_config
from lightspeed.observability import configure_logging

try:
    from lightspeed.mqtt import MqttLightingService
except ImportError as exc:  # pragma: no cover - dependency guard
    if "paho" in str(exc).lower():
        print("Le module 'paho-mqtt' est requis. Installez-le avec: pip install -r requirements.txt")
        sys.exit(1)
    raise

try:
    import paho.mqtt.client as bootstrap_mqtt
except ImportError as exc:  # pragma: no cover - dependency guard
    if "paho" in str(exc).lower():
        print("Le module 'paho-mqtt' est requis. Installez-le avec: pip install -r requirements.txt")
        sys.exit(1)
    raise


RGB = Tuple[int, int, int]
PatternFrame = Tuple[RGB, float]
_LIGHTING_MODULE: ModuleType | None = None


def _lighting_module() -> ModuleType:
    """Import lazily to avoid requiring the Logitech SDK for validate-config."""
    global _LIGHTING_MODULE
    if _LIGHTING_MODULE is None:
        from lightspeed import lighting as lighting_module  # Local import to defer logipy load

        _LIGHTING_MODULE = lighting_module
    return _LIGHTING_MODULE


def resolve_config_path(cli_value: str | None, env: Mapping[str, str]) -> Path:
    """Return the config path honoring CLI > env > default precedence."""
    if cli_value and cli_value.strip():
        return Path(cli_value).expanduser().resolve()
    if env_value := env.get("LOGI_CONFIG_PATH"):
        return Path(env_value).expanduser().resolve()
    return Path("config.yaml").resolve()


def _normalize_global_args(argv: Sequence[str]) -> list[str]:
    """Ensure global flags like --config appear before subcommands."""
    config_tokens: list[str] = []
    other_tokens: list[str] = []
    skip_next = False
    for index, token in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if token == "--config":
            config_tokens.append(token)
            if index + 1 < len(argv):
                config_tokens.append(argv[index + 1])
                skip_next = True
            continue
        if token.startswith("--config="):
            config_tokens.append(token)
            continue
        other_tokens.append(token)
    return config_tokens + other_tokens


def wait_loop(duration: float) -> None:
    if duration > 0:
        time.sleep(duration)
    else:
        print('Ctrl+C pour arrêter…')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def run_cli_color(profile: ConfigProfile, value: str, duration: float) -> None:
    lighting = _lighting_module()
    controller = lighting.LightingController(
        profile.logitech.dll_path,
        lock_file=profile.lighting.lock_file,
    )
    try:
        controller.set_static_color(lighting.parse_color_string(value))
        wait_loop(duration)
    finally:
        controller.shutdown()


def run_cli_pattern(profile: ConfigProfile, frames: Sequence[PatternFrame], duration: float) -> None:
    lighting = _lighting_module()
    controller = lighting.LightingController(
        profile.logitech.dll_path,
        lock_file=profile.lighting.lock_file,
    )
    try:
        controller.start_pattern(frames)
        wait_loop(duration)
    finally:
        controller.shutdown()


def run_cli_auto(profile: ConfigProfile) -> None:
    lighting = _lighting_module()
    controller = lighting.LightingController(
        profile.logitech.dll_path,
        lock_file=profile.lighting.lock_file,
    )
    try:
        controller.start()
        controller.release()
    finally:
        controller.shutdown()


def _pilot_state_topic(profile: ConfigProfile) -> str:
    legacy = getattr(profile.topics, "auto_state", None)
    if legacy:
        return legacy
    return profile.topics.mode_state


def _read_pilot_switch_state(
    profile: ConfigProfile,
    *,
    logger: logging.Logger,
    timeout: float = 2.0,
) -> Optional[bool]:
    """Return retained pilot switch state if broker exposes it, else None."""

    event = threading.Event()
    state: dict[str, Optional[str]] = {"value": None}

    client = bootstrap_mqtt.Client(
        client_id=f"{profile.mqtt.client_id}-bootstrap",
        clean_session=True,
    )
    if profile.mqtt.username:
        client.username_pw_set(profile.mqtt.username, profile.mqtt.password or None)

    def _on_connect(mqtt_client, _userdata, _flags, rc):
        if rc != 0:
            logger.warning("Connexion bootstrap pilot échouée", extra={"code": rc})
            event.set()
            return
        mqtt_client.subscribe(_pilot_state_topic(profile), qos=1)

    def _on_message(_mqtt_client, _userdata, message):
        state["value"] = message.payload.decode("utf-8", errors="ignore").strip().upper()
        event.set()

    client.on_connect = _on_connect
    client.on_message = _on_message

    try:
        client.connect(profile.mqtt.host, profile.mqtt.port, keepalive=profile.mqtt.keepalive)
        client.loop_start()
        event.wait(timeout)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Lecture pilot switch impossible", extra={"error": str(exc)})
        return None
    finally:
        client.loop_stop()
        client.disconnect()

    value = state["value"]
    if value in {"ON", "OFF"}:
        return value == "ON"
    return None


def run_validate_command(config_path: Path) -> int:
    try:
        profile = load_config(config_path)
    except ConfigError as exc:
        print("❌ Config invalide")
        print(f"  • Fichier : {config_path}")
        print(f"  • Raison  : {exc}")
        return 1
    timestamp = datetime.now(timezone.utc).isoformat()
    print("✅ Config valide")
    print(f"  • Fichier : {config_path}")
    print(f"  • Schéma  : {profile.schema_revision()}")
    print(f"  • Validée : {timestamp}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description='Middleware Logitech LED contrôlé par MQTT')
    parser.add_argument(
        '--config',
        default=None,
        help="Chemin du fichier config.yaml (défaut: --config ou LOGI_CONFIG_PATH ou config.yaml)",
    )
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('serve', help='Lance le service MQTT (par défaut)')
    subparsers.add_parser('validate-config', help='Valide le fichier config sans lancer MQTT/SDK')

    color_parser = subparsers.add_parser('color', help='Applique une couleur et garde le contrôle')
    color_parser.add_argument('value', help='#RRGGBB ou R,G,B')
    color_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    alert_parser = subparsers.add_parser('alert', help='Pattern alerte basé sur le fichier config.yaml')
    alert_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    warning_parser = subparsers.add_parser('warning', help='Pattern warning basé sur le fichier config.yaml')
    warning_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    subparsers.add_parser('auto', help='Rend la main immédiatement')

    normalized_args = _normalize_global_args(sys.argv[1:])
    args = parser.parse_args(normalized_args)
    config_path = resolve_config_path(args.config, os.environ)
    command = args.command or 'serve'

    if command == 'validate-config':
        sys.exit(run_validate_command(config_path))

    profile = load_config(config_path)
    configure_logging(profile.observability.log_level)
    logger = logging.getLogger('lightspeed.app')
    validated_at = datetime.now(timezone.utc)
    logger.info(
        "Configuration chargée",
        extra={
            'config_path': str(profile.source_path),
            'schema_revision': profile.schema_revision(),
        },
    )
    if command == 'serve':
        lighting = _lighting_module()
        service = MqttLightingService(
            lighting.LightingController(
                profile.logitech.dll_path,
                lock_file=profile.lighting.lock_file,
            ),
            profile,
            validated_at=validated_at,
        )
        bootstrap_state = _read_pilot_switch_state(profile, logger=logger)
        if bootstrap_state is not None:
            service.bootstrap_pilot_switch(bootstrap_state)
            logger.info(
                "État pilot initialisé",
                extra={"pilot_switch": "ON" if bootstrap_state else "OFF"},
            )
        else:
            logger.info("Aucun état pilot retenu détecté", extra={"topic": _pilot_state_topic(profile)})
        try:
            service.start()
            service.loop_forever()
        except KeyboardInterrupt:
            logger.info('Arrêt demandé par l\'utilisateur.')
        finally:
            service.stop()
    elif command == 'color':
        run_cli_color(profile, args.value, args.duration)
    elif command == 'alert':
        lighting = _lighting_module()
        run_cli_pattern(profile, lighting.alert_frames(profile), args.duration)
    elif command == 'warning':
        lighting = _lighting_module()
        run_cli_pattern(profile, lighting.warning_frames(profile), args.duration)
    elif command == 'auto':
        run_cli_auto(profile)
    else:
        parser.error(f'Commande inconnue: {command}')


if __name__ == '__main__':
    main()
