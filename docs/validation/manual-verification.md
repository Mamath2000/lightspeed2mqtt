# Journal de vérification manuelle – 23 novembre 2025

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

La commande retourne le code `0`, confirmant que le template partagé reste valide après les derniers changements.

## Étapes à exécuter sur le poste cible

Ces vérifications nécessitent le SDK Logitech (`LogitechLed.dll`) et un broker MQTT accessibles. Réalisez-les depuis la machine où tourne réellement le service :

1. **Copie & personnalisation**
   - `Copy-Item config.example.yaml config.yaml`
   - Renseignez les topics/métadonnées HA et remplacez `${MQTT_PASSWORD}` par une variable d'environnement définie.
2. **Validation finale**
   - `python simple-logi.py validate-config --config config.yaml`
   - Corrigez toute erreur signalée avant de poursuivre.
3. **Démarrage du service**
   - `python simple-logi.py serve --config config.yaml`
   - Attendez les logs `Configuration chargée` et `Connecté au broker`.
4. **Tests MQTT/HA**
   - Publiez sur `topics.alert`, `topics.warning`, `topics.color` et observez la LED.
   - Vérifiez dans Home Assistant qu'un seul device est créé et que le `binary_sensor` de statut bascule `online/offline`.
   - Inspectez `topics.health` pour confirmer que `config_path`, `schema_revision` et `validated_at` correspondent.
5. **CLI de secours**
   - `python simple-logi.py color '#0080FF' --config config.yaml`
   - `python simple-logi.py auto --config config.yaml`
   - Assurez-vous que le verrou logiciel libère correctement le clavier.

> **Note** : Ces étapes restent à exécuter avec le matériel Logitech branché. Aucun autre correctif n'est nécessaire côté code pour réaliser la validation complète.
