# Tasks: Logi Integration (Home Assistant MQTT)

**Input**: Design documents from `/specs/001-logi-integration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Targeted pytest coverage is requested for config validation, discovery payloads, and MQTT handlers. Manual HA smoke tests remain part of each story's acceptance.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stage dependencies, scaffolding, and documentation to support the new Python-only workflow.

- [ ] T001 Update `requirements.txt` to include `pyyaml` and refresh pinned versions for `logipy`/`paho-mqtt`.
- [ ] T002 Create `config.example.yaml` at the repo root, showing all supported keys (MQTT, topics, HA device block, palettes, dll path override).
- [ ] T003 Scaffold the `lightspeed/` package (`__init__.py`, placeholders for config/mqtt/lighting/patterns modules) plus `tests/` package stubs to unblock later work.
- [ ] T004 Refresh `README.md` and `specs/001-logi-integration/quickstart.md` sections that explain config-driven setup and HA discovery expectations.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core modules that every story depends on (config loader, Logitech arbitration, MQTT session skeleton, CLI wiring).

- [ ] T005 Implement `lightspeed/config.py` dataclasses + `load_config(path)` with schema validation and helpful error messages.
- [ ] T006 [P] Add `tests/test_config.py` to cover happy-path parsing, defaults, and validation failures (missing host, invalid palette frames).
- [ ] T007 Implement `lightspeed/lighting.py` with `LightingState`, Windows file lock via `msvcrt.locking`, and helpers to save/restore Logitech profiles (no color logic yet).
- [ ] T008 Implement shared logging + health helpers in `lightspeed/observability.py` (structured logging config + retained health payload composer).
- [ ] T009 Build `lightspeed/mqtt.py` connection manager: configure client ID, keepalive, LWT to `<base>/status`, reconnect loop hooks, and dependency injection for command handlers (no HA publishing yet).
- [ ] T010 Refactor `simple-logi.py` to instantiate the new modules for `serve`, `color`, `alert`, `warning`, `auto` commands while deferring story-specific logic to later phases.

**Checkpoint**: Config loading, locking, MQTT lifecycle, and CLI/bootstrap paths exist so user stories can build on stable primitives.

---

## Phase 3: User Story 1 – Home Assistant Auto-Discovers the Device (Priority: P1) 🎯 MVP

**Goal**: Publish retained HA discovery payloads and availability signals so the "Logitech Alerts" device (buttons, light, switch, status) appears automatically.

**Independent Test**: Start `python simple-logi.py serve --config config.yaml`; within 5 s verify one HA device with five entities is created via MQTT discovery, and `status` flips `online`/`offline` on reconnect.

### Implementation & Tests (US1)

- [ ] T011 [P] [US1] Implement `lightspeed/ha_contracts.py` builders that map `ConfigProfile` into button/light/switch/binary_sensor payloads using the shared device object.
- [ ] T012 [P] [US1] Add `tests/test_ha_contracts.py` covering payload shapes (topics, availability blocks, device identifiers) and regression cases.
- [ ] T013 [US1] Extend `lightspeed/mqtt.py` to publish retained discovery payloads + `<base>/status` availability on connect/reconnect, honoring config overrides.
- [ ] T014 [US1] Wire `serve` startup in `simple-logi.py` to call the discovery publisher, log completion, and surface errors when MQTT or config fails.
- [ ] T015 [US1] Document HA validation steps in `docs/validation/logi-ha-discovery.md` (new file) so QA can reproduce the independent test.

**Checkpoint**: User Story 1 delivers an MVP—the HA device exists with availability tracking.

---

## Phase 4: User Story 2 – Control Color & Auto Mode from HA (Priority: P1)

**Goal**: Allow HA to set RGB colors and toggle Auto/Manual ownership via MQTT topics, including state feedback and CLI parity.

**Independent Test**: From HA, set the light entity to `#33AAFF` and observe the keyboard change within 300 ms; toggle the Auto switch and confirm Logitech software regains control with accurate state topics.

### Implementation & Tests (US2)

- [ ] T016 [P] [US2] Implement color payload parsing + normalization helpers in `lightspeed/payloads.py` (support JSON, `#RRGGBB`, and `R,G,B`).
- [ ] T017 [P] [US2] Add `tests/test_payloads.py` to cover accepted formats, invalid payload errors, and conversion edge cases (e.g., lowercase hex).
- [ ] T018 [US2] Extend `lightspeed/lighting.py` to apply static colors, store `current_color`, and restore Logitech profile when Auto is requested.
- [ ] T019 [US2] Implement MQTT handlers in `lightspeed/mqtt.py` for `<base>/color/set`, `<base>/auto/set`, including state topic publishing (`<base>/color/state`, `<base>/auto/state`) and retention rules.
- [ ] T020 [US2] Update `simple-logi.py` CLI subcommands (`color`, `auto`) to reuse the shared helpers and mark conflicts when the MQTT worker currently holds the lock.

