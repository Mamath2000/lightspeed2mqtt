---
id: control-mode
title: Control Mode
sidebar_label: ControlMode
---

# Control Mode (`lightspeed.control_mode`)

Objets principaux :

- `Mode` (Enum) — valeurs : `pilot`, `logi`, `override_alert`, `override_warning`, `override_info`.
- `OverrideAction` — description d'un override en cours (kind, durée, started_at, timer_handle) et méthodes utilitaires (`to_payload`).
- `ControlMode` — dataclass immuable décrivant l'état courant :
  - `state`: valeur `Mode`
  - `pilot_switch`: bool (pilote actif)
  - `light_on`: bool
  - `last_command_color`: RGB
  - `last_brightness`: int
  - `updated_at`: timestamp
  - `override`: optionnel `OverrideAction`

API importante :

- `ControlMode.bootstrap(default_color, pilot_switch=True, light_on=True)` — état initial.
- `record_color_command(...)`, `set_pilot_switch(...)`, `set_light_state(...)`, `start_override(...)`, `clear_override()` — méthodes immutables retournant un nouveau `ControlMode`.
- `snapshot()` — représentation sérialisable pour publication MQTT.

Règles :

- L'état effectif est dérivé via `_derive_state()` : un override l'emporte, sinon `pilot`/`logi` selon `pilot_switch`.
- Les valeurs sont validées (brightness clampé entre 0 et 255).
