---
id: ha-contracts
title: Home Assistant Discovery
sidebar_label: HA Discovery
---

# Home Assistant Discovery (`lightspeed.ha_contracts`)

- Fournit `iter_discovery_messages(profile)` qui retourne une liste de `DiscoveryMessage` à publier sur le broker pour permettre l'autodiscovery Home Assistant.
- Le topic de discovery est construit à partir de `homeassistant/device/<device_id>/config`.
- Le payload contient :
  - `device` : métadonnées (identifiers, name, manufacturer, model, sw_version)
  - `components` : description des entités exposées (light, binary_sensor, switch, button...)
  - `availability` : configuré pour utiliser `topics.lwt` (`payload_available: 'online'`, `payload_not_available: 'offline'`).

Remarque : la discovery fait référence au topic LWT (disponibilité) — assurez-vous que `topics.lwt` est correctement défini dans `config.yaml`.
