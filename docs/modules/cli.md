---
id: cli
title: CLI & Entrypoint
sidebar_label: CLI
---

# CLI (`simple-logi.py`)

`simple-logi.py` est le point d'entrée principal et expose plusieurs sous-commandes :

- `serve` (par défaut) — lance le service MQTT et le contrôleur Logitech.
- `validate-config` — charge et valide la configuration.
- `color <value>` — applique une couleur et garde le contrôle (`#RRGGBB`, `R,G,B` ou JSON).
- `alert` / `warning` — lance les patterns d'alerte définis dans les palettes.
- `auto` — rend la main immédiatement à Logitech.

Fonctionnalités notables :

- `_read_retained_state(profile, logger, timeout)` : lit le `state_topic` retained au démarrage via un client bootstrap pour restaurer l'état précédent.
- `resolve_config_path()` : logique CLI > env (`LOGI_CONFIG_PATH`) > default `config.yaml`.
- `--config <path>` : option CLI pour spécifier un fichier de configuration.

Debugging :

- Pour pas-à-pas distant, ajouter un guard `debugpy` (voir `docs/usage.md`).

Exemple d'exécution :

```bash
python simple-logi.py serve --config ./config.yaml
```
