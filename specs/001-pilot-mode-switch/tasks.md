# Tasks: Pilot Mode Switch & Temporary Alerts

**Input**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Prerequisites**: Complete phases sequentially (Setup → Foundational → US1 → US2 → US3 → Polish)

All tasks follow `[ID] [P?] [Story] Description` with explicit file paths.

---

## Phase 1: Setup (Shared Infrastructure)

Capture prerequisite documentation and fixtures so development and validation share the same baseline.

- [ ] T001 Document the pilot switch + override validation prerequisites in `docs/validation/manual-verification.md` (broker info, required HA entities, Logitech prerequisites).
- [ ] T002 [P] Expand the prerequisites section in `specs/001-pilot-mode-switch/quickstart.md` to describe the HA sandbox setup, retained topics, and the `override_duration_seconds` knob before implementation begins.
- [ ] T003 [P] Update `config.example.yaml` to show `topics.auto_state`, retained status topic expectations, and default `effects.override_duration_seconds` so downstream schema tasks have an authoritative sample.

---

## Phase 2: Foundational (Blocking Prerequisites)

Finish shared schema/state plumbing required by every user story before building story-specific behavior.

- [ ] T004 Extend `lightspeed/config.py` plus validation tests (`tests/test_config.py`, `tests/test_cli_config.py`) to parse pilot switch metadata, optional `topics.auto_state`, and clamp `effects.override_duration_seconds` to 1–300 seconds.
- [ ] T005 [P] Regenerate configuration docs in `lightspeed/config_docs.py` (and ensure `docs/validation/manual-verification.md` references the new fields) so operators know how to set the pilot switch topics.
- [ ] T006 Implement the `ControlMode` / `OverrideAction` structures in `lightspeed/control_mode.py` to store pilot switch flags, last `{rgb, brightness}` payloads, monotonic timestamps, and optional override state shared by all stories.
- [ ] T007 Publish the richer status payload from `lightspeed/observability.py` (referenced by `lightspeed/mqtt.py`) so every transition emits `{mode, pilot_switch, light_state, override_type, remaining_seconds}` to `profile.topics.status`.

**Checkpoint**: Do not start any user story until T004–T007 are complete.

---

## Phase 3: User Story 1 – Control keyboard ownership (Priority: P1) 🎯 MVP

**Goal**: Provide a Home Assistant switch that deterministically grants or releases keyboard control between the service and Logitech software.

**Independent Test**: Toggle the Pilot switch in HA; within two seconds the service must publish retained state, set mode=`pilot` on ON, invoke `LogiLedRestoreLighting()` on OFF, and ignore color commands while OFF.

### Implementation & Tests (US1)

- [ ] T008 [P] [US1] Update `tests/test_ha_contracts.py` and `tests/test_mqtt_light.py` to expect the new Pilot switch discovery payload plus retained `topics.auto_state` behavior.
- [ ] T009 [US1] Modify `lightspeed/ha_contracts.py` to emit `components.pilot_switch` using `profile.topics.auto`/`topics.auto_state`, replacing the legacy Auto button entry.
- [ ] T010 [US1] Teach `lightspeed/mqtt.py` to subscribe to the pilot switch topic, persist retained switch state, and drive `ControlMode` transitions (`pilot ↔ off`) while publishing acknowledgments to `topics.auto_state`.
- [ ] T011 [US1] Ensure `simple-logi.py` (and any CLI startup path) initializes `ControlMode` with the retained switch state and logs every ownership change through `lightspeed/observability.py`.

**Parallel Opportunities (US1)**: T008 can run concurrently with T009–T011 because contract/tests work independently from MQTT wiring.

**Checkpoint**: MVP is complete when US1 tasks pass and HA can command ownership reliably.

---

## Phase 4: User Story 2 – Respect light on/off semantics (Priority: P2)

**Goal**: Align Light entity behavior with ownership; OFF must hand control back to Logitech, ON must replay the cached automation color instantly when Pilot mode is ON.

**Independent Test**: With Pilot ON, send Light `OFF` → keyboard reverts to Logitech within 1 s. Send Light `ON` (no color payload) → cached color/brightness reapplies in <1 s. With Pilot OFF, light color commands log `ignored_pilot_off` and do not change the keyboard.

### Implementation & Tests (US2)

