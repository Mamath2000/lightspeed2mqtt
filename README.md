# Logitech LED Middleware (Python)

Service unique en Python qui écoute des topics MQTT pour déclencher différentes animations RGB sur vos périphériques Logitech (G Hub / LGS).

## Prérequis

- Windows + Logitech G Hub **ou** Logitech Gaming Software (pour fournir `LogitechLed.dll`).
- DLL `LogitechLed.dll` accessible : placez-la à la racine du projet ou définissez `LOGI_LED_DLL` vers son chemin complet.
- Python 3.9+ (testé avec 3.13).
- Un broker MQTT accessible (Mosquitto, Home Assistant, etc.).
- Dépendances Python : `logipy`, `paho-mqtt`, `pyyaml` (installées via `pip install -r requirements.txt`).

## Installation rapide

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item config.example.yaml config.yaml  # puis personnalisez les accès MQTT et la découverte HA
```

> Vous pouvez remplacer `python` par `.\.venv\Scripts\python.exe` si vous préférez ne pas activer le venv.

## Configuration (`config.yaml`)

1. Copiez l'exemple : `Copy-Item config.example.yaml config.yaml`.
2. Remplacez les valeurs MQTT/Home Assistant, ou utilisez `${MQTT_PASSWORD}` pour référencer une variable d'environnement.
3. Validez sans toucher au SDK ni au broker :

   ```powershell
   python simple-logi.py validate-config --config config.yaml
   ```

4. Démarrez ensuite les commandes (`serve`, `alert`, etc.) avec `--config`. Vous pouvez aussi définir `LOGI_CONFIG_PATH` si vous ne voulez pas répéter le chemin (priorité : argument CLI > env > `config.yaml`).

### Exemple complet

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

### Table de référence

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

### Catalogue des topics canoniques

Tous les sujets MQTT sont dérivés dynamiquement de `topics.base`. Les commandes Home Assistant publient toujours sur les suffixes suivants, et le middleware republie les confirmations retenues afin de garder les dashboards synchronisés :

| Sujet | Retained | Direction | Payload | Description |
|-------|----------|-----------|---------|-------------|
| `<base>/power` | Oui | HA ➜ Service | `ON` / `OFF` | Transfert d'ownership : `ON` confie la main au middleware, `OFF` rend la main Logitech immédiatement. |
| `<base>/power/state` | Oui | Service ➜ HA | `ON` / `OFF` | Miroir retenu pour que HA voie l'état même après redémarrage. |
| `<base>/mode` | Oui | HA ⇄ Service | `pilot` / `logi` | Canal unique de commande + état. `pilot` force l'intégration, `logi` coupe toutes les animations et restaure LogitechLed.dll. |
| `<base>/mode/state` | Oui | Service ➜ HA | `pilot` / `logi` | Confirmation retenue, utile si HA rate la commande initiale. |
| `<base>/color` | Oui | HA ➜ Service | `#RRGGBB`, `R,G,B` ou JSON `{"r":..,"g":..,"b":..}` | Fixe la couleur RGB. Implémentation applique automatiquement la dernière luminosité connue. |
| `<base>/color/state` | Oui | Service ➜ HA | JSON `{"state":"ON","color":{...},"brightness":<0-255>}` | Permet à HA de restaurer l'état visuel après reboot broker/client. |
| `<base>/brightness` | Oui | HA ➜ Service | `0-100` ou JSON `{ "brightness": int }` | Ajuste la luminosité tout en laissant la couleur intacte. Force `power=ON`. |
| `<base>/brightness/state` | Oui | Service ➜ HA | JSON `{ "brightness": 0-100 }` | Confirmation retenue destinée aux sliders HA. |
| `<base>/alert` | Non | HA ➜ Service | JSON `{ "type": "alert"|"warning"|"info", "duration"?: 1-300 }` | Demarre un override. `info` est traité comme `alert`. Valeurs hors bornes sont rejetées et loguées. |
| `<base>/status` | Oui | Service ➜ HA | JSON `{ "state": "online"|"offline", "mode":..., ... }` | Télémétrie détaillée (mode, couleur, erreurs, override actif). |
| `<base>/lwt` | Oui | Service ⇄ Broker | `online` / `offline` | Disponibilité. Le client publie `online` à la connexion et configure la Last Will `offline`. |

