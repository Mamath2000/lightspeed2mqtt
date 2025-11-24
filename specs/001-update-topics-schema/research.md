# Research Notes: Base-Relative Topic Schema

## Context

- **Pain point**: Operators currently specify fully-qualified MQTT topics in `config.yaml`, making base changes tedious and leading to drifts between docs and actual runtime wiring.
- **Goal**: Move to a canonical topic catalog derived from `topics.base`, while ensuring payload semantics remain compliant with the Constitution (power, mode, color, brightness, alert, status, lwt).
- **Scope**: Python-only service (`lightspeed/` package) with Home Assistant integrations and Mosquitto-compatible brokers.

## Legacy vs Canonical Topics

| Capability | Legacy Topic(s) | Payload | Issues | Canonical Topic | Payload |
|------------|-----------------|---------|--------|-----------------|---------|
| Ownership toggle | `topics.auto` / `topics.auto_state` | `auto`, `manual` (strings, retained) | Two topics required; unclear separation between command vs state | `topics.mode` | `pilot`, `logi` retained (single channel for command + state)
| Power handoff | implicit via `topics.light` state | JSON with `state`, `brightness`, `color` | No dedicated retained `ON/OFF` ownership indicator | `topics.power` | `ON`, `OFF` retained strings, drives integration vs Logitech control
| Color control | `topics.color` (absolute) | `#RRGGBB`, `R,G,B`, or JSON `{ r,g,b }` | Required full topic string; duplicates base prefix everywhere | `topics.color` (suffix) | Same payloads, always derived from base and retained
| Brightness control | `topics.brightness` (optional) | Numeric payload 0–100 | Not consistently retained; manual topic config required | `topics.brightness` | Integers 0–100 (string or `{ "brightness": int }`), retained + implies `power=ON`
| Alerts | Separate `topics.alert` + `topics.warning` | Plain text `alert`/`warning` | Multiple topics, no JSON metadata | `topics.alert` | JSON `{ "type": "alert" | "warning" | "info", "duration"?: 1-300 }`
| Status | `topics.status` fully-qualified | JSON health blob, retained | Manual topic composition, not obviously tied to base | `topics.status` suffix | Same JSON payload, derived from base, retained
| Availability | None / broker default | N/A | No explicit watchdog hook | `topics.lwt` | Retained `online` on connect, broker LWT `offline`

## Constraints & References

- Constitution 1.2.0 mandates canonical topics and payloads (power/mode/color/brightness/alert + availability/status behavior).
- Alert effects must keep existing timing bounds (≤500 ms per frame) and override durations (≤300 s).
- MQTT operations must remain single-threaded with background workers for lighting effects (per plan.md technical context).

## Open Decisions

- None outstanding; payload literals (`pilot`, `logi`, `ON`, `OFF`) agreed and codified in spec.md.
