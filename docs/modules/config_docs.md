---
id: config-docs
title: Génération documentation config
sidebar_label: Config Docs
---

# Génération de la documentation de configuration

Le fichier `lightspeed/config_docs.py` centralise la définition des clés de configuration et leurs descriptions via la classe `FieldDoc`.

- `render_config_field_table()` retourne un tableau Markdown prêt à être inséré dans la documentation.
- Le script `scripts/update_config_docs.py` utilise cette fonction pour synchroniser `README.md` et `specs/.../quickstart.md` avec `config.example.yaml`.

Usage :

```bash
python scripts/update_config_docs.py
```

Ceci permet de garder la documentation utilisateur à jour avec la structure attendue du YAML.
