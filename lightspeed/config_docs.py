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
        FieldDoc("topics.power", "Suffixe ON/OFF retenu pour l'ownership", "<base>/power"),
        FieldDoc("topics.power_state", "Miroir retained confirmant le dernier payload ON/OFF", "<topics.power>/state"),
        FieldDoc("topics.mode", "Commande retenue pilot/logi pour prendre la main", "<base>/mode"),
        FieldDoc("topics.mode_state", "Miroir retained pour refléter le mode actif", "<topics.mode>/state"),
        FieldDoc("topics.color", "Commandes RGB (#RRGGBB, R,G,B ou JSON {r,g,b})", "<base>/color"),
        FieldDoc("topics.color_state", "Miroir retained de la dernière couleur acceptée", "<topics.color>/state"),
        FieldDoc("topics.brightness", "Commande 0-100 (implique power=ON)", "<base>/brightness"),
        FieldDoc("topics.brightness_state", "Miroir retained de la luminosité", "<topics.brightness>/state"),
        FieldDoc("topics.alert", "Sujet JSON pour alert/warning/info (non retained)", "<base>/alert"),
        FieldDoc("topics.status", "JSON retained online/offline + attributs", "<base>/status"),
        FieldDoc("topics.lwt", "Disponibilité MQTT publish/Last Will online/offline", "<base>/lwt"),
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
        FieldDoc("observability.health_topic", "Topic JSON de santé retenu", "<topics.status>"),
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