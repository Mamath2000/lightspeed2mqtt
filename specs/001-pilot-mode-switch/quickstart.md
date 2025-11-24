# Quickstart: Pilot Mode Switch & Temporary Alerts

1. **Update Configuration**
   - Add `effects.override_duration_seconds: 10` (or desired value between 1 et 300) inside each profile to bound Alert/Warning timers.
   - Define `topics.auto` and retained `topics.auto_state`; by default `topics.auto_state` can reuse `<topics.auto>/state`.
   - Confirm `topics.status` is retained to surface `pilot_switch` / `light_state` metadata in Home Assistant logs.

2. **Redeploy Discovery Payload**
   - Run `python simple-logi.py discover --config config.yaml` (or restart the service) so Home Assistant receives the updated `pilot_switch` component within the aggregated discovery payload.
   - Confirm the new switch entity appears under the device (`<device_name> Pilot`).

3. **Pilot Mode & Light Semantics**
   - Toggle the Pilot switch **ON**. The service publishes `pilot_switch=ON`, `mode=pilot`, and reapplies the cached RGB color immediately.
   - Turn the Light entity **OFF** (`{"state":"OFF"}` payload). Logitech control must resume instantly and `topics.status` should now show `light_state=OFF`.
   - Turn the Light entity **ON** without sending new RGB values; the previously cached `{color,brightness}` must be replayed as long as the Pilot switch remains ON.
   - Send color commands while the Pilot switch is OFF. They should be ignored and `reason=color_ignored_pilot_off` must appear in the retained status payload.

4. **Temporary Overrides**
   - Press the Alert or Warning buttons in HA. Each override runs its palette, publishes `mode=override_*`, and automatically schedules a timer for `effects.override_duration_seconds` seconds (or `{"duration": N}` when provided).
   - Trigger the other override while one is active. The prior timer cancels, the palette switches, and a new `override_*_start` reason is published.
   - Toggle the Pilot switch or Light OFF during an override. The override must stop, Logitech regains control, and no timer remainder fires.
   - Provide invalid `duration` payloads (0, >300, text). The service logs a warning with `override_action=invalid_duration` and rejects the request.
      - Observe `topics.status` retained payloads include `mode`, `pilot_switch`, `light_state`, `override_type`, and `remaining_seconds` (counting down while an override runs).

5. **Validation Checklist (à exécuter sur le poste avec périphériques Logitech)**
   - [ ] `python simple-logi.py serve --config config.yaml` démarre, loggue `Connecté au broker`, et republie l'état retenu du Pilot switch.
   - [ ] Pilot switch ON/OFF reflète instantanément l'état dans Home Assistant, `topics.auto_state`, et `topics.status` (`mode=pilot|off`).
   - [ ] Light OFF relâche la main vers Logitech immédiatement; Light ON restaure la couleur/brightness mise en cache.
   - [ ] Alert/Warning overrides se terminent après la durée configurée, peuvent être remplacées, et rétablissent la couleur précédente.
   - [ ] Les payloads `duration` invalides génèrent un warning (sans crash) et aucun override n'est lancé.
