---
id: observability
title: Observabilité & Payloads
sidebar_label: Observabilité
---

# Observabilité (`lightspeed.observability`)

Fonctions principales :

- `configure_logging(level)` — configure le logger racine et limite le niveau de `paho.mqtt.client`.
- `build_status_payload(control, state, reason)` — construit le JSON retained publié sur `topics.status` (ou `topics.state` selon la config).
- `build_health_payload(profile, status, validated_at, validation_status, last_error)` — payload de santé détaillé.
- `configure_last_will(client, profile)` — configure la Last Will (`topics.lwt`, payload `offline`, `retain=True`, `qos=1`).
- `publish_status(...)`, `publish_health(...)`, `publish_availability(client, profile, state)` — fonctions utilitaires pour publier les payloads adéquats.

LWT / Disponibilité :

- Le Will est configuré pour publier `offline` (retraité) en cas de départ inattendu.
- À la connexion (`on_connect`) le service publie explicitement `online` sur `topics.lwt` pour indiquer la disponibilité (publique retenue).

Format des payloads : JSON compacts (séparateurs `(',', ':')`) contenant état, mode, timestamps ISO UTC et métadonnées.

Conseil : surveiller `topics.lwt` et `topics.state` pour vérifier la santé du service.
