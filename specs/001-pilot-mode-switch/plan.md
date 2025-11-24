# Implementation Plan: Pilot Mode Switch & Temporary Alerts

**Branch**: `001-pilot-mode-switch` | **Date**: 2025-11-24 | **Spec**: [specs/001-pilot-mode-switch/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-pilot-mode-switch/spec.md`

**Note**: This plan drives `/speckit.tasks` and `/speckit.implement`. Follow the phased workflow exactly.

## Summary

Replace the legacy Auto button with a Home Assistant switch that explicitly governs Pilot (integration-controlled) or Off (Logitech-controlled) mode, enforce Light entity on/off semantics, and make Alert/Warning overrides time-bound so they revert to the prior mode automatically. Work touches MQTT discovery payloads, `ControlMode` orchestration, override timers, and configuration validation/doc updates so that HA operators get deterministic ownership and observability.

## Technical Context

**Language/Version**: Python 3.13 (single-process CLI + MQTT service)  
**Primary Dependencies**: `paho-mqtt`, `logipy` (LogitechLed.dll bridge), `pyyaml`, `click`  
**Storage**: In-memory state + retained MQTT topics (no external DB)  
**Testing**: `pytest` suite under `tests/` with MQTT + config stubs  
**Target Platform**: Windows host with Logitech G Hub/LGS and an MQTT broker (HA/Mosquitto)  
**Project Type**: Single Python service/CLI entrypoint (`simple-logi.py`)  
**Performance Goals**: Process MQTT commands within 100 ms, enforce override timers ≤300 s, resume saved colors within 1 s  
**Constraints**: Honor Logitech save/restore semantics, Python-only surface, bounded alert frames (≤500 ms), documented MQTT contracts  
**Scale/Scope**: One keyboard per process instance; limited MQTT topics scoped under configured base prefix

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Momentary Control (I)** – Pilot/Off transitions must always save last RGB payload and release Logitech control on Off; overrides cannot outlive configured timer and must restore prior owner.
2. **Explicit MQTT Contracts (II)** – Replaces Auto topic with HA switch + buttons but keeps schemas documented through updated discovery payloads and contracts docs.
3. **Python-Only Surface (III)** – All changes remain in `lightspeed/*.py`, CLI wiring, config docs, and pytest suites—no new runtimes or services.
4. **Safe Alert Patterns (IV)** – Override durations configurable but clamped (0 < t ≤ 300 s); alert/warning frame pacing unchanged.
5. **Observable Operations (V)** – Retained status topics/reporting extended to include Pilot/Off/Override state plus logs at each transition for troubleshooting.

**Post-Design Re-Evaluation**: `data-model.md`, `ha-mqtt-contract.md`, and `quickstart.md` all preserve save/restore semantics, keep MQTT schemas explicit (no new topics beyond documented switch/light/override/status set), rely solely on Python components, keep alert durations bounded by config validation, and enhance observability with retained status attributes—no constitution risks detected.

## Project Structure

### Documentation (this feature)

```text
specs/001-pilot-mode-switch/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 deliverable
├── data-model.md        # Phase 1 deliverable
├── quickstart.md        # Phase 1 deliverable
├── contracts/
│   └── ha-mqtt-contract.md  # Phase 1 deliverable
└── tasks.md             # Generated later by /speckit.tasks
```

### Source Code (repository root)

```text
lightspeed2mqtt/
├── simple-logi.py            # CLI entry (serve/color/alert/warning/auto)
├── lightspeed/
│   ├── config.py             # YAML loading + validation
│   ├── control_mode.py       # Pilot/off state machine & overrides
│   ├── mqtt.py               # MQTT client + HA discovery/topics
│   ├── lighting.py           # Logitech LED orchestration, palettes
│   ├── ha_contracts.py       # Discovery payload builders
│   ├── observability.py      # Structured logging/status topics
│   └── config_docs.py        # Derived config reference
├── tests/
│   ├── test_config.py
│   ├── test_cli_config.py
│   ├── test_control_mode.py
│   ├── test_mqtt_light.py
│   ├── test_ha_contracts.py
│   └── test_observability.py
├── docs/
│   └── validation/
├── config.example.yaml       # Canonical config template
├── requirements.txt
├── scripts/
└── specs/
    ├── 001-pilot-mode-switch/
    └── 001-update-topics-schema/
```

**Structure Decision**: Single Python package (`lightspeed/`) with CLI entrypoint plus pytest suite; feature work lives in config, MQTT, control, contracts, docs, and tests under this tree.

## Complexity Tracking

No constitution deviations identified; table not required.
