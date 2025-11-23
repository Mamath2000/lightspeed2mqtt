# Guide de validation `config.yaml`

Ce document explique comment préparer, valider et dépanner la configuration YAML utilisée par `simple-logi.py`.

## 1. Préparer le fichier

1. Copier `config.example.yaml` vers `config.yaml`.
2. Renseigner les champs obligatoires (`mqtt`, `topics`, `home_assistant`, `lighting`, `palettes`, `logitech`).
3. Pour les secrets, utilisez la syntaxe `${NOM_VARIABLE}` et définissez la variable d'environnement correspondante avant d'exécuter le service.

## 2. Validation hors connexion (`validate-config`)

Utilisez la commande dédiée avant chaque déploiement. Aucun accès MQTT/SDK n'est réalisé si la validation échoue.

```pwsh
python simple-logi.py validate-config --config config.yaml
```

### Résultat attendu (succès)

```text
✅ Config valide
	• Fichier : C:\repo\config.yaml
	• Schéma  : ab12cd34ef56
	• Validée : 2025-11-23T12:34:56+00:00
```

### Résultat attendu (échec)

```text
❌ Config invalide
	• Fichier : C:\repo\config.yaml
	• Raison  : Clé obligatoire manquante: mqtt.host
```

Code de sortie `0` en cas de succès, `1` sinon. Enchaînez ensuite avec `serve` uniquement si la validation passe.

## 3. Vérification en conditions réelles (`serve --config`)

Lancez temporairement le service pour confirmer la connectivité MQTT et la découverte HA :

```pwsh
python simple-logi.py serve --config config.yaml
```

### Logs attendus

```text
INFO lightspeed.app Configuration chargée config_path=C:\repo\config.yaml schema_revision=ab12cd34ef56
INFO lightspeed.mqtt Connexion MQTT host=broker.local port=1883
INFO lightspeed.mqtt Connecté au broker
INFO lightspeed.mqtt Pattern alerte actif
```

- La première ligne confirme que le fichier est lu, validé et que le schéma (`schema_revision`) correspond à la version du loader.
- Les lignes suivantes montrent la connexion MQTT et les messages lorsque vous testez des topics (`alert`, `warning`, etc.).

### Vérifications MQTT/HA

1. **Disponibilité (`status`)** : `mosquitto_sub -t lightspeed/alerts/status -v` doit afficher `online` dès que le service démarre.
2. **Santé (`health_topic`)** : `mosquitto_sub -t lightspeed/alerts/health -v` renvoie un JSON contenant `status`, `config_path`, `schema_revision` et `validated_at`.
3. **Découverte Home Assistant** : `mosquitto_sub -t 'homeassistant/#' -v` doit montrer les messages `config` pour le `light`, les `button` (alert, warning, auto) et le `binary_sensor` de statut. Dans Home Assistant, un seul device portant `device_name` doit apparaître.
4. **Tests de commande** : publiez sur `topics.alert`, `topics.warning` ou `topics.color` selon les valeurs du YAML et observez les logs `Lightspeed` confirmant l'effet appliqué.

Arrêtez le service avec `Ctrl+C`. Si des erreurs se produisent, elles seront loguées et reprises dans le payload santé (`last_error`).

## 4. Migration depuis `.env`

1. Ouvrir l'ancien `.env` et repérer : `MQTT_HOST`, `MQTT_PORT`, `TOPIC_*`, `DEFAULT_COLOR`, etc.
2. Reporter chaque valeur dans les sections équivalentes de `config.yaml`.
3. Pour les secrets (`MQTT_PASSWORD`), utiliser `${MQTT_PASSWORD}` dans YAML puis conserver la variable d'environnement.
4. Lancer `python simple-logi.py serve --config config.yaml` et vérifier les logs/health topics comme décrit ci-dessus.
5. Une fois validé, supprimer/ignorer l'ancien `.env` et utiliser systématiquement `--config` pour chaque commande (`serve`, `alert`, `warning`, `color`, `auto`).

## 5. Dépannage rapide

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| `Config file not found` | Mauvais chemin ou fichier absent | Vérifier l'argument `--config` et que `config.yaml` existe |
| `Unknown key` | Orthographe différente ou champ obsolète | Corriger le nom selon `config.example.yaml` |
| `Duration exceeds limit` | Frame > 500/350 ms | Ajuster `duration_ms` selon Principe IV |
| `ENV var resolved empty` | Variable non définie dans l'environnement | Définir la variable avant de relancer ou remplacer par une valeur directe |

## 6. Validation continue

- Ajouter la commande de validation dans vos pipelines CI: `python simple-logi.py validate-config --config config.example.yaml`.
- Exécuter `pytest -k config` pour couvrir les tests unitaires associés au parseur.
