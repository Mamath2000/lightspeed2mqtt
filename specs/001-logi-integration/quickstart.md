# Quickstart – Home Assistant MQTT Integration

## 1. Prerequisites

- Windows 10/11 workstation with Logitech G HUB (or LGS) and `LogitechLed.dll` placed next to `simple-logi.py`.
- Python 3.13 with virtual environment activated (`.venv\\Scripts\\activate`).
- MQTT broker credentials (host, port, optional username/password) and Home Assistant configured to listen on the same broker.
- Dépendances Python installées via `pip install -r requirements.txt` (`logipy`, `paho-mqtt`, `pyyaml`).

## 2. Configure `config.yaml`

1. Copy the template: `Copy-Item config.example.yaml config.yaml`.
2. Update MQTT credentials, Home Assistant metadata, and optional palette/logitech overrides. You can keep `${MQTT_PASSWORD}` to pull the secret from the environment.
3. Validate the file without starting MQTT/Logitech:

     ```pwsh
     python simple-logi.py validate-config --config config.yaml
     ```

4. Commit to a path strategy: either pass `--config` everywhere or set `LOGI_CONFIG_PATH` so every command picks the same file (flag overrides the env var).

### Example & Reference

<!-- config-example:start -->
```yaml
# Exemple de configuration Logitech Alerts
# Copiez ce fichier vers config.yaml puis remplacez les valeurs ci-dessous.
# Toutes les clés doivent rester présentes pour que la validation réussisse.

mqtt:
  host: localhost # Hôte / IP du broker
  port: 1883 # Port TCP (1883 sans TLS)
  username: "" # Identifiant optionnel
  password: "${MQTT_PASSWORD}" # Secret optionnel (peut référencer une variable d'environnement)
  client_id: lightspeed-led # Nom du client MQTT
  keepalive: 60 # Intervalle keepalive en secondes

topics:
  base: lightspeed/alerts # Préfixe commun pour toutes les entités HA
  power: "" # Laisser vide pour dériver <base>/power (payload ON/OFF retenu)
  power_state: "" # Retained miroir (défaut = <topics.power>/state)
  mode: "" # Laisser vide pour dériver <base>/mode (payload pilot/logi)
  mode_state: "" # Retained miroir du mode
  color: "" # Commandes RGB dérivées (<base>/color)
  color_state: "" # Retained couleur (<topics.color>/state)
  brightness: "" # Commandes 0-100 dérivées (<base>/brightness)
  brightness_state: "" # Retained luminosité (<topics.brightness>/state)
  alert: "" # Overrides JSON (type/duration) dérivés (<base>/alert)
  status: "" # Sujet JSON retained (<base>/status)
  lwt: "" # Sujet availability online/offline (<base>/lwt)

home_assistant:
  device_id: lightspeed-alerts
  device_name: "Logitech Alerts"
  manufacturer: "Logitech"
  model: "LED Middleware"
  area: "" # Nom d'aire HA optionnel

lighting:
  default_color: "#00FF80"
  auto_restore: true # Restaure le profil Logitech lors d'un `auto`
  lock_file: "lightspeed.lock" # Verrou pour éviter les accès concurrents

effects:
  override_duration_seconds: 10 # Durée Alert/Warning en secondes (entre 1 et 300)

palettes:
  alert:
    max_duration_ms: 500 # Ne jamais dépasser 500 ms (Principe IV)
    frames:
    - color: "#FF0000"
      duration_ms: 150
    - color: "#FFFFFF"
      duration_ms: 150
    - color: "#000000"
      duration_ms: 150
  warning:
    max_duration_ms: 350
    frames:
    - color: "#FF8C00"
      duration_ms: 150
    - color: "#000000"
      duration_ms: 150

logitech:
  dll_path: "" # Chemin personnalisé vers LogitechLed.dll (laisser vide pour auto)
  profile_backup: "backup.json" # Fichier où stocker l'état initial

observability:
  health_topic: "" # Laisser vide pour réutiliser <topics.status>
  log_level: "INFO"
```
<!-- config-example:end -->

