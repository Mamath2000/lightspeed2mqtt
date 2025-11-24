# Implementation Plan: Pilot Mode Switch & Temporary Alerts

**Branch**: `001-pilot-mode-switch` | **Date**: 2025-11-24 | **Spec**: [specs/001-pilot-mode-switch/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-pilot-mode-switch/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a Home Assistant Pilot switch that explicitly grants or releases keyboard control, ensure the Light entity mirrors HA on/off semantics, and make Alert/Warning overrides temporary with a configurable duration that restores the previous state automatically. Implementation will extend existing MQTT handlers, config schema, and discovery payloads while preserving Logitech LED control handoffs.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13  
**Primary Dependencies**: `paho-mqtt`, `logipy` (Logitech LED SDK wrapper), `click`, `pyyaml`  
**Storage**: N/A (in-memory state only)  
**Testing**: `pytest` with unit tests under `tests/`  
**Target Platform**: Windows host running Logitech LED SDK + MQTT broker connectivity  
**Project Type**: Single Python service/CLI  
**Performance Goals**: Process MQTT events <100 ms, keep overrides bounded (≤10 s default, configurable up to 300 s)  
**Constraints**: Must relinquish lighting on demand, retain discovery compatibility, keep CPU minimal during effects  
**Scale/Scope**: Single-user peripheral control; MQTT topics limited to existing namespace

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Momentary Control** – Plan keeps explicit Pilot/Off states plus override timers that always hand control back after duration, satisfying Principle I.
2. **MQTT Contracts** – We will continue using existing topics (`color`, `alert`, `warning`, `auto`/pilot switch) and documented JSON payloads; no new schema introduced.
3. **Python-Only Surface** – All changes touch current Python modules (`simple-logi.py`, `lightspeed/*`); no new runtimes are introduced.
4. **Safe Alert Patterns** – Alert/Warning effects already meet interval/palette bounds; we only add timers and resumptions, so Principle IV stays satisfied.
5. **Observable Operations** – Existing logging in `lightspeed.mqtt` will be extended to include Pilot switch state, override start/stop, and restoration outcomes per Principle V.

**Post-Design Re-Evaluation**: Data model + contracts keep momentary control guarantees (override timers), reuse existing MQTT topics, remain Python-only, bound alert durations via config validation, and document new logging touchpoints—no gate violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/001-pilot-mode-switch/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ha-mqtt-contract.md
└── tasks.md   # to be produced during /speckit.tasks
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
lightspeed2mqtt/
├── simple-logi.py            # CLI entrypoint / MQTT service runner
├── lightspeed/
│   ├── config.py             # YAML parsing + validation
│   ├── mqtt.py               # MQTT loop, color/light handlers
│   ├── lighting.py           # Logitech LED control helpers
│   ├── ha_contracts.py       # Discovery payload generation
│   └── observability.py      # logging + structured status helpers
├── tests/
│   ├── test_mqtt_light.py
│   ├── test_ha_contracts.py
│   └── other config validation suites
├── docs/
│   └── validation/manual-verification.md
└── specs/
  └── 001-pilot-mode-switch/...
```

**Structure Decision**: Single Python service with top-level `simple-logi.py`, domain modules in `lightspeed/`, and pytest suites under `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
