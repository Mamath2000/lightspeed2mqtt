<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles: Architecture Constraints – Configuration bullet now mandates `config.yaml` instead of `.env`
- Added sections: none
- Removed sections: none
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (no `.env` references; no change required)
  - ✅ .specify/templates/spec-template.md (already neutral on configuration medium)
  - ✅ .specify/templates/tasks-template.md (no action; tasks continue to reference config loader work)
- Follow-up TODOs: none
-->

# Lightspeed Alerts Constitution

## Core Principles

### I. Momentary Control (Non-Negotiable)

The middleware may take over Logitech lighting only to render an alert and MUST always save, restore, or release control on `auto` requests or process exit. Any feature proposal must state how it preserves the user's prior lighting profile and prove that the takeover duration is finite.

### II. Explicit MQTT Contracts

All capabilities are triggered via MQTT topics (`color`, `alert`, `warning`, `auto`). Payload formats are limited to `#RRGGBB`, `R,G,B`, or `{ "r":int, "g":int, "b":int }`. Specifications, plans, and code reviews must reject changes that introduce additional schemas or undocumented topics.

### III. Python-Only Surface

The runtime stack is Python 3.13+, `logipy`, `paho-mqtt`, and the Logitech LED SDK DLL. Reintroducing Node.js, extra daemons, or dependency bloat requires a separately approved experiment and a reversible migration plan.

### IV. Safe Alert Patterns

Alert effects must use bounded intervals (≤500 ms per frame), deterministic palettes (red/white/black for alerts, amber/black for warnings), and provide a defined stop condition. No new effect can bypass the stop flag or block the main MQTT loop.

### V. Observable Operations

Every message handling path logs topic, parsed intent, and outcome (success, validation failure, SDK error). Health indicators (e.g., retained status topic or CLI output) must expose whether lighting control is currently held or released.

## Architecture Constraints

- **Hardware & SDK**: LogitechLed.dll must reside next to `simple-logi.py` or be referenced via `LOGI_LED_DLL`. The service saves lighting state once per session and never assumes exclusive device ownership.
- **Runtime Layout**: Single Python entrypoint supporting `serve`, `color`, `alert`, `warning`, `auto` sub-commands. MQTT handling runs in one thread, while visual patterns run on background workers guarded by stop events.
- **Configuration**: `config.yaml` (or a CLI-provided YAML path) defines MQTT broker settings, discovery metadata, topic prefixes, palettes, and Logitech DLL overrides. A tracked `config.example.yaml` serves as the canonical template, and startup HALTs if required keys are missing or malformed.
- **Performance Envelope**: The service must process MQTT messages within 100 ms of receipt and keep CPU usage negligible by sleeping between pattern frames.

## Workflow & Quality Gates

- **Spec Kit Order**: Always run `/speckit.constitution` → `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`. Skip steps only when documented as out-of-scope experiments.
- **Constitution Check Items** (must appear in every plan):
  1. Does the change preserve Principle I (save/restore path)?
  2. Are MQTT payloads unchanged or clearly versioned per Principle II?
  3. Does the solution rely solely on Python dependencies per Principle III?
  4. Are alert intervals and palettes within Principle IV bounds?
  5. Where are logs/emitted metrics recorded to satisfy Principle V?
- **Testing Expectations**: Each user story describes the MQTT scenarios it covers and provides a repeatable manual validation note (e.g., publish payload X → observe pattern Y → send `auto`). Automated tests (unit or smoke scripts) must stub MQTT bindings when hardware access is unavailable.
- **Release Protocol**: Before tagging a release, run the CLI `auto` command to ensure lighting is restored, then document the tested MQTT topics in the release notes.

## Governance

- This constitution supersedes any ad-hoc practices. Reviews must cite the principle or gate being satisfied (or justify variance in the plan's Complexity Tracking table).
- **Versioning**: MAJOR for adding/removing principles or altering governance, MINOR for new sections or expanded guidance, PATCH for clarifications that do not change intent.
- **Amendments**: Proposed via `/speckit.constitution` with reasoning, impact assessment, and template sync notes. Approval requires consensus between stakeholders responsible for MQTT infrastructure and hardware usage.
- **Compliance**: `/speckit.plan` and `/speckit.tasks` outputs must explicitly document how each user story honors these principles before `/speckit.implement` begins.

//**Version**: 1.1.0 | **Ratified**: 2025-11-23 | **Last Amended**: 2025-11-23