<!-- config-table:start -->
| Clé YAML | Description | Exemple |
|-----------|-------------|---------|
| `mqtt.host` | Adresse/IP du broker MQTT | `localhost` |
| `mqtt.port` | Port TCP utilisé par le broker | `1883` |
| `mqtt.username` | Identifiant optionnel | `admin` |
| `mqtt.password` | Secret ou référence ${ENV} | `${MQTT_PASSWORD}` |
| `mqtt.client_id` | Nom unique du client MQTT | `lightspeed-led` |
| `mqtt.keepalive` | Intervalle keepalive en secondes | `60` |
| `topics.base` | Préfixe commun pour tous les topics | `lightspeed/alerts` |
| `topics.power` | Suffixe ON/OFF retenu pour l'ownership | `<base>/power` |
| `topics.power_state` | Miroir retained confirmant le dernier payload ON/OFF | `<topics.power>/state` |
| `topics.mode` | Commande retenue pilot/logi pour prendre la main | `<base>/mode` |
| `topics.mode_state` | Miroir retained pour refléter le mode actif | `<topics.mode>/state` |
| `topics.color` | Commandes RGB (#RRGGBB, R,G,B ou JSON {r,g,b}) | `<base>/color` |
| `topics.color_state` | Miroir retained de la dernière couleur acceptée | `<topics.color>/state` |
| `topics.brightness` | Commande 0-100 (implique power=ON) | `<base>/brightness` |
| `topics.brightness_state` | Miroir retained de la luminosité | `<topics.brightness>/state` |
| `topics.alert` | Sujet JSON pour alert/warning/info (non retained) | `<base>/alert` |
| `topics.status` | JSON retained online/offline + attributs | `<base>/status` |
| `topics.lwt` | Disponibilité MQTT publish/Last Will online/offline | `<base>/lwt` |
| `home_assistant.device_id` | Identifiant unique Home Assistant | `lightspeed-alerts` |
| `home_assistant.device_name` | Nom présenté dans HA | `Logitech Alerts` |
| `home_assistant.manufacturer` | Fabricant affiché | `Logitech` |
| `home_assistant.model` | Modèle affiché | `LED Middleware` |
| `home_assistant.area` | Zone HA optionnelle | `Bureau` |
| `lighting.default_color` | Couleur appliquée au démarrage | `#00FF80` |
| `lighting.auto_restore` | Restaure le profil Logitech en mode auto | `true` |
| `lighting.lock_file` | Verrou pour éviter les accès concurrents | `lightspeed.lock` |
| `effects.override_duration_seconds` | Durée des overrides Alert/Warning (1-300s) | `10` |
| `palettes.alert.max_duration_ms` | Durée max (Principe IV) | `500` |
| `palettes.warning.max_duration_ms` | Durée max warning | `350` |
| `logitech.dll_path` | Chemin personnalisé vers LogitechLed.dll |  |
| `logitech.profile_backup` | Sauvegarde du profil initial | `backup.json` |
| `observability.health_topic` | Topic JSON de santé retenu | `<topics.status>` |
| `observability.log_level` | Niveau de logs | `INFO` |
<!-- config-table:end -->

## 3. Run the MQTT Service

```pwsh
# From repo root with venv active
python simple-logi.py serve --config config.yaml
```

- On startup the service validates the config, connects to MQTT, publishes HA discovery payloads, and logs readiness.
- Check Home Assistant → Settings → Devices → "Lightspeed Alerts" to confirm entities appear.

## 4. Trigger Manual Jobs (optional)

```pwsh
python simple-logi.py alert   --config config.yaml
python simple-logi.py warning --config config.yaml
python simple-logi.py color   --color "#33AAFF" --config config.yaml
python simple-logi.py auto    --config config.yaml
```

- CLI commands share the same lock with the MQTT worker, so run them only when the service is idle or stopped.

## 5. Validate End-to-End

1. In Home Assistant, open the auto-generated device and test each entity:
    - Alert button → keyboard pulses red/white/black.
    - Warning button → keyboard pulses amber/black.
    - RGB light → pick colors and verify <300 ms latency.
    - Auto switch → returns control to Logitech software.
    - Status sensor → shows `online`; stop the service to see it flip `offline`.
2. Review the retained `lightspeed/alerts/health` topic for JSON telemetry (controller state, `last_error`).
3. Restart the service and confirm HA reuses the same device (no duplicates) thanks to retained discovery payloads.
