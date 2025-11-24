# Feature Specification: Base-Relative Topic Schema

**Feature Branch**: `001-update-topics-schema`  
**Created**: 2025-11-24  
**Status**: Draft  
**Input**: "la gestion des topic ne me va pas ... ajouter un topic {base}/lwt avec l'état de l'application online/offline."

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

### User Story 1 - Base-Derived Topics (Priority: P1)

As an operator, I want every canonical MQTT topic (`power`, `mode`, `color`, `brightness`, `alert`, `status`, `lwt`) in `config.yaml` to be defined as a suffix relative to `topics.base`, so that changing the base automatically updates the entire contract and keeps deployments consistent.

**Why this priority**: Eliminates mismatched topic names (current pain point) and guarantees that documentation + config stay aligned with a single source of truth.

**Independent Test**: Configure `topics.base: lightspeed`, set suffixes `power: power`, `mode: mode`, `color: color`, `brightness: brightness`, `alert: alert`, `status: status`, `lwt: lwt`. Start the service and assert that MQTT subscriptions/publishes happen exactly on `lightspeed/<suffix>` with no manual concatenation.

**Acceptance Scenarios**:

1. **Given** a profile with `topics.base = lightspeed` and `topics.status = status`, **When** the service publishes status, **Then** the message is sent to `lightspeed/status` and the retained payload mirrors the structured status JSON.
2. **Given** `topics.color = color` and `topics.brightness = brightness`, **When** Home Assistant publishes retained JSON commands to `lightspeed/color` or `lightspeed/brightness`, **Then** the service consumes them, updates cached values, and republishes the same payloads (retained) so HA dashboards resync after restart.

---

### User Story 2 - Pilot Mode Topic (Priority: P1)

As a Home Assistant user, I want a single retained `topics.mode` channel (payloads `pilot` or `logi`) to both command and reflect the Pilot switch so that ownership of the keyboard is unambiguous and survives reconnects.

**Why this priority**: Pilot control is central to the automation flow; a dedicated topic with deterministic semantics removes confusion and ensures retained state survives HA reconnects.

**Independent Test**: With the service running, publish retained payload `pilot` to `<base>/mode` and observe the keyboard enter automation mode. Publish retained payload `logi` and confirm the service restores Logitech lighting and shuts down the DLL connection.

**Acceptance Scenarios**:

1. **Given** the service is connected and `topics.mode` currently equals `logi`, **When** a retained payload `pilot` arrives on `<base>/mode`, **Then** Pilot mode activates, cached color/brightness is replayed, and the service republishes `pilot` (retained) so HA mirrors the state.
2. **Given** Pilot mode is active, **When** a retained payload `logi` is published to `<base>/mode`, **Then** the middleware restores Logitech control, shuts down the DLL session, and republishes `logi` as confirmation.

---

### User Story 3 - JSON Alerts & LWT (Priority: P2)

As an automation designer, I want the middleware to consume JSON overrides on `<base>/alert` and to expose an explicit `<base>/lwt` topic broadcasting `online`/`offline`, so downstream dashboards react uniformly to overrides and availability.

**Why this priority**: A single JSON contract keeps alert metadata consistent with the constitution, and a predictable LWT topic is critical for watchdogs that must know when the middleware is down.

**Independent Test**: Publish retained `online` via `paho-mqtt` to `<base>/lwt` on connect and configure broker LWT to emit `offline`. Trigger Alert/Warning buttons by sending `{ "type": "alert" }` or `{ "type": "warning" }` to `<base>/alert` and verify the middleware respects timers while logging the event.

**Acceptance Scenarios**:

1. **Given** the service receives `{ "type": "alert" }` on `<base>/alert`, **When** it begins the override, **Then** it validates payload fields, logs the request, enforces duration bounds, and resumes the prior mode when the override completes.
2. **Given** the MQTT broker forcibly disconnects, **When** the session ends, **Then** Home Assistant and monitoring tools see `<base>/lwt` change to `offline` via the broker’s Last Will message without additional configuration per topic.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Base suffix contains a leading/trailing slash. System must normalize to avoid `//` or missing separators when composing `<base>/<suffix>`.
- `topics.color` payload omits brightness metadata; middleware should replay the last retained brightness so HA state remains consistent.
- `topics.mode` receives an unknown string (neither `pilot` nor `logi`). Middleware should default to handing control back (`logi`) and log the invalid value.
- `<base>/alert` receives bursts (e.g., `{ "type": "alert" }` followed immediately by `{ "type": "warning" }`). Only one override may run at a time and the latest payload wins without leaving timers orphaned.
- Broker drops retained `topics.color` payload; service restart should republish cached color/brightness so HA state remains consistent even if the broker cleared retention.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: `topics.base` MUST represent the full namespace root (e.g., `lightspeed`) and every other topic entry MUST be defined as a suffix relative to this base; the system concatenates them as `<base>/<suffix>` when subscribing/publishing.
- **FR-002**: The configuration MUST expose the canonical fields `power`, `mode`, `color`, `brightness`, `alert`, `status`, and `lwt` inside `TopicMap`, each stored as a suffix yet derived to absolute topics at runtime.
- **FR-003**: `topics.status` MUST store only the suffix (e.g., `status`), and the middleware MUST publish structured status JSON to `<base>/<topics.status>` while keeping the payload schema unchanged (state + attributes).
- **FR-004**: `topics.mode` MUST be the authoritative retained channel where payload `pilot` enables integration control, payload `logi` relinquishes control, and any other value is rejected with a validation log. Transitioning to `logi` MUST immediately shut down the Logitech DLL session and restore saved lighting.
- **FR-005**: Publishing to `topics.color` or `topics.brightness` MUST imply `topics.power = ON`, update cached values, and republish retained confirmations so HA dashboards stay in sync; `topics.power` payloads `ON`/`OFF` remain the source of truth for ownership.
- **FR-006**: `topics.alert` MUST accept JSON payloads containing `{ "type": "alert" | "warning" | "info" }` and optional `{ "duration": int }` (1–300s). The middleware MUST validate payloads, enforce override timers, and log processing outcomes.
- **FR-007**: `topics.lwt` MUST be published as retained `online` on connect, and the MQTT Last Will MUST emit retained `offline` on the same topic when the session drops unexpectedly.
- **FR-008**: All derived topics (power, mode, color, brightness, alert, status, lwt, future additions) MUST reject absolute paths containing `/` when validation detects they would double-prefix the base, providing actionable config errors.
- **FR-009**: Documentation (`README`, quickstarts, sample config) MUST reflect the canonical topics plus the new LWT requirement, including example payloads (retained flags, JSON schemas, mode semantics) and removal of legacy `auto`, `warning`, or `<base>/event` references.

### Key Entities *(include if feature involves data)*

- **TopicMap**: Logical representation containing `base`, `power`, `mode`, `color`, `brightness`, `alert`, `status`, `lwt`, derived command/state relationships, and validation rules ensuring suffix-only values.
- **ModeMessage**: Conceptual payload placed on `<base>/mode`, including allowed values (`pilot`, `logi`), retain flag expectations, and the resulting ControlMode transition.
- **AlertRequest**: JSON payload placed on `<base>/alert` that instructs the middleware which override to run (`type` + optional `duration`) alongside any future metadata the docs may permit.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Updating only `topics.base` in `config.yaml` MUST re-point every derived topic (power, mode, color, brightness, alert, status, lwt) without further edits, confirmed by a single integration test run.
- **SC-002**: Pilot mode toggles via `<base>/mode` MUST apply within 1 second and publish the retained confirmation payload, verified over three consecutive toggles.
- **SC-003**: Alert and warning triggers routed through `<base>/alert` (JSON payloads) MUST achieve 100% success across 10 manual invocations while respecting configured override durations.
- **SC-004**: MQTT watchdogs subscribing to `<base>/lwt` MUST observe `offline` within broker-configured LWT timeout when the service is killed, and `online` within 2 seconds of reconnect.

## Assumptions

- Documentation and schema will treat suffix-only entries as required; advanced users no longer need to provide fully-qualified topic strings.
- Home Assistant will continue to use JSON schema for the light entity; switching to `<base>/color` does not change payload structure beyond the retained requirement.
- `logi` is the canonical payload meaning “Logitech takes control.” Any other payloads MUST be rejected with warning logs to avoid silent misconfiguration.
