# Feature Specification: Logi Integration (Home Assistant MQTT)

**Feature Branch**: `001-logi-integration`  
**Created**: 2025-11-23  
**Status**: Draft  
**Input**: User description: "Le programme reste en attente d'une commande sur MQTT, doit se déclarer dans Home Assistant via MQTT discovery en tant qu'appareil unique avec boutons alerte/warning, light couleur, switch auto, plus un statut via LWT, tout paramétré via fichier de configuration."

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

### User Story 1 - Home Assistant Auto-Discovers the Device (Priority: P1)

On startup the middleware loads `config.yaml`, connects to MQTT, and publishes the required Home Assistant discovery payloads (device info plus entities for Alert, Warning, RGB light, Auto switch, status sensor) so the Logitech Alerts device appears automatically.

**Why this priority**: Discovery is the entry point—without it, Home Assistant users cannot see or control the device.

**Independent Test**: Start the service against a test broker and confirm HA creates exactly one device with all entities within 5 seconds, even after service restarts.

**Acceptance Scenarios**:

1. **Given** a valid config file and reachable broker, **When** the service starts, **Then** retained discovery payloads for all entities are published referencing the same device descriptor, making the device visible in HA.
2. **Given** discovery data already exists, **When** the config changes (e.g., new friendly name), **Then** the next startup republishes updated payloads and HA reflects the changes without duplicates.

---

### User Story 2 - Control Color & Auto Mode from HA (Priority: P1)

Users adjust the RGB light entity to set specific colors and toggle the Auto switch to hand control back to Logitech software when alerts are done.

**Why this priority**: Direct color control plus the ability to relinquish control are the core day-to-day interactions.

**Independent Test**: From HA, set the light to `#33AAFF` and observe the keyboard change within 300 ms; toggle Auto on and verify the keyboard resumes its native effect.

**Acceptance Scenarios**:

1. **Given** the device is available, **When** a color payload arrives on the light command topic, **Then** the middleware applies that color, updates HA state, and maintains it until another command arrives.
2. **Given** the service currently drives the keyboard, **When** the Auto switch is turned on, **Then** the middleware restores the saved Logitech profile, marks itself "idle", and publishes the new state topics within 250 ms.

---

### User Story 3 - Trigger Alert & Warning Animations (Priority: P2)

From HA dashboards, operators press Alert or Warning buttons that fire predefined red/white/black or amber/black animations, reverting gracefully when superseded or stopped.

**Why this priority**: Alerting differentiates the project; severity-specific palettes communicate urgency.

**Independent Test**: Press Alert in HA and confirm the keyboard pulses red/white/black until Auto or Color interrupts; press Warning to see amber/black pulses with the same interruptible behavior.

**Acceptance Scenarios**:

1. **Given** manual mode is active, **When** Alert is pressed, **Then** the high-contrast pattern begins within 200 ms and sets HA state attributes (`effect=alert`, `active=true`).
2. **Given** any effect is running, **When** Warning is pressed, **Then** the amber pulse replaces the current effect, and a second Warning press stops it (idempotent stop behavior).

---

No additional stories are needed for this feature slice.

### Edge Cases

- Missing or malformed `config.yaml` causes startup to halt with actionable error messaging; service never connects to MQTT with partial settings.
- MQTT broker unavailable at startup triggers exponential backoff retries and ensures the HA availability topic stays `offline` until a successful connect.
- LogitechLed.dll or G HUB unavailable results in status sensor reporting `hardware_unavailable` while still keeping MQTT alive for future retries.
- Conflicting commands (e.g., color during alert) cancel the running pattern, apply the latest request, and update HA states so dashboards remain truthful.
- If HA sends rapid repeated commands, the middleware debounces identical payloads to avoid flooding the Logitech SDK while still acknowledging each MQTT message.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The service MUST load runtime parameters (MQTT host/port, credentials, topic prefixes, device metadata, palette timings, default color, Logitech DLL overrides) from a single config file (`config.yaml` by default) and validate presence/format before connecting.
- **FR-002**: On startup and mqtt reconnect, the service MUST publish Home Assistant MQTT discovery payloads for one device that exposes exactly: Alert button, Warning button, RGB light, Auto switch, binary status sensor, all referencing the same device identifiers.
- **FR-003**: Each discovered entity MUST define retained state and availability topics; the service MUST keep those topics synchronized with actual controller state (manual vs auto, current effect, health).
- **FR-004**: MQTT command handlers MUST transform HA payloads into Logitech SDK actions: RGB values to static color, alert/warning to pulsing macros, auto to the SDK's restore-control capability, ensuring interrupts happen within 250 ms.
- **FR-005**: The MQTT connection MUST configure Last Will/Testament to publish `status=offline`; upon healthy connection it MUST publish `status=online` every reconnect and keep it retained for subscribers.
- **FR-006**: Alert and Warning patterns MUST be non-blocking and cancelable; receiving Auto or a new color must stop the running pattern and apply the requested state without requiring a process restart.
- **FR-007**: Logging MUST record config load results, MQTT connect/disconnect, each command received (topic + payload + outcome), and any Logitech SDK errors to satisfy observability requirements.
- **FR-008**: The existing local CLI control MUST reuse the same config loader and coordinate with the MQTT worker to prevent concurrent conflicting control (e.g., via file lock or IPC flag).
- **FR-009**: The service MUST expose a retained health topic summarizing `connected`, `controller_state`, `last_alert`, and most recent error message so HA can surface readiness without parsing logs.

### Key Entities *(include if feature involves data)*

- **ConfigProfile**: Parsed configuration object containing MQTT credentials, discovery metadata (device id, manufacturer, model), topic prefixes, palette definitions, default colors, and hardware paths.
- **HaDeviceDescriptor**: Data structure describing the HA device and its child entities, reused for discovery and status updates.
- **LightingState**: Tracks manual/auto state, active effect, current color, and saved Logitech profile so the system can restore momentary control.
- **MqttSession**: Manages connection lifecycle, subscriptions, retained discovery/status messages, and LWT settings.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: HA must show all entities within 5 seconds of service startup or reconnect in 95% of attempts.
- **SC-002**: Color or Auto commands triggered from HA must reflect on the keyboard within 300 ms median / 500 ms p95 of the MQTT message arrival.
- **SC-003**: Alert/warning effects must terminate and yield to Auto or Color commands within 250 ms.
- **SC-004**: The status binary_sensor must flip to unavailable within 2× the MQTT keep-alive interval if the service crashes or disconnects unexpectedly.
- **SC-005**: Configuration errors must be reported before MQTT connection, with human-readable messages that allow users to fix issues without reading code (≥90% of setup issues resolved via logs alone).

## Assumptions

- Configuration uses YAML stored at `config.yaml` by default and can be overridden via CLI flag or env var.
- MQTT broker is reachable over TCP (no TLS mutual auth required for this iteration); username/password support is sufficient.
- LogitechLed.dll is already present on the host; the feature focuses on discovery/control, not SDK installation.