**Checkpoint**: User Stories 1 and 2 both function independently; the system can be shipped as an MVP (discovery + basic control).

---

## Phase 5: User Story 3 – Trigger Alert & Warning Animations (Priority: P2)

**Goal**: Provide HA buttons (and CLI) that launch high-contrast or amber alert patterns, remain interruptible, and update state/health accordingly.

**Independent Test**: Trigger the Alert button; the keyboard cycles red/white/black until Auto or a color command interrupts within 250 ms; repeat for Warning with amber/black.

### Implementation & Tests

- [ ] T021 [P] [US3] Implement `lightspeed/patterns.py` async workers for alert & warning palettes, using the frame durations from config and cooperative stop events.
- [ ] T022 [P] [US3] Add `tests/test_patterns.py` with faked Logitech SDK + time controls to ensure patterns honor frame caps (≤500 ms alert, ≤350 ms warning) and stop on interrupts.
- [ ] T023 [US3] Add MQTT handlers in `lightspeed/mqtt.py` for `<base>/alert/set` and `<base>/warning/set`, ensuring they transition `LightingState`, emit `<base>/color/state` attributes (`effect=alert|warning`), and log outcomes.
- [ ] T024 [US3] Enhance `simple-logi.py` alert/warning CLI commands to delegate into the new pattern API and publish stop events on exit signals so manual control remains momentary.

**Checkpoint**: All user stories operate independently; alerting adds the final differentiator.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidate docs, troubleshooting, and validation across all stories.

- [ ] T025 [P] Add a troubleshooting section to `README.md` covering MQTT connectivity, Logitech DLL issues, and interpreting the `health` topic.
- [ ] T026 [P] Create `docs/validation/logi-ha-smoketest.md` summarizing manual HA test matrices (discovery, color, auto, alert, warning) with expected outcomes.
- [ ] T027 Run through `specs/001-logi-integration/quickstart.md` step-by-step and update screenshots/log snippets to reflect the finished workflow.

---

## Dependencies & Execution Order

- **Phase dependencies**: Setup → Foundational → User Stories (US1/US2/US3 may proceed in priority order once Foundational completes) → Polish.
- **User story order**: US1 (discovery MVP) must finish before shipping; US2 builds on the same topics but is independently testable after Foundational; US3 depends on the color/auto infrastructure but can start once the pattern module scaffolding exists.
- **Task-level sequencing**:
  - Config loader (T005) precedes its tests (T006) and all later modules that consume `ConfigProfile`.
  - Lighting lock (T007) precedes MQTT handlers that manipulate the keyboard.
  - Discovery publishing (T013) depends on HA payload builders (T011) and MQTT base (T009).
  - Pattern handlers (T023) depend on the shared pattern workers (T021) and color state publisher (T019).

## Parallel Execution Examples

- **User Story 1**: T011 (HA payload builders) and T012 (payload tests) can run in parallel; once finished, T013 (discovery publish) can begin while T015 (validation doc) is drafted.
- **User Story 2**: T016 (parser helpers) and T017 (parser tests) can proceed concurrently; T018 (lighting apply) can start once T007 is done, while T019 (MQTT handlers) waits for T016/T018 and then runs alongside T020 (CLI integration).
- **User Story 3**: T021 (pattern workers) and T022 (pattern tests) run together; after they pass, T023 (MQTT buttons) and T024 (CLI wiring) can be tackled concurrently by different developers.

## Implementation Strategy

1. **MVP First**: Complete Phases 1–2, then finish US1 to deliver a discoverable HA device with availability. Validate manually using the new doc before moving on.
2. **Incremental Delivery**: Ship US2 next (color + auto). It reuses the same config/topics but can be tested independently—ideal checkpoint before introducing alert complexity.
3. **Alert Enhancements**: Implement US3 once static color control is stable. Patterns rely on the same lighting lock, so regressions are easy to spot via the health topic.
4. **Observability & Docs**: Use the Polish phase to finalize README/quickstart/troubleshooting plus the validation matrices, ensuring Principle V remains satisfied before release.

```diff
Legend:
- [ ] Pending task
[P] Parallel-capable task
[US#] User story association
```
