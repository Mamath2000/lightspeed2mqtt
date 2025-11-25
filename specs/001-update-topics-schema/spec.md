# Feature Specification: Simplified MQTT Topic Schema

**Feature Branch**: `001-update-topics-schema`  
**Created**: 2025-11-24  
**Updated**: 2025-11-25  
**Status**: Implemented  
**Input**: "C'est trop compliqué et l'utilisation de spec.kit n'est pas concluent. Dans la config je ne veux que le base topic."

## User Scenarios & Testing

### User Story 1 - Base Topic Only (Priority: P1)

As an operator, I want to configure only `topics.base` in `config.yaml`, with all other topics derived as fixed suffixes (`/status`, `/switch`, `/rgb/set`, `/brightness/set`, `/mode/set`, `/alert`, `/warn`, `/info`, `/lwt`), so that configuration is simple and consistent.

**Why this priority**: Eliminates complex topic configuration and ensures consistency across all deployments.

**Independent Test**: Configure `topics.base: lightspeed` and verify all topics are automatically generated as `lightspeed/status`, `lightspeed/switch`, etc.

**Acceptance Scenarios**:

1. **Given** a profile with `topics.base = lightspeed`, **When** the service starts, **Then** it subscribes to `lightspeed/switch`, `lightspeed/rgb/set`, `lightspeed/brightness/set`, `lightspeed/mode/set`, `lightspeed/alert`, `lightspeed/warn`, `lightspeed/info`.
2. **Given** the service is running, **When** it publishes state, **Then** the message is sent to `lightspeed/status` with full state JSON (state, rgb, brightness, mode).

---

### User Story 2 - Home Assistant Light Component (Priority: P1)

As a Home Assistant user, I want a single Light component that controls RGB color and brightness on my Logitech keyboard when in pilot mode, so I can integrate it with my existing lighting automations.

**Why this priority**: Light component is the primary interface for Home Assistant users.

**Independent Test**: Toggle the light on/off in Home Assistant and observe keyboard state changes. Change RGB and brightness and verify keyboard reflects the changes (in pilot mode only).

**Acceptance Scenarios**:

1. **Given** pilot mode is ON and light is ON, **When** I change RGB to red in HA, **Then** keyboard turns red within 1 second.
2. **Given** pilot mode is ON, **When** I turn the light OFF, **Then** keyboard turns black (0,0,0).
3. **Given** pilot mode is OFF, **When** I change light state in HA, **Then** keyboard is not affected (Logitech controls it).

---

### User Story 3 - Pilot/Auto Mode Switch (Priority: P1)

As a Home Assistant user, I want a Mode switch that controls whether the program pilots my keyboard (pilot) or lets Logitech software control it (auto), so I can easily switch between automation and manual control.

**Why this priority**: Essential for controlling when the program should manipulate the keyboard vs letting Logitech manage it.

**Independent Test**: Toggle mode switch in HA between pilot and auto, verify keyboard behavior changes accordingly.

**Acceptance Scenarios**:

1. **Given** mode is pilot, **When** I switch to auto, **Then** Logitech resumes control and keyboard returns to its original colors.
2. **Given** mode is auto, **When** I switch to pilot, **Then** program takes control and applies current light state to keyboard.

---

### User Story 4 - Visual Alert Buttons (Priority: P2)

As an automation designer, I want 3 separate buttons (Alert, Warn, Info) that trigger visual patterns on the keyboard regardless of light state or mode, so I can get immediate visual notifications.

**Why this priority**: Visual alerts should work even when program is not piloting the keyboard, providing critical notifications.

**Independent Test**: Press each alert button and verify corresponding pattern plays on keyboard, then keyboard returns to appropriate state (Logitech control if auto mode, light state if pilot mode).

**Acceptance Scenarios**:

1. **Given** mode is auto, **When** I press Alert button, **Then** red pattern plays, then Logitech control is restored.
2. **Given** mode is pilot and light is off, **When** I press Warn button, **Then** orange pattern plays, then keyboard returns to black.
3. **Given** mode is pilot and light is on, **When** I press Info button, **Then** blue pattern plays, then keyboard returns to light color/brightness.

---

### User Story 5 - LWT & State Retention (Priority: P2)

As a monitoring system, I want an LWT topic showing online/offline status and retained state that survives restarts, so I can track service availability and restore previous settings.

**Why this priority**: Critical for monitoring and ensuring consistent state across restarts.

**Independent Test**: Kill service and verify LWT shows offline. Restart service and verify it restores previous light state, mode, colors, and brightness from retained MQTT messages.

**Acceptance Scenarios**:

1. **Given** service is running, **When** I kill the process, **Then** `lightspeed/lwt` shows `offline` within 2 seconds.
2. **Given** light was on with blue color at 50% brightness in pilot mode, **When** service restarts, **Then** it reads retained state and applies blue at 50% to keyboard.

---

### Edge Cases

