---
id: configuration
title: Configuration
sidebar_label: Configuration
---

# Configuration (`config.yaml`)

La configuration est chargée par `lightspeed.config.load_config()` et transformée en `ConfigProfile`.

Principaux blocs et objets :

- `mqtt`: paramètres MQTT (
  - `host`, `port`, `username`, `password`, `client_id`, `keepalive`
  )
- `topics`: cartographie des topics utilisés par le service. Le champ `base` est le préfixe commun; les autres topics sont dérivés de `base`.
  - Exemples : `state_topic`, `command_topic`, `rgb_command_topic`, `brightness_command_topic`, `mode_command_topic`, `alert_command_topic`, `warn_command_topic`, `info_command_topic`, `lwt`.
- `home_assistant`: métadonnées pour la génération des payloads discovery (device_id, device_name, manufacturer, model, area).
- `lighting`: paramètres pour le contrôleur Logitech (couleur par défaut, `auto_restore`, `lock_file`).
- `effects`: `override_duration_seconds` pour alert/warning/info.
- `palettes`: définitions des palettes (alert, warning, info).
- `logitech`: `dll_path` et `profile_backup`.
- `observability`: `log_level` et éventuel `health_topic`.

Validations importantes (dans `lightspeed.config._validate_profile`):

- Ports MQTT valides et `keepalive` positif.
- Topics non vides sans espaces.
- Palettes avec frames valides et respectant les durées max (principe IV).
- Composantes RGB entre 0 et 255.

Fichiers utiles :

- Exemple : [config.example.yaml](../config.example.yaml)
- Charger/valider : `python simple-logi.py validate-config`
