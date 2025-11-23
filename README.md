# Logitech LED Middleware (Python)

Service unique en Python qui écoute des topics MQTT pour déclencher différentes animations RGB sur vos périphériques Logitech (G Hub / LGS).

## Prérequis

- Windows + Logitech G Hub **ou** Logitech Gaming Software (pour fournir `LogitechLed.dll`).
- DLL `LogitechLed.dll` accessible : placez-la à la racine du projet ou définissez `LOGI_LED_DLL` vers son chemin complet.
- Python 3.9+ (testé avec 3.13).
- Un broker MQTT accessible (Mosquitto, Home Assistant, etc.).

## Installation rapide

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # puis personnalisez les topics/identifiants MQTT
```

> Vous pouvez remplacer `python` par `.\.venv\Scripts\python.exe` si vous préférez ne pas activer le venv.

## Configuration (.env)

`simple-logi.py` lit automatiquement `.env`. Les variables disponibles :

| Variable        | Description                                      | Défaut                  |
|-----------------|--------------------------------------------------|-------------------------|
| `MQTT_HOST`     | Hôte du broker                                   | `localhost`             |
| `MQTT_PORT`     | Port TCP                                         | `1883`                  |
| `MQTT_USERNAME` | (optionnel)                                      | vide                    |
| `MQTT_PASSWORD` | (optionnel)                                      | vide                    |
| `MQTT_CLIENT_ID`| Nom du client MQTT                               | `lightspeed-led`        |
| `TOPIC_COLOR`   | Topic pour changer la couleur                    | `lightspeed/color`      |
| `TOPIC_ALERT`   | Topic pour lancer l'alerte rouge/blanc/noir      | `lightspeed/alert`      |
| `TOPIC_WARNING` | Topic warning (ambre qui clignote)               | `lightspeed/warning`    |
| `TOPIC_AUTO`    | Topic pour rendre la main (restore lighting)     | `lightspeed/auto`       |
| `DEFAULT_COLOR` | Couleur appliquée au démarrage (hex ou R,G,B)    | `#00FF80`               |

## Lancer le service MQTT

```powershell
python simple-logi.py serve
```

Le service :

- applique `DEFAULT_COLOR` au démarrage ;
- écoute les quatre topics et adapte l'éclairage :
  - **`TOPIC_COLOR`** : payload `#RRGGBB`, `R,G,B` ou JSON `{"r":255,"g":0,"b":0}` pour une couleur fixe ;
  - **`TOPIC_ALERT`** : alterne rapidement rouge → blanc → noir ;
  - **`TOPIC_WARNING`** : clignotement orange / noir plus lent ;
  - **`TOPIC_AUTO`** : stoppe toute animation et restaure l'éclairage utilisateur.
		- **`TOPIC_COLOR`** : payload `#RRGGBB`, `R,G,B` ou JSON `{"r":255,"g":0,"b":0}` pour une couleur fixe ;
		- **`TOPIC_ALERT`** : alterne rapidement rouge → blanc → noir ;
		- **`TOPIC_WARNING`** : clignotement orange / noir plus lent ;
		- **`TOPIC_AUTO`** : stoppe toute animation et restaure l'éclairage utilisateur.

Envoyez simplement un message (QoS 0/1) sur le topic voulu, le service répond immédiatement.

## Utilisation en ligne de commande (tests rapides)

Les sous-commandes offrent les mêmes effets que les topics MQTT :

```powershell
# Couleur ponctuelle (hex ou R,G,B). --duration permet de rendre la main automatiquement.
python simple-logi.py color '#FF3300' --duration 5

# Pattern alerte jusqu'à Ctrl+C
python simple-logi.py alert

# Pattern warning pendant 10 secondes
python simple-logi.py warning --duration 10

# Rendre la main immédiatement
python simple-logi.py auto
```

## Notes importantes

- `LogitechLed.dll` doit être disponible, sinon le SDK ne peut pas démarrer.
- Le service sauvegarde l'éclairage actuel au démarrage et le restaure lorsque vous publiez sur `TOPIC_AUTO` ou quand le programme se termine.
- Pour un usage 24/7, exécutez le script comme service Windows ou via le planificateur de tâches avec le venv activé.
