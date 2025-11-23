"""Typed configuration loader for the Logitech Lightspeed middleware."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import yaml

RGB = Tuple[int, int, int]
DEFAULT_CONFIG_FILENAME = "config.yaml"
DEFAULT_TOPIC_BASE = "lightspeed/alerts"
PALETTE_DURATION_LIMITS = {"alert": 500, "warning": 350}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")
logger = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when the configuration file cannot be parsed."""


@dataclass(frozen=True)
class MqttSettings:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    client_id: str
    keepalive: int


@dataclass(frozen=True)
class TopicMap:
    base: str
    color: str
    alert: str
    warning: str
    auto: str
    status: str


@dataclass(frozen=True)
class HomeAssistantSettings:
    device_id: str
    device_name: str
    manufacturer: str
    model: str
    area: Optional[str]


@dataclass(frozen=True)
class LightingSettings:
    default_color: RGB
    auto_restore: bool
    lock_file: str


@dataclass(frozen=True)
class PaletteFrame:
    color: RGB
    duration_ms: int


@dataclass(frozen=True)
class PaletteDefinition:
    name: str
    max_duration_ms: int
    frames: Tuple[PaletteFrame, ...]


@dataclass(frozen=True)
class Palettes:
    alert: PaletteDefinition
    warning: PaletteDefinition


@dataclass(frozen=True)
class LogitechSettings:
    dll_path: Optional[str]
    profile_backup: str


@dataclass(frozen=True)
class ObservabilitySettings:
    health_topic: str
    log_level: str


@dataclass(frozen=True)
class ConfigProfile:
    source_path: Path
    mqtt: MqttSettings
    topics: TopicMap
    home_assistant: HomeAssistantSettings
    lighting: LightingSettings
    palettes: Palettes
    logitech: LogitechSettings
    observability: ObservabilitySettings

    def schema_revision(self) -> str:
        """Return a stable hash representing the configuration schema."""
        return _SCHEMA_REVISION


def load_config(path: Optional[Path | str] = None, *, env: Optional[Mapping[str, str]] = None) -> ConfigProfile:
    """Load and parse the YAML configuration file into typed dataclasses."""
    config_path = Path(path or DEFAULT_CONFIG_FILENAME)
    if not config_path.exists():
        raise ConfigError(f"Le fichier de configuration est introuvable: {config_path}")
    try:
        raw: Dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - re-raised for clarity
        raise ConfigError(f"Impossible de lire {config_path}: {exc}") from exc

    env_map = env or os.environ
    substituted = _apply_env_substitution(raw, env_map, source=config_path)

    mqtt_data = substituted.get("mqtt", {})
    topics_data = substituted.get("topics", {})
    ha_data = substituted.get("home_assistant", {})
    lighting_data = substituted.get("lighting", {})
    palettes_data = substituted.get("palettes", {})
    logitech_data = substituted.get("logitech", {})
    observability_data = substituted.get("observability", {})

    mqtt = MqttSettings(
        host=_require_str(mqtt_data, "host"),
        port=int(mqtt_data.get("port", 1883)),
        username=_optional_str(mqtt_data.get("username")),
        password=_optional_str(mqtt_data.get("password")),
        client_id=_require_str(mqtt_data, "client_id", default="lightspeed-led"),
        keepalive=int(mqtt_data.get("keepalive", 60)),
    )

    topic_base = _require_str(topics_data, "base", default=DEFAULT_TOPIC_BASE)
    topics = TopicMap(
        base=topic_base,
        color=_derive_topic(topics_data.get("color"), f"{topic_base}/color"),
        alert=_derive_topic(topics_data.get("alert"), f"{topic_base}/alert"),
        warning=_derive_topic(topics_data.get("warning"), f"{topic_base}/warning"),
        auto=_derive_topic(topics_data.get("auto"), f"{topic_base}/auto"),
        status=_derive_topic(topics_data.get("status"), f"{topic_base}/status"),
    )

    home_assistant = HomeAssistantSettings(
        device_id=_require_str(ha_data, "device_id", default="lightspeed-alerts"),
        device_name=_require_str(ha_data, "device_name", default="Lightspeed Alerts"),
        manufacturer=_require_str(ha_data, "manufacturer", default="Logitech"),
        model=_require_str(ha_data, "model", default="LED Middleware"),
        area=_optional_str(ha_data.get("area")),
    )

    lighting = LightingSettings(
        default_color=_parse_color(_require_str(lighting_data, "default_color", default="#00FF80")),
        auto_restore=bool(lighting_data.get("auto_restore", True)),
        lock_file=_require_str(lighting_data, "lock_file", default="lightspeed.lock"),
    )

    palettes = Palettes(
        alert=_parse_palette("alert", palettes_data.get("alert")),
        warning=_parse_palette("warning", palettes_data.get("warning")),
    )

    logitech = LogitechSettings(
        dll_path=_optional_str(logitech_data.get("dll_path")),
        profile_backup=_require_str(logitech_data, "profile_backup", default="backup.json"),
    )

    observability = ObservabilitySettings(
        health_topic=_require_str(
            observability_data,
            "health_topic",
            default=f"{topics.base}/health",
        ),
        log_level=_require_str(observability_data, "log_level", default="INFO"),
    )

    profile = ConfigProfile(
        source_path=config_path,
        mqtt=mqtt,
        topics=topics,
        home_assistant=home_assistant,
        lighting=lighting,
        palettes=palettes,
        logitech=logitech,
        observability=observability,
    )
    _validate_profile(profile)
    return profile


