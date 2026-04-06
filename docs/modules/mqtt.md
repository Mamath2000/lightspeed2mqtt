---
id: mqtt-service
title: MQTT & Service
sidebar_label: MQTT Service
---

# MQTT & Service (`lightspeed.mqtt`)

Composant principal : `MqttLightingService`

Responsabilités :

- Se connecter au broker MQTT et maintenir la boucle réseau.
- S'abonner aux topics de commande (switch, rgb, brightness, mode, alert, warn, info).
- Publier l'état complet de la lumière (`state_topic`) en retained.
- Publier la découverte Home Assistant (via `lightspeed.ha_contracts.iter_discovery_messages`).
- Gérer les overrides (alert/warning/info) et lancer les patterns correspondants.
- Publier la disponibilité (LWT) via `publish_availability` (utilise `topics.lwt`).

Points d'entrée importants :

- `start()` : initialise le controller Logitech, restaure l'état initial si besoin, connecte le client MQTT, démarre la boucle.
- `loop_forever()` : boucle d'attente principale; à l'arrêt publie `offline` si connecté et se déconnecte proprement.
- `on_connect()` : abonne aux topics, publie `online` (via `_publish_availability`), publie l'état et discovery.
- `on_message()` : routage des messages entrants vers les handlers `_handle_*`.

Handlers :

- `_handle_switch_command(payload)` — on/off
- `_handle_rgb_command(payload)` — couleur (parse JSON, list, #hex ou "R,G,B")
- `_handle_brightness_command(payload)` — luminosité (int 0-255 ou JSON)
- `_handle_mode_command(payload)` — changement pilot/auto
- `_handle_alert_button()`, `_handle_warn_button()`, `_handle_info_button()` — déclenchent des overrides

Notes opérationnelles :

- Le service lit l'état retained (`state_topic`) au démarrage via le bootstrap (dans `simple-logi.py`) et peut réappliquer l'état.
- Le LWT est configuré via `lightspeed.observability.configure_last_will()` (payload `offline` en retained).
- Les messages d'état publiés sont JSON compressés (séparateurs `(',', ':')`) pour réduire la taille.

Voir aussi :
- [Home Assistant discovery](./ha_contracts)
- [Observability / LWT](./observability)
