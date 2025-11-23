# Feature Specification: Config YAML Management

**Feature Branch**: `001-config-yaml`  
**Created**: 2025-11-23  
**Status**: Draft  
**Input**: User description: "peux tu integrer la gestion du fichier config.yaml"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Single YAML Config Drives the Service (Priority: P1)

Operators define every runtime setting (MQTT access, HA device metadata, topic layout, palettes, default colors, DLL overrides) in one `config.yaml`, and the middleware loads it before touching MQTT or the Logitech SDK.

**Why this priority**: Without a trusted config source the rest of the Logitech middleware cannot boot safely or advertise the right entities.

**Independent Test**: Provide a complete `config.yaml`, run `python simple-logi.py serve --config config.yaml`, and verify startup succeeds, MQTT credentials match the file, and HA discovery metadata reflects the YAML contents.

**Acceptance Scenarios**:

1. **Given** a syntactically valid file containing all required sections, **When** the service starts, **Then** it loads the YAML, materializes a `ConfigProfile`, and uses those values for MQTT connection, discovery payloads, and Logitech DLL path without referencing `.env`.
2. **Given** the file is missing a required field (for example `mqtt.host`), **When** the service parses it, **Then** startup aborts before any MQTT connection occurs and the log/error message points to the missing key and section.

---

### User Story 2 - Config Path Selection & Validation CLI (Priority: P1)

Site Reliability Engineers need to validate a YAML file and choose a non-default path (ex: shared config directory) without editing code. A dedicated validation command reports pass/fail and shows every schema violation.

**Why this priority**: Config mistakes are the primary failure mode during deployment; fast validation avoids MQTT outages.

**Independent Test**: Run `python simple-logi.py validate-config --config some.yaml`. With a valid file the command exits 0 within 2 seconds; with a bad file it exits non-zero and enumerates the errors. Repeat using a different path to ensure overrides work.

**Acceptance Scenarios**:

1. **Given** an alternate path is supplied via `--config` or `LOGI_CONFIG_PATH`, **When** any command runs, **Then** the loader uses that file (not the default) and all downstream modules receive the resulting `ConfigProfile`.
2. **Given** an invalid YAML (wrong type on `topics.base`), **When** `validate-config` executes, **Then** it lists the offending key, explains the allowed format, and returns exit code 1 without attempting Logitech SDK access.

---

### User Story 3 - Canonical Example & Docs Stay in Sync (Priority: P2)

Documentation owners need a single `config.example.yaml` plus Quickstart snippets that reflect the same schema so new users can copy, fill, and run without hidden defaults.

**Why this priority**: Accurate examples reduce onboarding friction and keep Principle V (observable operations) grounded in reality.

**Independent Test**: Regenerate or lint `config.example.yaml`, compare it against the schema, and confirm Quickstart instructions reference the same keys. Manual reviewers load the example file (after filling secrets) and see the service start without edits.

**Acceptance Scenarios**:

1. **Given** schema updates add a new field (e.g., `home_assistant.area`), **When** docs are rebuilt, **Then** `config.example.yaml` and the README/Quickstart tables include the new field with descriptive comments before release.
2. **Given** a user copies `config.example.yaml`, sets credentials, and runs the validation command, **When** they start the service, **Then** it publishes HA discovery without additional configuration steps.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Config file missing or unreadable: service must stop immediately with guidance to run `python simple-logi.py generate-config` or copy the example file.
- YAML syntax errors: display the parser line/column and highlight the failing block while ensuring no partial config is used.
- Unknown keys or deprecated fields: warn but continue (unless flagged as fatal) so upgrades remain backward-compatible.
- Secrets stored via environment variables: allow `${ENV_VAR}` substitution but warn if the referenced variable is empty.
- Concurrency: when CLI commands and the daemon read the same config simultaneously, file locking/read consistency must avoid partial reads.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: Provide a canonical YAML schema covering at least `mqtt`, `topics`, `home_assistant`, `lighting`, `palettes`, and `logitech` sections, each with documented defaults and type constraints.
- **FR-002**: Default to `config.yaml` next to `simple-logi.py`, while allowing overrides via `--config <path>` CLI flag and `LOGI_CONFIG_PATH` environment variable with a deterministic precedence order (CLI > env > default).
- **FR-003**: Implement a `load_config(path)` helper that produces immutable dataclasses (`ConfigProfile`, `MqttSettings`, etc.) consumed by every runtime component (MQTT, discovery, CLI, patterns) without falling back to `.env`.
- **FR-004**: Validate required fields, numeric ranges (e.g., palette frame durations), and enumerations (e.g., device class) before any network or SDK calls; failures must raise descriptive exceptions and halt startup.
- **FR-005**: Add a `validate-config` (or equivalent) CLI subcommand that loads the file, prints a success summary, or lists every validation error with exit code 1.
- **FR-006**: Support optional `${ENV_VAR}` tokens inside YAML values so credentials can remain in env vars while structure stays in YAML, and log when substitutions resolve to empty strings.
- **FR-007**: Maintain `config.example.yaml` via the same schema tooling, including inline comments for every key, and ensure CI/test coverage keeps it valid.
- **FR-008**: Emit structured logs/health metadata that include the resolved config path, version hash, and last validation timestamp to satisfy Principle V.
- **FR-009**: Provide developer-facing unit tests for the parser, validation rules, and substitution logic to guarantee regressions are caught before release.

### Key Entities *(include if feature involves data)*

- **ConfigProfile**: Root dataclass that aggregates all nested sections plus derived values (topic prefixes, default palette objects) and exposes read-only helpers for the rest of the service.
- **MqttSettings**: Sub-entity containing host, port, credentials (with env substitution metadata), client ID, keepalive, and LWT topics.
- **TopicMap**: Normalized collection of concrete MQTT topics (color, alert, warning, auto, status, discovery base) derived from `topics.base` and entity names.
- **PaletteDefinition**: Describes alert/warning frames, colors, and max durations to enforce Principle IV; referenced by both CLI patterns and the MQTT worker.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of malformed or incomplete `config.yaml` files are rejected before any MQTT socket is opened, confirmed by automated tests that cover each required section.
- **SC-002**: Running `simple-logi.py validate-config --config <file>` on a 5 KB file completes in under 2 seconds on a reference workstation and returns exit code 0 (success) or 1 (failure) consistently.
- **SC-003**: Editing only the YAML file (no code changes) must be sufficient to update MQTT credentials or HA metadata, evidenced by Home Assistant reflecting changes on the very next service start in 95% of manual verification attempts.
- **SC-004**: `config.example.yaml` and the Quickstart table pass validation in CI for every release tag, ensuring documentation and schema never diverge.

## Assumptions

- Secrets that must not live in source control can be referenced via `${ENV_NAME}` placeholders, but the YAML structure remains the single source of truth.
- Hot reload of configuration is out of scope; users restart the service after editing the file.
- Windows remains the deployment target, so file paths and locking semantics should assume NTFS but keep POSIX compatibility where easy.

