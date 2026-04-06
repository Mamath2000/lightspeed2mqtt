---
id: development
title: Développement
sidebar_label: Développement
---

# Développement

Installer l'environnement :

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Exécuter les tests :

```bash
pytest -q
```

Synchroniser la documentation de configuration :

```bash
python scripts/update_config_docs.py
```

Bonnes pratiques :

- Garder les tests locaux verts avant de pousser.
- Utiliser des branches nommées `fix/...` ou `docs/...` pour changements isolés.
- Le script `scripts/update_config_docs.py` génère automatiquement le tableau des clés de configuration et met à jour `README.md` et `specs/.../quickstart.md`.

Dépannage rapide :

- Si le service refuse de démarrer à cause du verrou (`lightspeed.lock`), consultez `lightspeed/lighting.py` — un verrou stale est désormais détecté et peut être supprimé automatiquement (variable `LOGI_LOCK_STALE_SECONDS` pour régler l'âge).