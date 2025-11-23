# Research Findings – Home Assistant MQTT Integration

## 1. Config Format & Loader

- **Decision**: Use `pyyaml`'s `safe_load` plus a lightweight schema validator (dataclasses + manual checks) for `config.yaml`.
- **Rationale**: `pyyaml` ships in most Python environments, has no compiled dependencies, and `safe_load` avoids executing arbitrary constructors. Dataclass validation keeps the constitution’s Python-only constraint while giving clear error messages for missing keys. The config remains human-editable and supports comments for device metadata and topic overrides.
- **Alternatives Considered**:
  - `ruamel.yaml`: preserves comments/ordering but adds a larger dependency and slower load times not needed for a boot-time config.
  - JSON/TOML: would drop YAML conveniences (anchors, comments) and conflict with the explicit config-file requirement already communicated to users.

## 2. Logitech Control Arbitration & Momentary Control

- **Decision**: Centralize Logitech LED access in a `LightingState` service guarded by a Windows file lock (`msvcrt.locking`) plus in-process `asyncio.Lock`. CLI commands and the MQTT worker both acquire the same lock before calling SDK routines; releasing Auto restores the saved profile and frees the lock.
- **Rationale**: File locks work across multiple Python processes without extra packages, satisfying Principle I and III. Storing the prior lighting snapshot in memory (and re-reading on startup) ensures alerts remain momentary. The shared lock prevents concurrent CLI and MQTT commands without forcing the user to disable one path.
- **Alternatives Considered**:
  - Separate watchdog daemon: violates Principle III (Python-only, single entrypoint) and adds operational burden.
  - In-memory flags only: would break when CLI runs in a separate process, leading to conflicting LED commands.

## 3. Home Assistant MQTT Discovery Payloads

- **Decision**: Publish five retained discovery configs: `button` (alert), `button` (warning), `light` (RGB with HS support), `switch` (auto/manual), and `binary_sensor` (availability) under the same `device` dictionary. Use entity-specific `command_topic`/`state_topic` pairs and reference the LWT topic via `availability` objects.
- **Rationale**: Aligns with HA’s documented entity types. Buttons suit momentary actions (stateless), the light entity supports color pickers, and the switch models manual/auto mode. A binary sensor covers service health in dashboards. Device-level discovery keeps Home Assistant grouping tidy and prevents duplicate devices.
- **Alternatives Considered**:
  - Use `select` entity for alert modes: adds UX friction and duplicates functionality offered by two simple buttons.
  - Custom device per entity: clutters HA UI and breaks the requirement for a single device-level discovery flow.

## 4. Availability, Logging, and Testing Strategy

- **Decision**: Implement MQTT LWT with `status` topic emitting `online/offline`, plus a retained JSON health topic summarizing controller state, last alert, and last error. Logging remains Python’s `logging` module with structured context (topic, payload summary, outcome). Testing adopts `pytest` with fixtures that stub MQTT (using `paho-mqtt`’s local loop) and config validation tests; manual HA smoke tests remain for full-stack verification until hardware simulation exists.
- **Rationale**: Retained availability topics are the HA best practice and satisfy Principle V. JSON health data gives debugging insight without scraping logs. `pytest` keeps dependencies minimal while letting us unit-test config parsing and discovery payload builders. Manual MQTT smoke instructions ensure reproducibility even without automation.
- **Alternatives Considered**:
  - External monitoring agent: overkill for a workstation-bound service and outside Principle III.
  - Rely only on logs for health: forces dashboards to parse text and gives no real-time signal when the service dies.
  - unittest module: works but lacks fixtures/parametrization convenience; pytest is already standard in repo discussions.
