---
id: usage
title: Usage & Quickstart
sidebar_label: Usage
---

# Usage & Quickstart

Prérequis :

- Python 3.8+
- Broker MQTT (ex. Mosquitto)
- SDK Logitech `LogitechLed.dll` pour Windows (placer dans `lib/` ou définir `LOGI_LED_DLL`)

Installer les dépendances :

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Configurer :

- Copiez `config.example.yaml` → `config.yaml` et adaptez `mqtt`, `topics.base`, `home_assistant`, etc.

Lancer le service :

```bash
python simple-logi.py serve
```

Commandes utiles :

- `python simple-logi.py color #FF0000` — applique une couleur et garde le contrôle
- `python simple-logi.py alert` — lance la palette d'alerte définie
- `python simple-logi.py warning` — lance la palette warning
- `python simple-logi.py auto` — rend immédiatement la main à Logitech

Debug / pas-à-pas :

- Voir `docs/modules/cli` pour la méthode recommandée avec `debugpy`.
- Pour des tests rapides, insérer `import pdb; pdb.set_trace()` et exécuter en terminal.

Vérifier les topics MQTT (exemple avec mosquitto_sub) :

```bash
mosquitto_sub -h <BROKER> -t 'lightspeed/#' -v
```

Remarque : les messages d'état sont publiés en retained sur `topics.state` et la disponibilité (LWT) sur `topics.lwt` (online/offline).