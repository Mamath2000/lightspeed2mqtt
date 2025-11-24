# Journal de vérification manuelle – 24 novembre 2025

Ce document trace les vérifications manuelles effectuées après l'intégration du schéma « Base-Relative Topic ». Les étapes ci-dessous doivent être répétées à chaque fois que `topics.base`, la configuration MQTT, ou le workflow Pilot/Alert évolue.

## Environnement

- OS : Windows 11 (PowerShell)
- Python : 3.13.5 (`C:/Python313/python.exe`)
- Dépendances : `pip install -r requirements.txt`
- Fichier chargé : `config.example.yaml`

## Commandes exécutées

### 1. Validation hors connexion

```pwsh
python simple-logi.py validate-config --config config.example.yaml
```

Sortie observée :

```text
Variables d'environnement manquantes dans C:\Users\Mamat\OneDrive\Documents\lightspeed2mqtt\config.example.yaml: MQTT_PASSWORD
✅ Config valide
   • Fichier : C:\Users\Mamat\OneDrive\Documents\lightspeed2mqtt\config.example.yaml
  • Schéma  : 0779deed2db0
  • Validée : 2025-11-23T22:13:24.065603+00:00
```

La commande retourne le code `0`, confirmant que le template partagé reste valide après les derniers changements (suffixes dérivés `power/mode/color/brightness/alert/status/lwt`).

### 2. Service + flux Pilot/Light

```pwsh
python simple-logi.py serve --config config.yaml
```

Observations attendues (avec broker MQTT + clavier Logitech branchés) :

1. Les logs `Configuration chargée`, `Connecté au broker` puis `Etat pilot_switch=...` apparaissent. Le service republie immédiatement tous les topics retenus (`<base>/mode/state`, `<base>/power/state`, `<base>/color/state`, `<base>/status`, `<base>/lwt`).
2. Publication `"pilot"` sur `<base>/mode` (ou bascule du switch Home Assistant) force `pilot_switch=ON`, `light_state=ON`, et rejoue la dernière couleur en moins de 2 s.
3. Publication `{"state":"OFF"}` sur `<base>/color` libère l'éclairage (`restore_logitech_control`), même si Pilot reste ON. Le statut MQTT expose alors `light_state=OFF` et `reason=color_ignored_light_off` si une couleur arrive pendant OFF.
4. Repasser `{"state":"ON"}` sans payload couleur réapplique automatiquement `{last_color,last_brightness}` mis en cache et republie `<base>/color/state`.
5. Envoyer une commande couleur pendant que Pilot est `logi` laisse Logitech maître des LED et enregistre `reason=color_ignored_pilot_off` dans `topics.status`.

### 3. Overrides + disponibilité

```pwsh
# Alert/Warn via CLI (équivaut à publier JSON sur <base>/alert)
python simple-logi.py alert --duration 5 --config config.yaml
python simple-logi.py warning --duration 7 --config config.yaml

# MQTT direct depuis PowerShell
mosquitto_pub -h $env:MQTT_HOST -t "lightspeed/alerts/mode" -m "pilot" -r
mosquitto_pub -h $env:MQTT_HOST -t "lightspeed/alerts/alert" -m '{"type":"alert","duration":15}'
mosquitto_sub -h $env:MQTT_HOST -t "lightspeed/alerts/status" -C 1
```

Attendus :

1. Chaque override publie `state=override_alert|override_warning` dans `<base>/status`, démarre un minuteur (`duration_seconds = payload.duration`), puis revient automatiquement à `pilot` ou `logi` selon l'état précédent.
2. Lancer Warning pendant Alert interrompt la première animation instantanément (`reason=alert_replaced`).
3. Basculer Pilot sur `logi` ou publier `OFF` sur `<base>/power` annule l'override, arrête le timer et remet Logitech aux commandes.
4. Payloads invalides (`duration=0`, texte, >300, type inconnu) génèrent un warning et aucun pattern ne démarre.
5. `mosquitto_sub -t <base>/lwt` doit montrer `online` après la connexion initiale, puis `offline` si vous tuez le process (`Ctrl+C`) sans `loop_stop`.

## Étapes consolidées (poste cible)

Ces vérifications nécessitent le SDK Logitech (`LogitechLed.dll`), un broker MQTT accessible et une configuration `topics.base` cohérente. Effectuez-les dans l'ordre :

1. **Copie & personnalisation**
   - `Copy-Item config.example.yaml config.yaml`
   - Renseignez `mqtt.*`, `topics.base`, les métadonnées Home Assistant, et exportez `${MQTT_PASSWORD}`.
2. **Validation finale**
   - `python simple-logi.py validate-config --config config.yaml`
   - Corrigez toute erreur (suffixes contenant `/`, durées hors 1-300, manque de DLL) avant d'aller plus loin.
3. **Démarrage du service**
   - `python simple-logi.py serve --config config.yaml`
   - Vérifiez dans les logs que le client configure le Last Will (`<base>/lwt = offline`) puis publie `online`.
4. **Tests Pilot/Light**
   - Depuis Home Assistant **ou** `mosquitto_pub` :
     - `mosquitto_pub -t "<base>/mode" -m "pilot" -r`
     - `mosquitto_pub -t "<base>/mode" -m "logi" -r`
   - Confirmez que les publications parallèles `mode_state`, `power_state`, `status.reason` correspondent aux actions.
   - Envoyez `{"state":"OFF"}` puis `{"state":"ON"}` sur `<base>/color` et vérifiez que Logitech reprend/relâche la main correctement.
5. **Tests overrides JSON**
   - `mosquitto_pub -t "<base>/alert" -m '{"type":"alert","duration":12}'`
   - `mosquitto_pub -t "<base>/alert" -m '{"type":"warning"}'`
   - Surveillez `mosquitto_sub -t "<base>/status"` pour voir `override_alert` → `override_warning` puis le retour à `pilot`.
   - Envoyez une charge invalide (`{"type":"unknown"}`) pour vérifier la présence d'un warning et l'absence d'override.
6. **Disponibilité / LWT**
   - `mosquitto_sub -t "<base>/lwt" -v`
   - Tuez le processus (`Ctrl+C`). Vous devez recevoir `offline` (message Last Will). Relancez `serve` pour voir `online`.
7. **CLI de secours (optionnel)**
   - `python simple-logi.py color '#0080FF' --config config.yaml`
   - `python simple-logi.py alert --duration 5 --config config.yaml`
   - `python simple-logi.py auto --config config.yaml`
   - Confirmez que ces commandes publient sur les mêmes sujets `<base>/<suffix>` que les automatisations.

> **Note** : Ces étapes doivent être retestées à chaque changement de profils ou de topics. Documentez tout écart dans ce journal.
