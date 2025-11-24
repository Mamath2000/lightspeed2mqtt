# Changelog

## [Unreleased] – 2025-11-25

### Added

- Pilot switch discovery + retained state plumbing (`lightspeed/ha_contracts.py`, `lightspeed/mqtt.py`) so users can déterministiquement rendre ou reprendre la main depuis Home Assistant.
- Temporary Alert/Warning overrides with configurable timers and cancellation semantics, including structured status logs (`lightspeed/mqtt.py`, `lightspeed/observability.py`).
- Canonical `config.yaml` loader with schema hashing, validation helpers, and env substitution (`lightspeed/config.py`).
- `config.example.yaml` template plus doc sync tooling/tests to keep README + Quickstart snippets aligned.
- `validate-config` CLI command wired into `simple-logi.py` and automated via CI (`.github/workflows/config-validation.yml`).
- Manual verification log (`docs/validation/manual-verification.md`) capturing the validation run and on-host checklist.

### Changed

- README, Quickstarts, and manual verification docs now explain Pilot switch workflows, cached color semantics, override duration tuning, and validation steps.
- MQTT status payloads include `pilot_switch`, `light_state`, `mode`, and override reasons for easier troubleshooting après chaque transition.
- CLI argument parsing now honors `python simple-logi.py <commande> --config chemin.yaml` by normalisant le flag global avant parsing.
- MQTT service defers Logitech SDK imports so validation tooling and CI can run sans `LogitechLed.dll`.
- README / Quickstart reference the validated copy/validate/start workflow shared avec `config.example.yaml`.

### Operator Actions

1. Copier `config.example.yaml` vers `config.yaml` et renseigner vos topics/métadonnées.
2. Définir les secrets via variables d'environnement (ex. `${MQTT_PASSWORD}`).
3. Lancer `python simple-logi.py validate-config --config config.yaml` : la commande doit retourner `0` avant tout démarrage.
4. Démarrer `python simple-logi.py serve --config config.yaml` et vérifier dans Home Assistant qu'un seul device « Lightspeed Alerts » apparaît avec les entités attendues.
5. Basculez le switch Pilot ON/OFF puis la Light ON/OFF : Logitech doit reprendre la main pendant OFF et la couleur précédente doit revenir instantanément pendant ON.
6. Déclenchez Alert/Warning pour confirmer que les overrides durent `effects.override_duration_seconds` (ou la valeur envoyée) puis reviennent bien à l'état précédent.
7. Surveillez `lightspeed/alerts/status` (online/offline) et `lightspeed/alerts/health` pour confirmer la prise en compte de la configuration active.

### CI/CD

- Nouvelle vérification GitHub Actions (`config-validation.yml`) exécutant `pytest -k config` puis `python simple-logi.py validate-config --config config.example.yaml` sur chaque Pull Request.
