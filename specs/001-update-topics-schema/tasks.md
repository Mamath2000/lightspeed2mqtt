# Tasks: Base-Relative Topic Schema

**Input**: plan.md, spec.md, existing code/tests under `lightspeed2mqtt/`
**Prerequisites**: Constitution 1.2.0 (canonical `power`, `mode`, `color`, `brightness`, `alert` topics) and branch `001-update-topics-schema`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the current vs target MQTT topic contract so downstream phases agree on canonical names and payloads.

- [X] T001 Summarize legacy vs canonical MQTT topics and payloads in `specs/001-update-topics-schema/research.md`
- [X] T002 Record the updated `TopicMap` entity (base + power/mode/color/brightness/alert/status/lwt fields) in `specs/001-update-topics-schema/data-model.md`
- [X] T003 Describe the Home Assistant MQTT contract (publish/subscribe expectations, retained flags) in `specs/001-update-topics-schema/contracts/ha-mqtt-contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ensure configuration loading, docs, and samples derive every canonical topic from `topics.base` before runtime logic changes.

- [X] T004 Refactor canonical topic derivation + validation (suffix enforcement, retained state topics) in `lightspeed/config.py`
- [X] T005 Refresh field descriptions so `power/mode/color/brightness/alert` guidance matches the constitution in `lightspeed/config_docs.py`
- [X] T006 Rewrite the canonical topic examples (base + suffixes) in `config.example.yaml`
- [X] T007 Expand suffix-validation & default-topic coverage for the new `TopicMap` in `tests/test_config.py`
- [X] T008 Align the config docs snapshot with the updated topic list in `tests/test_config_docs.py`
- [X] T009 Adjust CLI config fixtures to expect derived topics only in `tests/test_cli_config.py`

**Checkpoint**: Topic derivation is centralized; runtime files may now rely on `TopicMap` exclusively.

---

## Phase 3: User Story 1 - Base-Derived Topics (Priority: P1) 🎯 MVP

**Goal**: Every runtime component (MQTT handlers, discovery payloads, observability) consumes the derived `TopicMap`, preventing manual string concatenation and guaranteeing a single source of truth per canonical topic.

**Independent Test**: Configure `topics.base = lightspeed/alerts` with suffix overrides, start the service, and observe subscriptions/publishes only on the derived topics (`lightspeed/alerts/power`, etc.) while Home Assistant discovery reflects the same subjects.

### Implementation Tasks

- [X] T010 [US1] Route all MQTT subscriptions/publishes through `TopicMap` (power/mode/color/brightness/alert + retained state mirrors) in `lightspeed/mqtt.py`
- [X] T011 [P] [US1] Emit derived canonical topics inside the Home Assistant discovery payloads in `lightspeed/ha_contracts.py`
- [X] T012 [US1] Publish health/status JSON via the derived `topics.status` (formerly manual) in `lightspeed/observability.py`
- [X] T013 [P] [US1] Assert derived topics in MQTT light end-to-end tests (color & brightness retaining) in `tests/test_mqtt_light.py`

**Checkpoint**: With `TopicMap` enforced everywhere, base changes alone redirect the integration. This is the MVP slice.

---

## Phase 4: User Story 2 - Pilot Mode Topic (Priority: P1)

**Goal**: A single retained `topics.mode` channel (payloads `pilot`/`logi`) orchestrates control handoff, ensures cached color replay, and restores Logitech immediately when leaving Pilot mode.

**Independent Test**: Publish retained `pilot` to `<base>/mode` and verify keyboards enter Pilot mode plus confirm the middleware republishes `pilot`. Publish retained `logi` and confirm Logitech control resumes, the DLL session shuts down, and the retained state flips.

### Implementation Tasks

- [X] T014 [US2] Enforce `pilot`/`logi` payload handling and mode persistence in `lightspeed/control_mode.py`
- [X] T015 [US2] Handle retained `topics.mode` commands (including associated `topics.power` side effects) in `lightspeed/mqtt.py`
- [X] T016 [P] [US2] Ensure lighting restore/lockfile logic respects the new mode semantics in `lightspeed/lighting.py`
- [X] T017 [P] [US2] Cover control-mode transitions and retained payload cases in `tests/test_control_mode.py`

**Checkpoint**: Pilot mode switching is deterministic and reflected over MQTT without relying on deprecated `auto` topics.

---

## Phase 5: User Story 3 - JSON Alerts & LWT (Priority: P2)

**Goal**: Alert/warning overrides flow through the canonical JSON `topics.alert`, and availability is exposed via `topics.lwt` with MQTT Last Will semantics for `online`/`offline`.

**Independent Test**: Trigger `{"type":"alert"}` on `<base>/alert` to start the override and log the run, then kill the process and verify the broker emits retained `offline` on `<base>/lwt`; restart and confirm `online` is republished.

### Implementation Tasks

- [X] T018 [US3] Parse JSON payloads on `topics.alert`, enforce duration bounds, and coordinate override lifecycles in `lightspeed/mqtt.py`
- [X] T019 [P] [US3] Publish retained availability and configure MQTT Last Will on `topics.lwt` in `lightspeed/observability.py`
- [X] T020 [P] [US3] Advertise the alert service & LWT topics in `lightspeed/ha_contracts.py`
- [X] T021 [US3] Expand MQTT alert/LWT coverage (JSON parsing, retained online/offline) in `tests/test_mqtt_light.py`
- [X] T022 [P] [US3] Validate Home Assistant discovery reflects alert + LWT entities in `tests/test_ha_contracts.py`

**Checkpoint**: Automations can react uniformly to overrides and service availability.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Align surfaced docs and release notes with the canonical topic catalog and new control semantics.

- [X] T023 Document the canonical topic catalog, retained payloads, and pilot workflow updates in `README.md`
- [X] T024 Update manual verification steps (including MQTT scripts for mode/alert/status) in `docs/validation/manual-verification.md`
- [X] T025 Capture the schema change + upgrade notes in `CHANGELOG.md`

---

## Dependencies & Execution Order

1. **Setup ➜ Foundational**: Tasks T001–T003 must complete before code changes so every contributor references the same canonical topic definitions.
2. **Foundational ➜ US1**: T004–T009 unblock runtime refactors by guaranteeing `TopicMap` fidelity.
3. **US1 (MVP)**: T010–T013 deliver a working system with base-derived topics. Later stories build atop this slice.
4. **US2 depends on US1 outputs**: Control-mode handling (T014–T017) assumes MQTT handlers already consume `TopicMap`.
5. **US3 depends on US1 + US2 infrastructure**: Alert and LWT work (T018–T022) require derived topics plus stable mode/power ownership.
6. **Polish**: T023–T025 run last once all behavior is verified.

Visual order: `Setup → Foundational → US1 → {US2, US3} → Polish` (US2 should start before/alongside US3 only after US1 completes).

## Parallel Execution Examples

- **US1**: T011 and T013 can proceed while T010 refactors the MQTT client because they operate on different files (`lightspeed/ha_contracts.py`, `tests/test_mqtt_light.py`).
- **US2**: T016 (lighting restore logic) can run in parallel with T017 (tests) once T014 defines the new mode semantics.
- **US3**: T019 (observability) and T020 (HA contracts) are independent of T018’s alert parser and can execute concurrently after US1 infrastructure lands.

## Implementation Strategy

1. **MVP (US1 only)**: Complete Setup + Foundational + US1 (T001–T013). Ship this slice so operators immediately benefit from base-derived canonical topics.
2. **Increment 2 (US2)**: Layer in the dedicated mode topic (T014–T017) to stabilize pilot/logi ownership. Validate independently before merging.
3. **Increment 3 (US3)**: Add alert JSON + availability (T018–T022) and confirm watchdog scenarios.
4. **Polish**: Update docs and changelog (T023–T025) once behavior is frozen.

Each increment is independently testable and can be demonstrated to stakeholders before proceeding.
