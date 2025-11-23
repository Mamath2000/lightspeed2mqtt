# Implementation Plan: Logi Integration (Home Assistant MQTT)

**Branch**: `001-logi-integration` | **Date**: 2025-11-23 | **Spec**: `specs/001-logi-integration/spec.md`
**Input**: Feature specification from `/specs/001-logi-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Deliver a Python-only middleware update so Logitech keyboards appear in Home Assistant as a single MQTT-discovered device exposing alert, warning, RGB color, auto mode, and status entities. The service loads settings from `config.yaml`, publishes retained discovery and availability payloads, translates incoming MQTT commands into Logitech LED SDK actions, and reports health via LWT/status topics while keeping alert animations safe and interruptible.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13 (per Principle III)
**Primary Dependencies**: `logipy` (Logitech LED SDK bindings), `paho-mqtt`, `pyyaml` (safe_load), standard library (`asyncio`, `logging`, `pathlib`).
**Storage**: N/A (in-memory state only)
**Testing**: Pytest suite for config validation + discovery payload builders, plus documented manual MQTT/HA smoke tests until hardware stubs exist.
**Target Platform**: Windows 10/11 workstation running Logitech G HUB + Python runtime.
**Project Type**: Single script/service + CLI entrypoint (`simple-logi.py`).
**Performance Goals**: Handle MQTT command-to-SDK latency ≤300 ms median / 500 ms p95; discovery published ≤5 s after connect; alert termination ≤250 ms.
**Constraints**: Must honor Principles I–V, maintain CPU-lite pattern loops, and avoid introducing non-Python services.
**Scale/Scope**: Single user workstation; MQTT topics limited to one device; future multi-device support out-of-scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Principle I (Momentary Control)** – Resolved via research: shared Windows file lock + `LightingState` ensures CLI and MQTT coordinate, saving/restoring Logitech profile on Auto.
2. **Principle II (Explicit MQTT Contracts)** – Contracts documented in `contracts/home-assistant-mqtt.md`; no new payload schemas beyond documented topics.
3. **Principle III (Python-Only Surface)** – Implementation remains Python 3.13 using `logipy`, `paho-mqtt`, `pyyaml`; no new runtimes introduced.
4. **Principle IV (Safe Alert Patterns)** – `patterns.py` will cap frame durations to 500 ms/350 ms per research and remain interruptible via cooperative stop events.
5. **Principle V (Observable Operations)** – LWT + retained `health` topic and structured logging (topic, payload, outcome) defined in research + contracts.

**Post-Design Check**: Gates satisfied with concrete artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) establishing control strategy, MQTT schemas, and observability plan.

## Project Structure

### Documentation (this feature)

```text
specs/001-logi-integration/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── (MQTT discovery + entity schemas)
└── tasks.md             # Created during /speckit.tasks
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
├── simple-logi.py              # Current CLI + MQTT entrypoint (will be modularized)
├── requirements.txt            # logipy + paho-mqtt
├── README.md
├── LogitechLed.dll             # SDK dependency
├── specs/                      # Feature docs
├── .specify/                   # Spec Kit automation
├── .venv/
└── .github/

(To be introduced during implementation)
├── lightspeed/
│   ├── config.py               # YAML loader + validation logic
│   ├── mqtt.py                 # MQTT session + HA discovery
│   ├── ha_contracts.py         # Discovery payload builders
│   ├── lighting.py             # State + SDK control
│   └── patterns.py             # Alert/warning workers
└── tests/
  ├── test_config.py
  └── test_contracts.py
```

**Structure Decision**: Single Python project centered on `simple-logi.py` with planned `lightspeed/` package to keep config, MQTT, and lighting concerns separated; future tests live under `tests/` at repo root.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
