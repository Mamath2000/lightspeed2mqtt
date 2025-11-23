# Implementation Plan: Config YAML Management

**Branch**: `001-config-yaml` | **Date**: 2025-11-23 | **Spec**: `specs/001-config-yaml/spec.md`
**Input**: Feature specification from `/specs/001-config-yaml/spec.md`

**Note**: This plan aligns the newly ratified Constitution v1.1.0 with the feature scope that replaces `.env` with a canonical `config.yaml` workflow.

## Summary

Replace the legacy `.env` runtime wiring with a cohesive YAML configuration system. The work introduces a schema-driven loader (`lightspeed/config.py`), CLI validation tooling, path override support, and documentation assets (`config.example.yaml`, Quickstart tables). All runtime modules (MQTT session, discovery contracts, CLI subcommands) consume the parsed dataclasses so Home Assistant metadata, MQTT credentials, and palette limits originate from a single file. Env-substitution keeps secrets out of source control while preserving the YAML structure as the source of truth.

## Technical Context

**Language/Version**: Python 3.13 (existing runtime per Principle III)  
**Primary Dependencies**: `pyyaml` (SafeLoader + custom constructors), `pydantic`-style validation is out-of-scope; rely on stdlib `dataclasses`, `typing`, and `pathlib`.  
**Storage**: No persistent storage; configs live on disk as YAML.  
**Testing**: `pytest` unit coverage for `load_config`, env substitution, and CLI validation flows. CLI harness uses `subprocess.run` or `click` testing utilities once adopted.  
**Target Platform**: Windows 10/11 workstation (NTFS paths, UNC support) with optional portability to WSL for dev.  
**Project Type**: Single Python script/service (`simple-logi.py`) with modular `lightspeed/` package.  
**Performance Goals**: Config parsing/validation completes <2s for 5KB files; CLI validation is CPU-light.  
**Constraints**: Honor Constitution gates (momentary control, explicit MQTT schemas, Python-only surface, safe alert patterns, observable operations). Ensure YAML parsing never touches the Logitech SDK or MQTT until validation succeeds.  
**Scale/Scope**: Single-device deployments; multi-device/multi-tenancy is deferred.

## Constitution Check

1. **Principle I – Momentary Control**: Config introduces `lighting` + `palettes` sections that store saved-state behavior. Loader enforces required restore flags so CLI/MQTT continue to release control on `auto`.  
2. **Principle II – Explicit MQTT Contracts**: Topics and HA device metadata move into YAML but schemas remain identical. Discovery payload builders will read from `TopicMap` without altering entity count or payload formats.  
3. **Principle III – Python-Only Surface**: Implementation relies on `pyyaml`, `dataclasses`, and existing tooling; no new runtimes or services are introduced.  
4. **Principle IV – Safe Alert Patterns**: Palette definitions inside YAML enforce frame caps (≤500 ms alert, ≤350 ms warning). Validation rejects values outside bounds before pattern threads start.  
5. **Principle V – Observable Operations**: Config path, version hash, and validation status are logged at startup and exported via the retained health topic. `validate-config` command prints structured results for SREs.  

*Status*: All gates satisfied by design; no waivers required.

## Project Structure

### Documentation (this feature)

```text
specs/001-config-yaml/
├── spec.md
├── plan.md              # This file
├── checklists/
│   └── requirements.md  # Completed spec review
```

### Source Code (repository root)

```text
lightspeed2mqtt/
├── simple-logi.py                 # Entry point; gains --config + validate-config wiring
├── config.example.yaml            # Canonical template kept in sync with schema
├── README.md / specs/**/quickstart.md  # Updated instructions referencing YAML flow
├── lightspeed/
│   ├── __init__.py
│   ├── config.py                  # NEW: dataclasses, schema validation, env substitution, loader API
│   ├── observability.py           # Adds config health metadata helpers
│   └── mqtt.py / ha_contracts.py  # Consume ConfigProfile instead of os.environ
├── tests/
│   ├── __init__.py
│   ├── test_config.py             # Parser, substitution, validation scenarios
│   └── test_cli_config.py         # CLI validation command (optional, stretch)
└── docs/
    └── validation/
        └── config-lint.md         # Procedure for manual validation (new)
```

**Structure Decision**: Retain single-project layout. Introduce `lightspeed/config.py` + tests to encapsulate parsing/validation and expose typed objects to existing modules. Documentation + example config live at repo root for discoverability.

## Implementation Phases

1. **Phase 0 – Tooling & Examples**  
   - Add `pyyaml` to `requirements.txt`.  
   - Create `config.example.yaml` with exhaustive comments plus a schema doc in `/docs/validation/config-lint.md`.  
   - Update README + Quickstart to reference YAML-only setup.

2. **Phase 1 – Config Loader Core (User Story 1)**  
   - Build dataclasses for `ConfigProfile`, `MqttSettings`, `TopicMap`, `PaletteDefinition`, etc.  
   - Implement `load_config(path)` with SafeLoader, env substitution (`${ENV_VAR}`), default injection, and strict validation (missing keys, invalid ranges).  
   - Comprehensive unit tests targeting success + failure cases.  
   - Replace all `os.environ[...]` usages in `simple-logi.py`, `lightspeed/mqtt.py`, `lightspeed/ha_contracts.py`, and pattern modules to consume the new objects.

3. **Phase 2 – Path Overrides & Validation CLI (User Story 2)**  
   - Add `--config` argument to every CLI command and `LOGI_CONFIG_PATH` fallback; centralize precedence logic.  
   - Implement `validate-config` (or `config validate`) CLI subcommand that loads + reports results without invoking MQTT/SDK.  
   - Emit structured logs and health payload updates referencing the resolved config path + validation timestamp.

4. **Phase 3 – Documentation & Drift Prevention (User Story 3)**  
   - Align `config.example.yaml`, README tables, Quickstart instructions, and spec docs using the same schema definitions.  
   - Add validation scripts/tests to ensure `config.example.yaml` remains valid.  
   - Publish manual validation checklist in `docs/validation/config-lint.md`.

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Parser rejects existing `.env`-only deployments | Service would fail to start | Ship `config.example.yaml`, migration guide, and CLI validator so users can translate env vars before upgrading |
| Env substitution resolves to empty string silently | MQTT credentials broken | Log warnings when `${VAR}` is missing; allow `strict_env=true` flag in config for hard-fail mode |
| Partial updates: YAML edited while service running | May read inconsistent file | Read entire file via `pathlib.Path.read_text()` before parsing; optionally use file timestamps to detect changes and prompt restart |
| Validation logic drifts from docs | Users copy stale keys | Keep docs + example validated in CI; add unit test that loads README table to ensure field names stay synchronized |

## Complexity Tracking

No Constitution violations or exceptions required; table intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| *(none)*  |            |                                      |
