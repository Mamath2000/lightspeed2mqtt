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
  color: "" # Laisser vide pour dériver <base>/color, sinon fournir un topic complet
  alert: ""
  warning: ""
  auto: ""
  status: "" # Topic de disponibilité / santé

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
  health_topic: "lightspeed/alerts/health"
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
| `topics.color` | Topic pour les commandes de couleur | `<base>/color` |
| `topics.alert` | Topic pour déclencher le pattern alerte | `<base>/alert` |
| `topics.warning` | Topic pour déclencher le pattern warning | `<base>/warning` |
| `topics.auto` | Topic pour rendre la main à Logitech | `<base>/auto` |
| `topics.status` | Topic retained online/offline | `<base>/status` |
| `home_assistant.device_id` | Identifiant unique Home Assistant | `lightspeed-alerts` |
| `home_assistant.device_name` | Nom présenté dans HA | `Logitech Alerts` |
| `home_assistant.manufacturer` | Fabricant affiché | `Logitech` |
| `home_assistant.model` | Modèle affiché | `LED Middleware` |
| `home_assistant.area` | Zone HA optionnelle | `Bureau` |
| `lighting.default_color` | Couleur appliquée au démarrage | `#00FF80` |
| `lighting.auto_restore` | Restaure le profil Logitech en mode auto | `true` |
| `lighting.lock_file` | Verrou pour éviter les accès concurrents | `lightspeed.lock` |
| `palettes.alert.max_duration_ms` | Durée max (Principe IV) | `500` |
| `palettes.warning.max_duration_ms` | Durée max warning | `350` |
| `logitech.dll_path` | Chemin personnalisé vers LogitechLed.dll |  |
| `logitech.profile_backup` | Sauvegarde du profil initial | `backup.json` |
| `observability.health_topic` | Topic JSON de santé retenu | `<base>/health` |
| `observability.log_level` | Niveau de logs | `INFO` |
<!-- config-table:end -->

## Lancer le service MQTT

```powershell
python simple-logi.py serve --config config.yaml
```

Le service :

- applique `DEFAULT_COLOR` au démarrage ;
- écoute les quatre topics et adapte l'éclairage :
  - **`TOPIC_COLOR`** : payload `#RRGGBB`, `R,G,B` ou JSON `{"r":255,"g":0,"b":0}` pour une couleur fixe ;
  - **`TOPIC_ALERT`** : alterne rapidement rouge → blanc → noir ;
  - **`TOPIC_WARNING`** : clignotement orange / noir plus lent ;
  - **`TOPIC_AUTO`** : stoppe toute animation et restaure l'éclairage utilisateur.

Envoyez simplement un message (QoS 0/1) sur le topic voulu, le service répond immédiatement.

## Utilisation en ligne de commande (tests rapides)

Les sous-commandes offrent les mêmes effets que les topics MQTT :

```powershell
# Couleur ponctuelle (hex ou R,G,B). --duration permet de rendre la main automatiquement.
python simple-logi.py color '#FF3300' --duration 5 --config config.yaml

# Pattern alerte jusqu'à Ctrl+C
python simple-logi.py alert --config config.yaml

# Pattern warning pendant 10 secondes
python simple-logi.py warning --duration 10 --config config.yaml

# Rendre la main immédiatement
python simple-logi.py auto --config config.yaml
```

## Notes importantes

- `LogitechLed.dll` doit être disponible, sinon le SDK ne peut pas démarrer.
- Le service sauvegarde l'éclairage actuel au démarrage et le restaure lorsque vous publiez sur `TOPIC_AUTO` ou quand le programme se termine.
- Pour un usage 24/7, exécutez le script comme service Windows ou via le planificateur de tâches avec le venv activé.

## Migration depuis `.env`

1. Sauvegardez votre ancien `.env`, puis copiez `config.example.yaml` vers `config.yaml`.
2. Mappez chaque variable (`MQTT_HOST`, `MQTT_PORT`, `TOPIC_ALERT`, `DEFAULT_COLOR`, etc.) vers la section YAML équivalente (`mqtt.host`, `topics.alert`, `lighting.default_color`).
3. Pour les secrets, conservez `${MQTT_PASSWORD}` dans YAML et définissez la variable d'environnement côté système.
4. Exécutez `python simple-logi.py validate-config --config config.yaml`, corrigez les erreurs éventuelles, puis démarrez `serve`.
5. Supprimez ou ignorez l'ancien `.env` dès que la migration est terminée afin d'éviter les divergences.

Consultez `docs/validation/config-lint.md` pour un pas-à-pas détaillé (logs attendus, commandes MQTT de contrôle, etc.).
