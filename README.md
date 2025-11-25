# Logitech LED Middleware (Python)

Service Python qui écoute des topics MQTT pour déclencher différentes animations RGB sur vos périphériques Logitech (G Hub / LGS).

## Commandes Makefile

Le Makefile fournit des commandes pour automatiser l’installation, les tests et la gestion du service Windows via NSSM :

| Commande             | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `make install`       | Crée l’environnement virtuel et installe les dépendances Python              |
| `make run`           | Lance l’application principale (`simple-logi.py`)                           |
| `make test`          | Exécute tous les tests unitaires avec pytest                                |
| `make add_service`   | Installe le service Windows via NSSM                                        |
| `make remove_service`| Désinstalle le service Windows via NSSM                                     |
| `make stop_service`  | Arrête le service Windows via NSSM                                          |
| `make edit_service`  | Ouvre l’interface graphique NSSM pour éditer le service Windows             |
| `make help`          | Affiche l’aide sur les commandes disponibles                                |

> Le chemin de NSSM est paramétrable dans le Makefile (`NSSM_PATH`).

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

> Vous pouvez remplacer `python` par `./.venv/Scripts/python.exe` si vous préférez ne pas activer le venv.

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
  device_id: lightspeed
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
  info:
    max_duration_ms: 200
    frames:
    - color: "#FFFFFF"
      duration_ms: 150
    - color: "#555555"
      duration_ms: 150

logitech:
  dll_path: "lib\\LogitechLed.dll" # Chemin personnalisé vers LogitechLed.dll (laisser vide pour auto)

observability:
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
| `home_assistant.device_id` | Identifiant unique Home Assistant | `lightspeed` |
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
| `palettes.info.max_duration_ms` | Durée max info | `200` |
| `logitech.dll_path` | Chemin personnalisé vers LogitechLed.dll | `lib\\LogitechLed.dll` |
| `observability.log_level` | Niveau de logs | `INFO` |
<!-- config-table:end -->

### Catalogue des topics MQTT

Tous les topics sont dérivés de `topics.base` (ex : `lightspeed/alerts`).

| Sujet                | Retained | Direction      | Payload                                         | Description                                      |
|----------------------|----------|---------------|-------------------------------------------------|--------------------------------------------------|
| `<base>/status`      | Oui      | Service ➜ HA  | JSON `{ "state": "on"|"off", "rgb": [r,g,b], "brightness": 0-255, "mode": "pilot"|"auto" }` | État complet de la lumière et du mode            |
| `<base>/switch`      | Oui      | HA ➜ Service  | `on` / `off`                                    | Allume/éteint la lumière (pilot uniquement)      |
| `<base>/rgb/set`     | Oui      | HA ➜ Service  | `#RRGGBB`, `R,G,B` ou JSON                      | Change la couleur RGB (pilot uniquement)         |
| `<base>/brightness/set` | Oui   | HA ➜ Service  | `0-255` ou JSON                                 | Change la luminosité (pilot uniquement)          |
| `<base>/mode/set`    | Oui      | HA ➜ Service  | `pilot` / `auto`                                | Change le mode de contrôle                       |
| `<base>/alert`       | Non      | HA ➜ Service  | (vide ou JSON)                                  | Déclenche un effet d’alerte (rouge)             |
| `<base>/warn`        | Non      | HA ➜ Service  | (vide ou JSON)                                  | Déclenche un effet warning (orange)             |
| `<base>/info`        | Non      | HA ➜ Service  | (vide ou JSON)                                  | Déclenche un effet info (blanc/gris)            |
| `<base>/lwt`         | Oui      | Service ⇄ Broker | `online` / `offline`                         | Disponibilité MQTT (Last Will)                   |

> Les topics `/switch`, `/rgb/set`, `/brightness/set`, `/mode/set` sont à utiliser pour piloter l’état. Le topic `/status` est retained et permet à Home Assistant de re-synchroniser l’état après redémarrage.

### Workflow pilot/auto

1. **Prendre la main (pilot)** : publiez `pilot` sur `<base>/mode/set`. Le middleware applique la dernière couleur/brightness et passe en mode pilot.
2. **Envoyer des commandes** : tant que le mode pilot est actif, envoyez des couleurs (`<base>/rgb/set`), de la luminosité (`<base>/brightness/set`) ou déclenchez un effet (`<base>/alert`, etc.).
3. **Rendre la main à Logitech (auto)** : publiez `auto` sur `<base>/mode/set`. Le service arrête les effets actifs, restaure l’éclairage Logitech, et passe en mode auto.

Le topic `<base>/status` est retained et permet à Home Assistant de retrouver l’état après redémarrage. `<base>/lwt` indique la disponibilité du service.

## Lancer le service MQTT

```powershell
python simple-logi.py serve --config config.yaml
```

Le service :
- applique `lighting.default_color` dès que le contrôleur est prêt ;
- s'abonne aux sujets dérivés de `topics.base` décrits ci-dessus ;
- restaure Logitech instantanément lorsque vous publiez `auto` sur `<base>/mode/set` ;
- republie toutes les confirmations (`/status`, `lwt`) avec `retain` pour que Home Assistant retrouve l'état après redémarrage ;
- rejette toute commande JSON invalide (alertes, couleurs, brightness) et consigne la raison dans les logs.

## Utilisation en ligne de commande (tests rapides)

Les sous-commandes offrent les mêmes effets que les topics MQTT :

```powershell
# Couleur ponctuelle (hex ou R,G,B). --duration permet de rendre la main automatiquement.
python simple-logi.py color '#FF3300' --duration 5 --config config.yaml

# Pattern alerte jusqu'à Ctrl+C (équivalent à publier sur <base>/alert)
python simple-logi.py alert --config config.yaml

# Pattern warning pendant 10 secondes (équivalent à <base>/warn)
python simple-logi.py warning --duration 10 --config config.yaml

# Rendre la main immédiatement (publie `auto` sur <base>/mode/set)
python simple-logi.py auto --config config.yaml
```

## Notes importantes

- `LogitechLed.dll` doit être disponible, sinon le SDK ne peut pas démarrer.
- Le service sauvegarde l'éclairage actuel au démarrage et le restaure lorsque vous publiez `auto` sur `<base>/mode/set` ou quand le programme se termine.
- Pour un usage 24/7, exécutez le script comme service Windows ou via le planificateur de tâches avec le venv activé.