def _parse_color(value: str) -> RGB:
    text = value.strip()
    if not text.startswith("#") or len(text) != 7:
        raise ConfigError(f"Couleur invalide: {value}")
    try:
        r = int(text[1:3], 16)
        g = int(text[3:5], 16)
        b = int(text[5:7], 16)
    except ValueError as exc:  # pragma: no cover - ValueError indicates invalid hex
        raise ConfigError(f"Couleur invalide: {value}") from exc
    return (r, g, b)


def _parse_palette(name: str, data: Optional[Mapping[str, Any]]) -> PaletteDefinition:
    limit = PALETTE_DURATION_LIMITS.get(name, 500)
    if not data:
        frames = _default_frames(name)
        return PaletteDefinition(name=name, max_duration_ms=limit, frames=frames)

    max_duration = int(data.get("max_duration_ms", limit))
    if max_duration > limit:
        raise ConfigError(
            f"{name} max_duration_ms ({max_duration}) dépasse la limite {limit} imposée par le principe IV"
        )
    raw_frames = data.get("frames", [])
    frames = []
    for frame in raw_frames:
        color_value = frame.get("color")
        duration_value = frame.get("duration_ms")
        if color_value is None or duration_value is None:
            raise ConfigError(f"Frame incomplet pour {name}")
        duration = int(duration_value)
        if duration <= 0:
            raise ConfigError(f"Une frame {name} possède une durée <= 0 ms")
        if duration > max_duration:
            raise ConfigError(
                f"Une frame {name} dépasse la durée max ({duration}>{max_duration})"
            )
        frames.append(PaletteFrame(color=_parse_color(str(color_value)), duration_ms=duration))

    if not frames:
        frames = list(_default_frames(name))

    return PaletteDefinition(name=name, max_duration_ms=max_duration, frames=tuple(frames))


def _default_frames(name: str) -> Tuple[PaletteFrame, ...]:
    if name == "alert":
        return (
            PaletteFrame((255, 0, 0), 150),
            PaletteFrame((255, 255, 255), 150),
            PaletteFrame((0, 0, 0), 150),
        )
    return (
        PaletteFrame((255, 140, 0), 200),
        PaletteFrame((0, 0, 0), 200),
    )


