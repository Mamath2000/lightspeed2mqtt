---
id: introduction
title: Vue d'ensemble
sidebar_label: Introduction
---

# lightspeed2mqtt — Vue d'ensemble

Ce dépôt contient un petit middleware qui expose le rétroéclairage Logitech via MQTT et s'intègre à Home Assistant.

Composants principaux :

- Service MQTT : orchestre les commandes, publie l'état retained, gère les discovery Home Assistant.
- Contrôleur Logitech : wrapper autour du SDK Logitech (DLL), applique des couleurs et patterns.
- Gestion de configuration : charge `config.yaml` en `ConfigProfile` typé.
- Observabilité : payloads de santé et mécanisme LWT (online/offline).

Architecture (simplifiée) :

- `simple-logi.py` — point d'entrée CLI / mode `serve` lance le service.
- `lightspeed.mqtt.MqttLightingService` — connecte au broker, abonne et traite les commandes.
- `lightspeed.lighting.LightingController` — interface avec la DLL Logitech.
- `lightspeed.control_mode.ControlMode` — état et overrides (alert/warning/info).
- `lightspeed.ha_contracts` — génération des payloads Home Assistant discovery.

Voir les pages modules pour la documentation technique détaillée :

- Modules :
  - [Configuration](./modules/configuration)
  - [MQTT & Service](./modules/mqtt-service)
  - [Lighting / SDK](./modules/lighting)
  - [Observability](./modules/observability)
  - [Control Mode](./modules/control-mode)
  - [Home Assistant (HA) discovery](./modules/ha-contracts)
  - [CLI (simple-logi)](./modules/cli)
