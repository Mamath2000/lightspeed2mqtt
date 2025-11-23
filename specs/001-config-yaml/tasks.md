# Tasks: Config YAML Management

**Input**: `/specs/001-config-yaml/spec.md`, plan.md, constitution v1.1.0
**Prerequisites**: research handled in plan; this task list assumes the spec + plan are approved.

**Tests requested**: Unit coverage for config parser/validation/env substitution plus CLI validation flows. Docs + sample config must also pass automated validation.

**Organization**: Phases follow Spec Kit guidance—Setup → Foundational → User Stories (independent) → Polish.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Update `requirements.txt` to include `pyyaml` (pinned) and document the addition in `README.md` dependencies section.
- [X] T002 Add `config.example.yaml` at repo root with commented sections (`mqtt`, `topics`, `home_assistant`, `lighting`, `palettes`, `logitech`) to serve as the canonical template.
- [X] T003 Refresh configuration instructions in `README.md` and `specs/001-logi-integration/quickstart.md` so YAML replaces `.env`, including `--config` flag usage examples.
- [X] T004 Create `docs/validation/config-lint.md` describing manual validation steps, expected CLI outputs, and how to migrate from `.env`.

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 Implement `lightspeed/config.py` dataclasses (`ConfigProfile`, `MqttSettings`, `TopicMap`, `PaletteDefinition`, etc.) plus the `load_config(path: Path)` entrypoint with default handling.
- [x] T006 [P] Build validation helpers in `lightspeed/config.py` that enforce required keys, numeric ranges, and allowed enums before any MQTT/SDK usage.
- [x] T007 [P] Add env-substitution support (`${ENV_VAR}`) with logging for missing variables inside `lightspeed/config.py`.
- [x] T008 Create `tests/test_config.py` covering happy paths, missing keys, invalid palette durations, and env-substitution edge cases.
- [x] T009 Introduce a lightweight schema hash/version helper (e.g., `ConfigProfile.schema_revision()`) to expose in logs/health topics.

**Checkpoint**: A validated, typed config loader exists; no consumer should rely on `os.environ` anymore.

## Phase 3: User Story 1 – Single YAML Config Drives the Service (Priority: P1)

- [x] T010 [US1] Replace legacy env reads in `simple-logi.py` with calls to `load_config`, storing the resulting `ConfigProfile` for all subcommands.
- [x] T011 [P] [US1] Update `lightspeed/mqtt.py` to accept `MqttSettings` + `TopicMap` instead of raw env strings, ensuring LWT/discovery topics honor YAML values.
- [x] T012 [P] [US1] Update `lightspeed/ha_contracts.py` (and any other discovery helpers) to consume YAML-driven device metadata so HA payloads reflect the file contents.
- [x] T013 [US1] Wire palette/default-color fields from `ConfigProfile` into `lightspeed/lighting.py` and pattern modules, keeping Principle IV bounds enforced.
- [x] T014 [US1] Add structured startup logs + health payload updates (via `lightspeed/observability.py`) that record the resolved config path, schema hash, and validation timestamp.
- [x] T015 [US1] Document an independent validation walkthrough in `docs/validation/config-lint.md` showing `python simple-logi.py serve --config config.yaml` with expected MQTT/HA outcomes.

**Checkpoint**: Service can boot solely from YAML; HA metadata and MQTT credentials originate from the file.

## Phase 4: User Story 2 – Config Path Selection & Validation CLI (Priority: P1)

- [x] T016 [US2] Extend CLI parsing in `simple-logi.py` to accept `--config` for every subcommand and define precedence: CLI flag > `LOGI_CONFIG_PATH` > default `config.yaml`.
- [x] T017 [US2] Add a new `validate-config` (or `config validate`) subcommand that loads the file, prints success/failure summaries, and exits with proper codes without touching MQTT/SDK.
- [x] T018 [P] [US2] Implement tests in `tests/test_cli_config.py` for argument precedence, env override handling, and validator exit codes (use temp files & monkeypatching).
- [x] T019 [US2] Update `lightspeed/observability.py` + retained health topic to include config path + last validation result so operators can confirm which file is active.

**Checkpoint**: Operators can point at any YAML path, validate it independently, and observe its status via logs/health topics.

## Phase 5: User Story 3 – Canonical Example & Docs Stay in Sync (Priority: P2)

- [x] T020 [US3] Write a script or CI-friendly check (e.g., `tests/test_config_example.py`) that loads `config.example.yaml` to guarantee it passes validation.
- [x] T021 [US3] Ensure README tables, Quickstart snippets, and `config.example.yaml` share the same field list by generating or linting them via a shared helper.
- [x] T022 [US3] Add guidance to `docs/validation/config-lint.md` (and Quickstart) about copying the example file, filling secrets, running `validate-config`, and starting the service.
- [x] T023 [US3] Include a migration note in `README.md` (or `docs/migration/config.md`) explaining how to convert existing `.env` installations to `config.yaml` step-by-step.

**Checkpoint**: Documentation/examples never drift from the schema; onboarding follows a single, validated path.

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T024 [P] Add CI wiring (GitHub Actions or local script) to run `pytest -k config` plus `python simple-logi.py validate-config --config config.example.yaml` on every PR.
- [x] T025 [P] Capture release notes / CHANGELOG entry summarizing the YAML migration, validation tooling, and required operator actions.
- [x] T026 Perform an end-to-end manual verification: copy `config.example.yaml`, fill secrets, run validator, start the service, and confirm HA discovery plus color/alert topics still behave.

## Dependencies & Execution Order

- Setup (Phase 1) → Foundational (Phase 2) must complete before any user story begins.
- User Story 1 depends on the loader (T005–T009) and unlocks the YAML-only runtime; finish before shipping.
- User Story 2 can proceed once US1’s loader integration exposes `ConfigProfile` to CLI/MQTT modules.
- User Story 3 relies on the finalized schema + validation hooks to keep docs/examples current.
- Polish tasks follow all user stories and focus on CI + release communication.

## Parallel Execution Examples

- While T005 implements dataclasses, T006/T007 can run in parallel to flesh out validation and env substitution since they target different helpers.
- Once `load_config` exists, T011 (MQTT integration) and T012 (HA contracts) can proceed concurrently—one touches networking, the other discovery payloads.
- T018 (CLI tests) can run concurrently with T017’s CLI implementation once interfaces are defined, using mocks/temp files to avoid MQTT dependencies.
- T020 (config example validation) and T021 (doc lint) can be executed in parallel because they operate on different artifacts (example file vs documentation).

## Implementation Strategy

1. **MVP (US1)**: Finish Setup + Foundational work, then drive US1 to completion so the middleware boots purely from YAML and HA discovery matches the file. Ship this as the minimal viable change.
2. **Hardening (US2)**: Add path override support and validation CLI to reduce deployment risk; ensure operators can test configs before touching hardware.
3. **Docs/Drift Prevention (US3)**: Lock down examples + documentation so new users and upgrades follow the same path, then add CI/polish tasks to prevent regressions.

```diff
Legend:
- [ ] Pending task
[P] Parallel-capable task
[US#] User story association
```
