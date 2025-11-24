# Phase 0 Research

## MQTT Ownership Switch

- **Decision**: Publish the new Pilot switch via HA MQTT discovery using retained `state_topic`/`command_topic` pairs plus `availability`, mapping `"on"` → Pilot and `"off"` → Off.
- **Rationale**: HA switches expect retained state so the UI reflects keyboard ownership after restarts; using the standard pattern lets HA manage optimistic updates and reuses existing MQTT session handling in `lightspeed.mqtt`.
- **Alternatives considered**: Keeping the Auto button (stateless) or mapping Pilot to Light on/off were rejected because they hide ownership state and create ambiguous MQTT semantics.

## Override Timer Enforcement

- **Decision**: Track overrides in `ControlMode` with a single `threading.Timer` (or equivalent) bound to monotonic time, cancel/restart on Alert/Warning/Light/Switch events, and clamp configured duration to 1–300 seconds.
- **Rationale**: Centralizing timers ensures only one override runs at a time and prevents drift if MQTT messages pile up; using monotonic timers guarantees resumption even if the system clock changes.
- **Alternatives considered**: Spawning per-action timers risks overlaps and race conditions, and polling loops would block the MQTT handler, violating the <100 ms processing goal.

## Configuration Schema Update

- **Decision**: Introduce `override_duration_seconds` (default 10) under each profile in `config.yaml`, validate via `lightspeed.config` (`pyyaml` + custom checks), and surface it in `config_docs.py` plus `config.example.yaml`.
- **Rationale**: Reusing the current config pipeline keeps validation errors actionable, supports per-profile overrides, and avoids ad-hoc environment variables.
- **Alternatives considered**: Hard-coding durations in code blocks operators from tuning behavior; a second YAML file was rejected to keep configuration centralized.

## Logitech Control Release

- **Decision**: Continue using `logipy` to save Logitech state, call `LogiLedRestoreLighting` whenever Off mode or override completion hands control back, and guard redundant calls using `ControlMode` ownership flags.
- **Rationale**: This honors the Momentary Control principle, avoids flicker, and ensures Logitech Options+ regains ownership immediately when requested.
- **Alternatives considered**: Restarting the Logitech DLL on every handoff adds latency and instability; skipping restore would violate Principle I.

## Status Telemetry Pattern

- **Decision**: Extend the retained status topic payload to include `mode` (`pilot|off|override`) plus `override_type` and `remaining_seconds` when relevant, publishing on every transition.
- **Rationale**: Operators and dashboards can confirm ownership transitions without log scraping, satisfying Principle V and simplifying alert debugging.
- **Alternatives considered**: Creating separate topics per mode would multiply subscriptions and complicate HA templates; logging locally only would make remote monitoring impossible.
