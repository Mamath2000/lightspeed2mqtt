# Home Assistant MQTT Contract: Base-Relative Topic Schema

| Topic | Direction | Retained | Payload | Notes |
|-------|-----------|----------|---------|-------|
| `<base>/<power>` | HA ➜ Service | Yes | `"ON"` or `"OFF"` | `ON` hands control to integration, `OFF` restores Logitech immediately. Service mirrors to `<power/state>`. |
| `<base>/<mode>` | HA ⇄ Service | Yes | `"pilot"` or `"logi"` | Single channel for command + state. Service republishes the accepted payload and updates `<mode/state>`. |
| `<base>/<color>` | HA ➜ Service | Yes | `#RRGGBB`, `R,G,B`, or `{ "r":int, "g":int, "b":int }` | Implies `power=ON`. Service republishes parsed color JSON to `<color/state>`. |
| `<base>/<brightness>` | HA ➜ Service | Yes | `0-100` or `{ "brightness": int }` | Implies `power=ON`. Confirmed via `<brightness/state>`. |
| `<base>/<alert>` | HA ➜ Service | No | JSON `{ "type": "alert"|"warning"|"info", "duration"?: int }` | Triggers palettes with duration cap 1–300s. Unknown fields ignored with warning. |
| `<base>/<status>` | Service ➜ HA | Yes | JSON `{ "state": "online"|"offline", "attributes": {"mode":..., "power":..., "last_error"?: str} }` | Updated on connect, state transitions, and error paths per Principle V. |
| `<base>/<lwt>` | Service ↔ Broker | Yes | `"online"` / `"offline"` | Client publishes `online` on connect; MQTT Last Will is set to `offline`. HA automations watch this topic for availability. |

## QoS & Retain Strategy

- All retained topics use QoS 1 to survive broker restarts (power, mode, color, brightness, status, lwt).
- Non-retained command topics (`<base>/alert`) use QoS 0 to minimize latency; HA automations may resend periodically if idempotence required.

## Discovery Notes

- `lightspeed/ha_contracts.py` must render MQTT discovery payloads pointing to the derived canonical topics above.
- Light entity uses `<color>` and `<brightness>` topics for command/state, while switches/sensors expose `<power>`, `<mode>`, `<status>`, and `<lwt>` as appropriate.

## Validation

- Any payload outside the allowed literals should elicit a warning log and the service should re-publish the last known good state to keep HA dashboards consistent.