def _require_str(section: Mapping[str, Any], key: str, *, default: Optional[str] = None) -> str:
    value = section.get(key)
    if value is None:
        if default is None:
            raise ConfigError(f"Clé obligatoire manquante: {key}")
        return default
    if isinstance(value, str):
        text = value.strip()
        return text or (default or text)
    return str(value)


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _derive_topic(value: Optional[str], fallback: str) -> str:
    text = (value or "").strip()
    return text or fallback


def _apply_env_substitution(data: Any, env: Mapping[str, str], *, source: Path) -> Dict[str, Any]:
    missing: set[str] = set()

    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, str):
            def _repl(match: re.Match[str]) -> str:
                key = match.group(1)
                if key in env:
                    return env[key]
                missing.add(key)
                return ""

            return ENV_PATTERN.sub(_repl, value)
        return value

    substituted = replace(data)
    if missing:
        logger.warning(
            "Variables d'environnement manquantes dans %s: %s",
            source,
            ", ".join(sorted(missing)),
        )
    if not isinstance(substituted, dict):
        raise ConfigError("Le fichier de configuration doit contenir un objet YAML en racine")
    return substituted


def _validate_profile(profile: ConfigProfile) -> None:
    if not 1 <= profile.mqtt.port <= 65535:
        raise ConfigError("Le port MQTT doit être compris entre 1 et 65535")
    if profile.mqtt.keepalive <= 0:
        raise ConfigError("Le keepalive MQTT doit être strictement positif")

    for topic in (profile.topics.base, profile.topics.color, profile.topics.alert,
                  profile.topics.warning, profile.topics.auto, profile.topics.status):
        if not topic or " " in topic:
            raise ConfigError("Les topics MQTT ne doivent pas être vides ni contenir d'espaces")

    if profile.observability.log_level.upper() not in ALLOWED_LOG_LEVELS:
        raise ConfigError(
            f"Niveau de log invalide: {profile.observability.log_level}. Attendu: {sorted(ALLOWED_LOG_LEVELS)}"
        )

    for palette in (profile.palettes.alert, profile.palettes.warning):
        if not palette.frames:
            raise ConfigError(f"Le palette {palette.name} doit contenir au moins une frame")
        limit = PALETTE_DURATION_LIMITS.get(palette.name, palette.max_duration_ms)
        if palette.max_duration_ms > limit:
            raise ConfigError(
                f"La durée max {palette.max_duration_ms}ms dépasse la limite autorisée ({limit}ms) pour {palette.name}"
            )
        for frame in palette.frames:
            if frame.duration_ms <= 0:
                raise ConfigError(f"Une frame {palette.name} possède une durée <= 0 ms")
            if frame.duration_ms > palette.max_duration_ms:
                raise ConfigError(
                    f"Une frame {palette.name} dépasse la durée max ({frame.duration_ms}>{palette.max_duration_ms})"
                )

    if any(channel < 0 or channel > 255 for channel in profile.lighting.default_color):
        raise ConfigError("Les composantes RGB doivent être comprises entre 0 et 255")


def _field_names(cls, exclude: Optional[set[str]] = None) -> Tuple[str, ...]:
    excluded = exclude or set()
    return tuple(field.name for field in fields(cls) if field.name not in excluded)


def _compute_schema_revision() -> str:
    blueprint = {
        "ConfigProfile": _field_names(ConfigProfile, exclude={"source_path"}),
        "MqttSettings": _field_names(MqttSettings),
        "TopicMap": _field_names(TopicMap),
        "HomeAssistantSettings": _field_names(HomeAssistantSettings),
        "LightingSettings": _field_names(LightingSettings),
        "PaletteDefinition": _field_names(PaletteDefinition),
        "PaletteFrame": _field_names(PaletteFrame),
        "LogitechSettings": _field_names(LogitechSettings),
        "ObservabilitySettings": _field_names(ObservabilitySettings),
    }
    payload = json.dumps(blueprint, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


_SCHEMA_REVISION = _compute_schema_revision()
