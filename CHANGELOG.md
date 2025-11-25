# Changelog

## [Unreleased] – 2025-11-25

### Added

- Base-relative topic schema: all runtime components now derive `power/mode/color/brightness/alert/status/lwt` from `topics.base`, eliminating manual concatenation and ensuring configuration + discovery stay aligned (`lightspeed/config.py`, `lightspeed/mqtt.py`, `lightspeed/ha_contracts.py`).
- MQTT availability handling: the client configures a retained Last Will on `<base>/lwt` and republishes `online`/`offline` alongside structured status health (`lightspeed/observability.py`, `lightspeed/mqtt.py`).
- JSON alert contract enforcement: alert/warning/info payloads must be JSON with optional bounded `duration`, and overrides now expose their lifecycle via `topics.status` (`lightspeed/mqtt.py`).
- Pilot switch discovery + retained state plumbing (`lightspeed/ha_contracts.py`, `lightspeed/mqtt.py`) so users can déterministiquement rendre ou reprendre la main depuis Home Assistant.
- Temporary Alert/Warning overrides with configurable timers and cancellation semantics, including structured status logs (`lightspeed/mqtt.py`, `lightspeed/observability.py`).
- Canonical `config.yaml` loader with schema hashing, validation helpers, and env substitution (`lightspeed/config.py`).
- `config.example.yaml` template plus doc sync tooling/tests to keep README + Quickstart snippets aligned.
- `validate-config` CLI command wired into `simple-logi.py` and automated via CI (`.github/workflows/config-validation.yml`).
- Manual verification log (`docs/validation/manual-verification.md`) capturing the validation run and on-host checklist.

### Changed

- README, Quickstarts, and manual verification docs maintenant décrivent le catalogue de topics canoniques, le workflow pilot/logi, les scripts MQTT (`mode`, `alert`, `status`, `lwt`) et les étapes de validation terrain.
- MQTT status payloads include `pilot_switch`, `light_state`, `mode`, and override reasons for easier troubleshooting après chaque transition.
- CLI argument parsing now honors `python simple-logi.py <commande> --config chemin.yaml` by normalisant le flag global avant parsing.
- MQTT service defers Logitech SDK imports so validation tooling and CI can run sans `LogitechLed.dll`.
- README / Quickstart reference the validated copy/validate/start workflow shared avec `config.example.yaml`.

### Operator Actions

1. Copier `config.example.yaml` vers `config.yaml`, renseigner `mqtt.*`, définir `topics.base`, et conserver les suffixes relatifs.
2. Exporter les secrets (ex. `${MQTT_PASSWORD}`) puis exécuter `python simple-logi.py validate-config --config config.yaml`. Corriger toute erreur de suffixe ou de durée avant de continuer.
3. Démarrer `python simple-logi.py serve --config config.yaml` et vérifier que `<base>/lwt` passe à `online` et que Home Assistant découvre les entités (switch Power, switch Mode, boutons Alert/Warning/Info, capteurs Status/LWT).
4. Publier `pilot`/`logi` sur `<base>/mode` (ou utiliser le switch HA) pour vérifier que la couleur retenue est rejouée et que `<base>/mode/state` reflète l'état.
5. Envoyer des commandes couleur/brightness sur `<base>/color` / `<base>/brightness` : le service doit republier les miroirs `/state` et maintenir `power=ON`.
6. Déclencher des overrides JSON sur `<base>/alert` (`{"type":"alert","duration":15}`) et confirmer que `topics.status` journalise `override_alert` puis revient à `pilot`. Tester un payload invalide pour observer le warning sans override.
7. Tuer le processus pour vérifier que l'ultime message du broker est `offline` sur `<base>/lwt`, puis relancer `serve` pour republier `online`.

### CI/CD

- Nouvelle vérification GitHub Actions (`config-validation.yml`) exécutant `pytest -k config` puis `python simple-logi.py validate-config --config config.example.yaml` sur chaque Pull Request.
