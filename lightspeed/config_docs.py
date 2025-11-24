"""Shared helpers to keep configuration documentation in sync."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FieldDoc:
    key: str
    description: str
    example: str


def _docs() -> Sequence[FieldDoc]:
    return (
        FieldDoc("mqtt.host", "Adresse/IP du broker MQTT", "localhost"),
        FieldDoc("mqtt.port", "Port TCP utilisé par le broker", "1883"),
        FieldDoc("mqtt.username", "Identifiant optionnel", "admin"),
        FieldDoc("mqtt.password", "Secret ou référence ${ENV}", "${MQTT_PASSWORD}"),
        FieldDoc("mqtt.client_id", "Nom unique du client MQTT", "lightspeed-led"),
        FieldDoc("mqtt.keepalive", "Intervalle keepalive en secondes", "60"),
        FieldDoc("topics.base", "Préfixe commun pour tous les topics", "lightspeed/alerts"),
        FieldDoc("topics.color", "Topic pour les commandes de couleur", "<base>/color"),
        FieldDoc("topics.alert", "Topic pour déclencher le pattern alerte", "<base>/alert"),
        FieldDoc("topics.warning", "Topic pour déclencher le pattern warning", "<base>/warning"),
        FieldDoc("topics.auto", "Topic pour rendre la main à Logitech", "<base>/auto"),
        FieldDoc("topics.auto_state", "Topic retained exposant l'état du switch piloté", "<base>/auto/state"),
        FieldDoc("topics.status", "Topic retained online/offline", "<base>/status"),
        FieldDoc("home_assistant.device_id", "Identifiant unique Home Assistant", "lightspeed-alerts"),
        FieldDoc("home_assistant.device_name", "Nom présenté dans HA", "Logitech Alerts"),
        FieldDoc("home_assistant.manufacturer", "Fabricant affiché", "Logitech"),
        FieldDoc("home_assistant.model", "Modèle affiché", "LED Middleware"),
        FieldDoc("home_assistant.area", "Zone HA optionnelle", "Bureau"),
        FieldDoc("lighting.default_color", "Couleur appliquée au démarrage", "#00FF80"),
        FieldDoc("lighting.auto_restore", "Restaure le profil Logitech en mode auto", "true"),
        FieldDoc("lighting.lock_file", "Verrou pour éviter les accès concurrents", "lightspeed.lock"),
        FieldDoc(
            "effects.override_duration_seconds",
            "Durée des overrides Alert/Warning (1-300s)",
            "10",
        ),
        FieldDoc("palettes.alert.max_duration_ms", "Durée max (Principe IV)", "500"),
        FieldDoc("palettes.warning.max_duration_ms", "Durée max warning", "350"),
        FieldDoc("logitech.dll_path", "Chemin personnalisé vers LogitechLed.dll", ""),
        FieldDoc("logitech.profile_backup", "Sauvegarde du profil initial", "backup.json"),
        FieldDoc("observability.health_topic", "Topic JSON de santé retenu", "<base>/health"),
        FieldDoc("observability.log_level", "Niveau de logs", "INFO"),
    )


def render_config_field_table() -> str:
    lines = [
        "| Clé YAML | Description | Exemple |",
        "|-----------|-------------|---------|",
    ]
    for row in _docs():
        example = f"`{row.example}`" if row.example else ""
        lines.append(f"| `{row.key}` | {row.description} | {example} |")
    return "\n".join(lines)