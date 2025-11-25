# Implementation Plan: Base-Relative Topic Schema

**Branch**: `001-update-topics-schema` | **Date**: 2025-11-24 | **Spec**: [specs/001-update-topics-schema/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-update-topics-schema/spec.md`

**Note**: This plan drives `/speckit.tasks` and `/speckit.implement`. Stick to the phases below.

## Summary

Normalize all MQTT topics so operators only set `topics.base` plus the canonical suffixes (`power`, `mode`, `color`, `brightness`, `alert`, `status`, `lwt`). Color/brightness retain their schemas, alert/warning commands converge on the JSON payload defined for `<base>/alert`, pilot control remains `<base>/mode` (`pilot` vs `logi`), and `<base>/lwt` surfaces `online`/`offline`. Code, docs, and tests must be updated together so the refreshed TopicMap is validated, rendered in discovery payloads, and exercised end-to-end.

## Technical Context

**Language/Version**: Python 3.13 (single-process CLI + MQTT service)  
**Primary Dependencies**: `paho-mqtt`, `logipy` + LogitechLed.dll, `pyyaml`, `click`  
**Storage**: None (state kept in memory + MQTT retained topics)  
**Testing**: `pytest` test suite under `tests/`  
**Target Platform**: Windows host w/ Logitech G Hub or LGS and an accessible MQTT broker (Home Assistant / Mosquitto)  
**Project Type**: Single Python service/CLI (`simple-logi.py` entrypoint)  
**Performance Goals**: Handle MQTT commands <100 ms, keep overrides ≤300 s, republish retained state within 1 s of reconnect  
**Constraints**: Preserve Logitech handoff semantics, keep MQTT contracts explicit, remain Python-only, maintain bounded alert timings, log every transition (Principles I–V)  
**Scale/Scope**: One keyboard per instance; a handful of MQTT topics within `<base>`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Momentary Control (I)** – Plan retains cached color/brightness replay, enforces override timers, and defines `logi` payload to immediately restore Logitech control + shut down the DLL session.
2. **Explicit MQTT Contracts (II)** – Topic names stay within the constitutionally mandated catalog (power/mode/color/brightness/alert + status + lwt); contracts + docs will be versioned, preventing undocumented schemas.
3. **Python-Only Surface (III)** – Only `lightspeed/*.py`, `simple-logi.py`, and pytest suites change; no new runtimes or daemons.
4. **Safe Alert Patterns (IV)** – Alert/warning effects stay untouched; consolidating topics does not alter frame durations or palettes.
5. **Observable Operations (V)** – Structured status JSON persists, and new retained `mode` + `lwt` topics improve visibility of ownership & availability.

**Post-Design Re-Evaluation**: Data model + contracts keep save/restore semantics, reuse existing palettes, and increase observability while remaining Python-only. No constitution violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-update-topics-schema/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 deliverable
├── data-model.md        # Phase 1 deliverable
├── quickstart.md        # Phase 1 deliverable
├── contracts/
│   └── ha-mqtt-contract.md  # Phase 1 deliverable
└── tasks.md             # Produced later by /speckit.tasks
```

### Source Code (repository root)

```text
lightspeed2mqtt/
├── simple-logi.py
├── lightspeed/
│   ├── config.py
│   ├── mqtt.py
│   ├── ha_contracts.py
│   ├── control_mode.py
│   ├── lighting.py
│   ├── observability.py
│   └── config_docs.py
├── tests/
│   ├── test_config.py
│   ├── test_cli_config.py
│   ├── test_config_docs.py
│   ├── test_mqtt_light.py
│   ├── test_ha_contracts.py
│   └── test_control_mode.py
├── docs/
│   └── validation/
├── config.example.yaml
└── specs/
    ├── 001-pilot-mode-switch/
    └── 001-update-topics-schema/
```

**Structure Decision**: Single Python service with a `lightspeed/` domain package, pytest suites in `tests/`, and feature specs under `specs/`.

## Complexity Tracking

No constitution deviations identified; additional tracking not required.

````