> 💡 Les topics suffixes (`power`, `mode`, etc.) **doivent** rester relatifs ; la dérivation `<base>/suffix` évite tout décalage quand vous changez `topics.base`.

### Workflow pilot/logi

1. **Prendre la main** : publiez le payload retenu `pilot` sur `<base>/mode` (ou utilisez le bouton HA correspondant). Le middleware s'assure que `power` vaut `ON`, rejoue la dernière couleur/brightness retenue et publie `pilot` sur `<base>/mode/state`.
2. **Envoyer des commandes** : tant que `pilot` est actif, envoyez des couleurs (`<base>/color`), de la luminosité (`<base>/brightness`) ou déclenchez un override (`<base>/alert`). Chaque commande est accusée via les topics `.../state` et `status`.
3. **Rendre la main Logitech** : publiez `logi` sur `<base>/mode` ou `OFF` sur `<base>/power`. Le service arrête les overrides actifs, restaure l'éclairage stocké via LogitechLed.dll, met à jour `mode_state`, `power_state`, `status` et laisse HA voir `logi`/`OFF` comme confirmation.

Grâce au retained + Last Will, Home Assistant peut redémarrer sans perdre l'information d'ownership et vos automatisations savent quand l'intégration est réellement disponible (`<base>/lwt`).

## Lancer le service MQTT

```powershell
python simple-logi.py serve --config config.yaml
```

Le service :

- applique `lighting.default_color` dès que le contrôleur est prêt ;
- s'abonne aux sujets dérivés de `topics.base` décrits ci-dessus ;
- restaure Logitech instantanément lorsque vous publiez `OFF` sur `<base>/power` ou `logi` sur `<base>/mode` ;
- republie toutes les confirmations (`/state`, `status`, `lwt`) avec `retain` pour que Home Assistant retrouve l'état après redémarrage ;
- rejette toute commande JSON invalide (alertes, couleurs, brightness) et consigne la raison dans les logs.

Envoyez simplement vos payloads sur les sujets canoniques (QoS 0 ou 1), la boucle événementielle applique les changements en moins de 100 ms.

## Utilisation en ligne de commande (tests rapides)

Les sous-commandes offrent les mêmes effets que les topics MQTT :

```powershell
# Couleur ponctuelle (hex ou R,G,B). --duration permet de rendre la main automatiquement.
python simple-logi.py color '#FF3300' --duration 5 --config config.yaml

# Pattern alerte jusqu'à Ctrl+C (équivalent à publier {"type":"alert"} sur <base>/alert)
python simple-logi.py alert --config config.yaml

# Pattern warning pendant 10 secondes (équivalent à {"type":"warning","duration":10})
python simple-logi.py warning --duration 10 --config config.yaml

# Rendre la main immédiatement (publie `logi` sur <base>/mode)
python simple-logi.py auto --config config.yaml
```

## Notes importantes

- `LogitechLed.dll` doit être disponible, sinon le SDK ne peut pas démarrer.
- Le service sauvegarde l'éclairage actuel au démarrage et le restaure lorsque vous publiez `logi` sur `<base>/mode`, `OFF` sur `<base>/power`, ou quand le programme se termine.
- Pour un usage 24/7, exécutez le script comme service Windows ou via le planificateur de tâches avec le venv activé.

## Migration depuis `.env`

1. Sauvegardez votre ancien `.env`, puis copiez `config.example.yaml` vers `config.yaml`.
2. Mappez chaque variable (`MQTT_HOST`, `MQTT_PORT`, `TOPIC_ALERT`, `DEFAULT_COLOR`, etc.) vers la section YAML équivalente (`mqtt.host`, `topics.alert`, `lighting.default_color`).
3. Pour les secrets, conservez `${MQTT_PASSWORD}` dans YAML et définissez la variable d'environnement côté système.
4. Exécutez `python simple-logi.py validate-config --config config.yaml`, corrigez les erreurs éventuelles, puis démarrez `serve`.
5. Supprimez ou ignorez l'ancien `.env` dès que la migration est terminée afin d'éviter les divergences.

Consultez `docs/validation/config-lint.md` pour un pas-à-pas détaillé (logs attendus, commandes MQTT de contrôle, etc.).