- [ ] T012 [P] [US2] Expand `tests/test_mqtt_light.py` and `tests/test_control_mode.py` to cover light OFF releasing control, ON restoring cached `{rgb, brightness}`, and ignoring colors while Pilot OFF.
- [ ] T013 [US2] Enhance `lightspeed/control_mode.py` to cache the most recent `{rgb, brightness}`, persist Light entity state, and expose helpers for “apply cached color” vs “release to Logitech”.
- [ ] T014 [US2] Update `lightspeed/mqtt.py` to invoke the new helpers: publish retained light state payloads, release control whenever HA sends OFF, and guard ON commands behind Pilot ON checks.
- [ ] T015 [US2] Adjust `lightspeed/lighting.py` (and palettes if needed) so Logitech restore + cached-color replay happen atomically, minimizing flicker.

**Parallel Opportunities (US2)**: T012 can execute alongside T013–T015; within implementation, T013 (state helpers) unlocks T014 and T015, which can then run in parallel.

---

## Phase 5: User Story 3 – Temporary alert and warning overrides (Priority: P3)

**Goal**: Alert/Warning buttons temporarily override colors for a configurable duration, then automatically revert to the prior Pilot or Off mode.

**Independent Test**: Trigger Alert then Warning: each publishes `mode=override_*`, honors the configured duration (default 10 s), cancels when the other button fires or the Pilot/Light state changes, and restores the cached base color or Logitech control when finished.

### Implementation & Tests (US3)

- [ ] T016 [P] [US3] Add override-duration coverage in `tests/test_control_mode.py` and `tests/test_mqtt_light.py`, asserting timer cancellation, invalid-duration rejection, and state restoration.
- [ ] T017 [US3] Implement the single active `OverrideAction` timer in `lightspeed/control_mode.py` (monotonic clock, cancellation hooks, remaining-seconds calculations for telemetry).
- [ ] T018 [US3] Wire Alert/Warning MQTT handlers in `lightspeed/mqtt.py` to call the new scheduler, clamp payload-provided durations, and publish override-specific status updates.
- [ ] T019 [US3] Emit retained status + observability logs for `override_*` transitions in `lightspeed/observability.py`, ensuring dashboards see `override_type` and countdown metadata.

**Parallel Opportunities (US3)**: T016 (tests) can run in parallel with T017–T019 once the foundational ControlMode work exists; T018/T019 can also proceed concurrently after timer primitives land.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T020 [P] Update user-facing docs (`README.md`, `specs/001-pilot-mode-switch/quickstart.md`, `docs/validation/manual-verification.md`) to describe Pilot switch workflows, override durations, and manual validation checklists.
- [ ] T021 Refresh `specs/001-pilot-mode-switch/contracts/ha-mqtt-contract.md` and `docs/validation/manual-verification.md` screenshots/logs to match the new retained status payload.
- [ ] T022 Summarize the feature in `CHANGELOG.md` and capture a validation proof (logs or screenshots) referenced from `docs/validation/manual-verification.md`.

---

## Dependencies & Execution Order

1. **Setup → Foundational**: Documentation + config samples (T001–T003) unblock schema changes; T004–T007 must finish before any user story work.
2. **User Story Order**: US1 (T008–T011) delivers the MVP Pilot switch and is a dependency for US2/US3 because they rely on the ControlMode ownership semantics. US2 (T012–T015) must complete before US3 final verification to ensure cached colors exist for override restoration.
3. **Polish**: T020–T022 run after all targeted user stories succeed so docs and changelog reflect final behavior.

Dependency graph (story level): `Setup → Foundational → US1 → (US2, then US3) → Polish`.

---

## Parallel Execution Examples

- **US1**: T008 (tests) can proceed while T009 (contracts) and T010–T011 (MQTT + CLI wiring) implement command handling; once ControlMode transitions exist, tasks do not conflict.
- **US2**: After T013 creates caching helpers, T014 (MQTT) and T015 (lighting) can execute simultaneously, while T012 keeps refining regression coverage.
- **US3**: T016 tests run while T017 builds the timer helper; as soon as T017 lands, T018 (MQTT) and T019 (telemetry) can advance in parallel.

---

## Implementation Strategy

1. **MVP First**: Deliver Setup + Foundational + US1 to unblock HA operators with a deterministic ownership switch.
2. **Incremental Delivery**: Ship US2 next (restoring Light semantics) so cached colors behave before layering override complexity; demo after each story.
3. **Final Enhancements**: Implement US3 overrides, then complete documentation/changelog polish to prep release notes.

MVP scope = Phase 3 (US1). Each subsequent phase adds functionality without regressing earlier stories, enabling staged rollouts.

---