- Base suffix contains leading/trailing slashes. System normalizes to avoid `//`.
- Light state changes while in auto mode - keyboard is not affected.
- Alert triggered while another alert is running - new alert interrupts previous one.
- Mode switch toggled during alert - alert completes, then mode change applies.
- Brightness command received as dict vs int - both formats handled correctly.

## Requirements

### Functional Requirements

- **FR-001**: `topics.base` MUST be the only configurable topic field; all other topics are generated as `{base}/status`, `{base}/switch`, `{base}/rgb/set`, `{base}/brightness/set`, `{base}/mode/set`, `{base}/alert`, `{base}/warn`, `{base}/info`, `{base}/lwt`.
- **FR-002**: Light component MUST publish full state to `{base}/status` as retained JSON containing `state` (on/off), `rgb` (array), `brightness` (0-255), `mode` (pilot/auto).
- **FR-003**: Light commands MUST be received on `{base}/switch` (on/off), `{base}/rgb/set` (R,G,B), `{base}/brightness/set` (0-255).
- **FR-004**: Mode switch MUST use `{base}/mode/set` for commands (payload: "pilot" or "auto") and read state from `{base}/status` JSON field `mode`.
- **FR-005**: Alert buttons MUST use `{base}/alert`, `{base}/warn`, `{base}/info` with payload "press" to trigger visual patterns.
- **FR-006**: Pilot mode MUST control whether light state is applied to keyboard - when OFF, keyboard is controlled by Logitech; when ON, keyboard reflects light state.
- **FR-007**: Visual alerts MUST work regardless of mode or light state, and MUST restore appropriate state after completion (Logitech control if auto, light state if pilot).
- **FR-008**: `{base}/lwt` MUST publish retained "online" on connect and "offline" via MQTT Last Will on disconnect.
- **FR-009**: Service MUST read retained `{base}/status` on startup to restore previous state (light on/off, colors, brightness, mode).
- **FR-010**: Home Assistant discovery MUST use device format with components: light, binary_sensor (status), switch (mode), 3 buttons (alert/warn/info).

### Key Entities

- **TopicMap**: Contains `base` and 9 derived fields: `state_topic`, `command_topic`, `rgb_command_topic`, `brightness_command_topic`, `mode_command_topic`, `alert_command_topic`, `warn_command_topic`, `info_command_topic`, `lwt`.
- **ControlMode**: State machine tracking `pilot_switch` (bool), `light_on` (bool), `last_command_color` (RGB), `last_brightness` (int), `override` (alert/warn/info in progress).
- **MqttLightingService**: Main service managing MQTT subscriptions, light state, mode control, and visual alerts.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Configuration MUST contain only `topics.base`, all other topics are automatically derived.
- **SC-002**: Mode switch MUST toggle between pilot/auto within 1 second.
- **SC-003**: Light state changes MUST apply to keyboard within 1 second when in pilot mode.
- **SC-004**: Visual alerts MUST play pattern and restore correct state within configured duration.
- **SC-005**: Service restart MUST restore previous state (mode, light state, colors, brightness) from retained MQTT messages.
- **SC-006**: LWT MUST show offline within 2 seconds of service termination.
- **SC-007**: 25 unit tests MUST pass covering config validation, HA contracts, control mode, and observability.

## Implementation Status

### Completed ✅

- Base topic configuration simplified to single `topics.base` field
- All 9 topics auto-generated with fixed suffixes
- Home Assistant light component with RGB and brightness control
- Mode switch (pilot/auto) controlling keyboard piloting
- 3 separate alert buttons (Alert, Warn, Info) working in all modes
- LWT topic with online/offline status
- Retained state bootstrapping on restart
- 25 unit tests passing
- Home Assistant device discovery with all components

### Topics Schema

```yaml
topics:
  base: lightspeed  # Only configurable field

# Auto-generated:
# - lightspeed/status → state_topic (retained, full state JSON)
# - lightspeed/switch → command_topic (on/off for light)
# - lightspeed/rgb/set → rgb_command_topic (R,G,B)
# - lightspeed/brightness/set → brightness_command_topic (0-255)
# - lightspeed/mode/set → mode_command_topic (pilot/auto)
# - lightspeed/alert → alert_command_topic (button press)
# - lightspeed/warn → warn_command_topic (button press)
# - lightspeed/info → info_command_topic (button press)
# - lightspeed/lwt → availability (online/offline)
```

### Home Assistant Integration

Single device with 6 components:
1. **Light** - RGB + brightness control (only applies in pilot mode)
2. **Status Sensor** - Binary sensor showing connection status
3. **Mode Switch** - Toggle between pilot (program controls) and auto (Logitech controls)
4. **Alert Button** - Trigger red alert pattern
5. **Warn Button** - Trigger orange warning pattern
6. **Info Button** - Trigger blue info pattern

## Assumptions

- Home Assistant uses MQTT device discovery format with components
- Light component follows HA MQTT light JSON schema
- Mode switch is independent of light state
- Visual alerts temporarily override current state, then restore it
- Logitech SDK (LogitechLed.dll) is available and G Hub/LGS is running
