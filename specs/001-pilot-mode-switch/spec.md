# Feature Specification: Pilot Mode Switch & Temporary Alerts

**Feature Branch**: `001-pilot-mode-switch`  
**Created**: 2025-11-24  
**Status**: Draft  
**Input**: User description: "ok super, il faut gerer differemment le mode auto: voila la spec: le programme a deux mode : pilote (les couleurs du clavier sont envoyees par HA sur le composant Light) et off (quand on eteint la lumiere, le programme redonne la main a Logitech). Il faut remplacer le mode auto par un switch pilote: si le switch est on, le programme controle le clavier, si le switch est off, Logitech le controle. Les actions Alert et Warning doivent etre temporaires (ex: 10 s configurable dans config.yml); apres ce delai, on revient au mode precedent et, si pilote est actif, on re-applique la bonne couleur."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Control keyboard ownership (Priority: P1)

Operators can toggle a Home Assistant switch to decide whether the integration or Logitech Options+ controls the keyboard lighting.

**Why this priority**: Without a deterministic way to release control, users cannot quickly return to Logitech defaults or enforce automation-driven colors on demand.

**Independent Test**: Toggle the switch from HA and observe that keyboard control transfers within seconds while MQTT topics acknowledge the new state.

**Acceptance Scenarios**:

1. **Given** the service is running in Off mode, **When** the user sets the Pilot switch to "on", **Then** the integration claims lighting control, reenables the Light component, and future color commands take effect.
2. **Given** the service is in Pilot mode, **When** the user sets the Pilot switch to "off", **Then** the integration stops issuing color changes and Logitech regains control without additional user input.

---

### User Story 2 - Respect light on/off semantics (Priority: P2)

Home Assistant users expect that turning the Light entity off hands control back to Logitech, and turning it on reapplies the last requested automation color if Pilot mode is enabled.

**Why this priority**: Aligning with HA lighting semantics avoids inconsistent states where the UI says "off" but the keyboard continues to emit automation-driven colors.

**Independent Test**: Toggle the Light entity while observing the keyboard and MQTT logs, ensuring the switch and Light entity remain synchronized.

**Acceptance Scenarios**:

1. **Given** Pilot mode is enabled, **When** the user turns the Light entity off, **Then** the integration enters Off mode, releases the keyboard, and marks the light as off.
2. **Given** the light was turned off previously, **When** the user turns it back on while the Pilot switch remains on, **Then** the previously commanded RGB color (and brightness) is restored without flicker.

---

### User Story 3 - Temporary alert and warning overrides (Priority: P3)

Automations can invoke Alert or Warning buttons to override current colors for a configurable duration, after which the keyboard resumes whichever mode was active previously.

**Why this priority**: Incident responders need short-lived overrides to draw attention without permanently desynchronizing lighting behavior.

**Independent Test**: Trigger each button and verify the override lasts exactly the configured number of seconds, then automatically reverts and, if in Pilot mode, reapplies the last automation color.

**Acceptance Scenarios**:

1. **Given** Pilot mode is active with a set color, **When** the Alert button is pressed, **Then** the keyboard shows the alert pattern for the configured duration before returning to the prior color and brightness.
2. **Given** the system is in Off mode, **When** Warning is pressed, **Then** the override still occurs for the configured duration, and afterward the device returns to Logitech-managed lighting without extra steps.

---

### Edge Cases

- How does the system behave if the Pilot switch changes while an Alert/Warning override is active?
- What happens when HA sends a light-off command while the switch remains on but an override is active?
- How does the service react if the configured override duration is missing, zero, or exceeds safe limits?
- What if MQTT connectivity drops mid-override; does the system still ensure eventual reversion?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide a Home Assistant switch entity (replacing the former Auto button) whose "on" state enables Pilot mode and whose "off" state releases lighting control to Logitech.
- **FR-002**: When Pilot mode is "on", the Light entity must accept RGB + brightness commands and apply them immediately; when "off", incoming Light commands must be ignored or acknowledged without altering keyboard colors.
- **FR-003**: Turning the Light entity off must force Off mode regardless of switch state, persist the last requested RGB/brightness, and ensure Logitech resumes control until the Light entity is turned on again.
- **FR-004**: Turning the Light entity back on while the Pilot switch remains "on" must reapply the last stored RGB color, brightness, and effect within 1 second without requiring a new MQTT payload.
- **FR-005**: Provide separate Alert and Warning button entities whose activation triggers their respective lighting patterns for a configurable duration defined in `config.yml` (default 10 seconds).
- **FR-006**: After an Alert/Warning override elapses, the service must resume the previously active mode (Pilot or Off) and restore either the stored automation color (Pilot) or Logitech control (Off) without user intervention.
- **FR-007**: Override timers must be cancelable when the other button is pressed or when the Light/Switch state changes, ensuring that only one override runs at a time.
- **FR-008**: The new configuration parameter(s) must pass existing validation rules, support per-profile overrides, and reject invalid values (non-numeric, negative, or exceeding safe maximum, e.g., 300 seconds) with actionable error messages.
- **FR-009**: Discovery payloads must reflect the new switch entity, remove the deprecated Auto button, and expose metadata so HA can represent the switch and buttons correctly with availability topics.
- **FR-010**: Status telemetry must indicate which mode is active (Pilot, Off, or Override) so dashboards and troubleshooting scripts can confirm state transitions.

### Key Entities *(include if feature involves data)*

- **ControlMode**: Represents the current ownership of lighting (pilot, off, override). Stores the active source, timestamps for transitions, and the last automation color payload for restoration.
- **OverrideAction**: Captures metadata about the active Alert/Warning override (type, remaining seconds, requested effect) and enforces single-active override semantics.
- **Configuration Profile**: Extends existing `config.yml` structures with fields such as `override_duration_seconds` (default 10) and optional per-action durations, ensuring per-profile validation and documentation.

### Assumptions

- Override duration is a single shared value for Alert and Warning; if different values are needed later, the configuration schema can be extended.
- Pilot mode remains the default after service start if the switch entity reports "on"; otherwise the system starts in Off mode respecting Logitech control.
- Alert/Warning patterns reuse existing lighting effects; only their duration handling changes in this iteration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Pilot switch toggles propagate to the keyboard within 2 seconds, confirmed via logs during manual verification.
- **SC-002**: Turning the Light entity off and back on restores the last automation color (hue + brightness) in at least 95% of regression test runs.
- **SC-003**: Alert and Warning overrides automatically end within +/- 1 second of the configured duration in 30 consecutive automated tests.
- **SC-004**: Configuration validation rejects invalid override durations with actionable error text in 100% of negative test cases, preventing the service from starting with unsafe values.
