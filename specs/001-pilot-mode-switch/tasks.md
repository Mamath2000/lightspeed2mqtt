# Tasks: Pilot Mode Switch & Temporary Alerts

**Input**: plan.md, spec.md, research.md, data-model.md, contracts/
**Prerequisites**: Complete Setup → Foundational → User Stories (in priority order) → Polish

All tasks follow the `[ID] [P?] [Story] Description` checklist format with explicit file paths.

---

## Phase 1: Setup (Shared Infrastructure)

Prepare documentation and fixtures so the new pilot/override behaviors have clear templates before implementation.

- [x] T001 Update sample configuration defaults in `config.example.yaml` and `lightspeed/config_docs.py` to document `effects.override_duration_seconds` (1-300) plus pilot switch command/state topics.
- [x] T002 Add a pilot-mode profile fixture (or update existing mocks) in `tests/test_config_example.py` to ensure config sample + docs stay synchronized before schema work begins.

---

## Phase 2: Foundational (Blocking Prerequisites)

These tasks establish shared config/schema/state infrastructure required by every user story.

- [x] T003 Extend `lightspeed/config.py` (and validations in `tests/test_config.py` + `tests/test_cli_config.py`) to model pilot switch metadata, optional `topics.auto_state`, and `override_duration_seconds` range checks.
- [x] T004 Implement the `ControlMode`/`OverrideAction` helpers (new module `lightspeed/control_mode.py` or similar) and wire skeleton usage inside `lightspeed/mqtt.py` to track state, last color, brightness, and transition timestamps.
- [x] T005 Enhance logging/status utilities in `lightspeed/observability.py` and their usage in `lightspeed/mqtt.py` so every transition publishes `{mode, pilot_switch, light_state}` plus override metadata to `profile.topics.status`.

**Checkpoint**: Once Phase 2 completes, all user stories can be implemented independently.

---

## Phase 3: User Story 1 - Control keyboard ownership (Priority: P1) 🎯 MVP

**Goal**: Provide a Home Assistant switch that deterministically grants or releases keyboard control between the integration and Logitech Options+.

**Independent Test**: From HA, toggle the Pilot switch ON/OFF and confirm the MQTT service logs the mode change, applies colors only when ON, and restores Logitech control immediately when OFF.

### Tests for User Story 1

- [x] T006 [P] [US1] Update `tests/test_ha_contracts.py` to expect a `components.pilot_switch` entry (command + state topics) and removal of the legacy auto button payload.
- [x] T007 [P] [US1] Expand `tests/test_mqtt_light.py` to cover pilot switch command/state handling, including retained state replay and status publishing.

### Implementation for User Story 1

- [x] T008 [US1] Modify `lightspeed/ha_contracts.py` to emit the Pilot switch discovery payload using `profile.topics.auto` / `topics.auto_state`, aligned with the new config schema.
- [x] T009 [US1] Update `lightspeed/mqtt.py` to subscribe to the pilot switch topic, publish retained state, and transition the `ControlMode` between `pilot` and `off` while invoking Logitech restore helpers as needed.
- [x] T010 [US1] Ensure `simple-logi.py` bootstraps the pilot switch state at startup (reading retained MQTT state if available) and logs every ownership change via the observability helpers.

**Checkpoint**: MVP is shippable once US1 tasks + tests pass.

---

## Phase 4: User Story 2 - Respect light on/off semantics (Priority: P2)

**Goal**: Align the HA Light entity with keyboard ownership—turning the light off must release Logitech control, and turning it on must instantly restore the cached automation color when Pilot mode is active.

**Independent Test**: Toggle the HA Light entity off/on while observing the keyboard; Logitech should regain control during OFF, and the previously set RGB/brightness should return immediately upon ON when Pilot mode is still ON.

### Tests for User Story 2

- [x] T011 [P] [US2] Add ON/OFF flow coverage in `tests/test_mqtt_light.py` verifying cached color/brightness restoration and ignored color commands while the pilot switch is OFF.

### Implementation for User Story 2

- [x] T012 [US2] Enhance `lightspeed/mqtt.py` to persist the last `{rgb, brightness}` payload, ignore new color commands whenever the pilot switch or Light entity is OFF, and call `LogiLedRestoreLighting()` the moment HA reports OFF.
- [x] T013 [US2] Add helper routines in `lightspeed/lighting.py` to atomically restore Logitech defaults and reapply cached colors during Pilot reactivation, minimizing flicker.

---

## Phase 5: User Story 3 - Temporary alert and warning overrides (Priority: P3)

**Goal**: Allow Alert/Warning buttons to temporarily override keyboard colors for a configurable duration, then automatically revert to the prior Pilot or Off state.

**Independent Test**: Trigger Alert and Warning from HA; each should run for exactly the configured duration, update status to `override_*`, cancel cleanly when the other button or Pilot switch changes, and finally return to the correct base mode/color.

### Tests for User Story 3

- [x] T014 [P] [US3] Extend `tests/test_mqtt_light.py` with timer-based Alert/Warning scenarios validating duration enforcement, cancellation when states change, and color restoration.

### Implementation for User Story 3

- [x] T015 [US3] Implement override scheduling in `lightspeed/mqtt.py` (e.g., `threading.Timer`) using the `OverrideAction` helper so only one override runs at a time, respecting the config-sourced duration and canceling on new commands.
- [x] T016 [US3] Publish override state transitions (and invalid-duration warnings) using `lightspeed/observability.py`, ensuring `topics.status` reflects `override_alert` / `override_warning` and reverts to `pilot`/`off` afterward.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T017 [P] Refresh user-facing docs (`README.md`, `docs/validation/manual-verification.md`, `specs/001-pilot-mode-switch/quickstart.md`) with pilot switch workflows, override duration guidance, and manual validation steps.
- [x] T018 Summarize the feature in `CHANGELOG.md` (and any release notes) plus rerun `python simple-logi.py serve --config config.yaml` to capture proof of the validation checklist.

---

## Dependencies & Execution Order

1. Phase 1 tasks unblock config/schema edits and must finish before foundational work.
2. Phase 2 establishes shared config/state/logging infrastructure—ALL user stories depend on T003–T005.
3. User Story phases proceed in priority order (US1 → US2 → US3) but can run in parallel once foundational tasks are complete if different contributors own them.
4. Polish tasks depend on completion of every targeted user story.

## Parallel Execution Examples

- **US1**: Run T006 and T007 (tests) concurrently while another developer implements T008/T009.
- **US2**: T011 can execute in parallel with T012 once cached-color hooks exist; T013 can proceed independently as long as the ControlMode helper is available.
- **US3**: T014 (tests) may run alongside T015 (scheduler implementation) because both rely on the shared ControlMode abstractions; T016 follows once timers emit events.

## Implementation Strategy

1. **MVP First**: Complete Phases 1–2, then deliver US1 (Pilot switch control). Validate independently via the HA switch + logs.
2. **Incremental Delivery**: Layer US2 (Light ON/OFF semantics) and demo once cached color restoration works. Add US3 overrides last, as it builds on cached color + Pilot states.
3. **Parallel Staffing**: After Phase 2, dedicate separate owners to each user story using the parallel opportunities above while keeping tests close to their implementations.

---
