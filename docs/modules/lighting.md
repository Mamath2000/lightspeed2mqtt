---
id: lighting
title: Lighting & SDK
sidebar_label: Lighting
---

# Lighting / SDK (`lightspeed.lighting`)

Ce module gère l'interaction avec le SDK Logitech et expose un contrôleur haut-niveau `LightingController`.

Principales caractéristiques :

- Patch de `logipy.logi_led` pour injecter un handle direct vers `LogitechLed.dll` (attendu dans `lib/`).
- Wrapper Python pour les appels SDK (init, shutdown, set_lighting, flash, pulse, save/restore).
- `LightingController` : cycle de vie `start()` / `shutdown()`, application immédiate `set_static_color()`, patterns (`start_pattern()`), et `release()` pour rendre la main.

Verrou d'accès au périphérique :

- `lock_file` (configurable via `lighting.lock_file`) évite les accès concurrents à la DLL.
- Le fichier contient un JSON `{ "pid": <int>, "timestamp": <float> }`.
- Comportement : si le fichier existe, le contrôleur tente de détecter un verrou *stale* :
  - vérifie si le PID signalé est toujours vivant (si non → stale),
  - ou si l'horodatage dépasse `LOGI_LOCK_STALE_SECONDS` (par défaut 300s) → stale.
- Si stale → suppression du fichier et reprise; sinon → `RuntimeError`.

Chargement de la DLL :

- `ensure_logi_dll_loaded()` recherche `LogitechLed.dll` dans `lib/`, variable d'env `LOGI_LED_DLL`, ou chemins standards `Program Files`.

Utilitaires :

- `parse_color_string(value)` — accepte JSON `{r,g,b}`, listes `[r,g,b]`, hex `#RRGGBB` ou `R,G,B`.
- `apply_brightness(color, brightness)` — applique la luminosité 0-255.
- `palette_frames(palette)` / `alert_frames(profile)` / `warning_frames(profile)` / `info_frames(profile)` — conversion des palettes de config en frames temporelles.

Sécurité :

- Tous les appels SDK sont encapsulés et protégés par locks pour éviter les conditions de concurrence.

Save/Restore et contrôle Logitech (limite du SDK) :

- `LogiLedSaveCurrentLighting()` / `LogiLedRestoreLighting()` ne font que rejouer un snapshot interne au SDK ; ils ne rendent jamais la main au driver/G HUB. La session SDK reste propriétaire exclusive de l'éclairage tant qu'elle est ouverte.
- `LogiLedInit()` coupe systématiquement tout effet natif Logitech en cours (comportement documenté du SDK) — il n'y a donc pas de moyen de "jeter un œil" à l'effet natif sans l'interrompre.
- Seul `LogiLedShutdown()` (via `release()`) rend réellement la main à Logitech Options+/G HUB.
- `start_pattern()` appelle `LogiLedSaveCurrentLighting()` juste avant de lancer l'effet (recommandation du SDK), pour disposer d'un état de repli à jour si un appelant veut réappliquer la couleur précédente sans repasser par `release()`.

Voir aussi :
- `config.yaml` pour `lighting.lock_file` et `lighting.default_color`.
