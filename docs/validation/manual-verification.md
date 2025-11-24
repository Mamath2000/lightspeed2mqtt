# Journal de vérification manuelle – 25 novembre 2025

Ce document trace les vérifications manuelles effectuées après l'intégration du flux `config.yaml`.

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

La commande retourne le code `0`, confirmant que le template partagé reste valide après les derniers changements, y compris les champs `topics.auto_state` et `effects.override_duration_seconds`.

### 2. Service + flux Pilot/Light

```pwsh
python simple-logi.py serve --config config.yaml
```

Observations attendues (avec broker MQTT + clavier Logitech branchés) :

1. Les logs `Configuration chargée`, `Connecté au broker` puis `Etat pilot_switch=OFF` apparaissent. Le service republie immédiatement l'état retenu (`topics.auto_state`).
2. Publication `"ON"` sur `topics.auto` (ou bascule du switch Home Assistant) force `pilot_switch=ON`, `mode=pilot`, et rejoue la dernière couleur en moins de 2 s.
3. Publication `{"state":"OFF"}` sur `topics.color` libère l'éclairage (`LogiLedRestoreLighting()`), même si le Pilot reste ON. Le statut MQTT expose alors `light_state=OFF`.
4. Repasser `{"state":"ON"}` sans payload couleur réapplique automatiquement `{last_color,last_brightness}` mis en cache.
5. Envoyer une commande couleur pendant que le Pilot est OFF laisse Logitech maître des LED et enregistre `reason=color_ignored_pilot_off` dans `topics.status`.

### 3. Overrides temporaires

```pwsh
# Alert/Warn depuis Home Assistant ou via MQTT direct
python simple-logi.py alert --duration 5 --config config.yaml
python simple-logi.py warning --duration 7 --config config.yaml
```

Attendus :

1. Chaque override publie `mode=override_alert|override_warning`, démarre un minuteur, puis revient automatiquement à `pilot` ou `off` selon l'état des entités.
2. Lancer Warning pendant Alert interrompt la première animation instantanément (`override_action=replaced`).
3. Basculer le Pilot switch OFF/OFF annule l'override et remet Logitech aux commandes (aucune reprise différée).
4. Payloads invalides (`duration: 0`, texte, >300) génèrent `WARNING override_action=invalid_duration` sans planter.

## Étapes consolidées (à exécuter sur le poste cible)

Ces vérifications nécessitent le SDK Logitech (`LogitechLed.dll`) et un broker MQTT accessibles. Réalisez-les depuis la machine où tourne réellement le service :

1. **Copie & personnalisation**
   - `Copy-Item config.example.yaml config.yaml`
   - Renseignez les topics/métadonnées HA et remplacez `${MQTT_PASSWORD}` par une variable d'environnement définie.
2. **Validation finale**
   - `python simple-logi.py validate-config --config config.yaml`
   - Corrigez toute erreur signalée avant de poursuivre (les erreurs sur `topics.auto_state` ou `override_duration_seconds` sont bloquantes).
3. **Démarrage du service**
   - `python simple-logi.py serve --config config.yaml`
   - Attendez les logs `Configuration chargée`, `Connecté au broker`, et vérifiez que `topics.status` publie `mode=off` ou `pilot` selon l'état retenu.
4. **Tests Pilot/Light**
   - Dans Home Assistant, basculez le switch Pilot ON/OFF et observez l'éclairage + `topics.auto_state`.
   - Éteignez puis rallumez la Light; Logitech doit reprendre la main pendant OFF et la couleur précédente doit revenir instantanément pendant ON.
5. **Tests overrides**
   - Appuyez sur Alert/Warning. Les palettes doivent durer exactement `effects.override_duration_seconds` (ou la valeur envoyée) puis revenir à l'état précédent.
   - Lancez un second override ou basculez Pilot OFF pour confirmer que les minuteurs s'annulent sans délai.
6. **CLI de secours**
   - `python simple-logi.py color '#0080FF' --config config.yaml`
   - `python simple-logi.py auto --config config.yaml`
   - Assurez-vous que `color` n'est appliquée que lorsque Pilot est ON.

> **Note** : Ces étapes doivent être retestées à chaque changement de profils ou de topics. Documentez tout écart dans ce journal.
