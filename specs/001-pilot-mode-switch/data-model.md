# Data Model: Pilot Mode Switch & Temporary Alerts

## Entities

### 1. ControlMode

- **Purpose**: Tracks who currently owns keyboard lighting.
- **States**: `pilot`, `off`, `override_alert`, `override_warning`.
- **Fields**:
  - `state`: enum (values above).
  - `pilot_switch_enabled`: bool (last-known HA switch state for discovery + telemetry).
  - `light_on`: bool (mirrors HA light entity on/off state, even when commands ignored).
  - `last_color`: struct `{r:int, g:int, b:int}` (0–100 scaled percentages for Logitech SDK).
  - `last_brightness`: int (0–100, derived from HA payloads).
  - `status_snapshot`: struct `{mode:str, override_type:Optional[str], remaining_seconds:Optional[int]}` published to retained status topic.
  - `updated_at`: datetime (monotonic timestamp for debouncing/resume logic).
- **Relationships**: Owns a reference to `OverrideAction` when `state` starts with `override_*`.
- **Validation Rules**:
  - `last_color` must include all channels; default to palette fallback if absent.
  - `last_brightness` defaults to 100 when unspecified but must be stored before overrides run.
  - Transitions between `pilot` and `off` require invoking Logitech restore/set helpers.

### 2. OverrideAction

- **Purpose**: Describes an in-flight alert or warning override.
- **Fields**:
  - `type`: enum (`alert`, `warning`).
  - `started_at`: datetime.
  - `duration_seconds`: int (1–300 validated via config).
  - `timer_handle`: reference to scheduler handle for cancellation.
- **Relationships**: Linked to `ControlMode`; only one active instance allowed.
- **Validation Rules**:
  - New overrides cancel any existing `timer_handle` before scheduling.
  - `duration_seconds` defaults to config `override_duration_seconds` if button payload omits custom value.

### 3. ConfigurationProfile Extensions

- **Purpose**: Extends existing YAML profile with new knobs.
- **Fields**:
  - `home_assistant.pilot_switch`: metadata for discovery (entity_id, friendly name, topics, `unique_id`).
  - `effects.override_duration_seconds`: int default 10.
  - `observability.status_attributes`: optional map of extra keys to expose on retained status topic (default includes `mode`, `pilot_switch`, `light_state`).
- **Validation Rules**:
  - Duration must be between 1 and 300 seconds.
  - `pilot_switch` inherits availability/status topics from profile; no empty strings allowed.

## State Transitions

```mermaid
graph TD
  Off(Off Mode) -->|Pilot switch ON| Pilot
  Pilot -->|Pilot switch OFF| Off
  Pilot -->|Light entity OFF| Off
  Off -->|Light entity ON & pilot switch ON| Pilot
  Pilot -->|Alert button| AlertOverride
  Pilot -->|Warning button| WarningOverride
  Off -->|Alert/Warning button| AlertOverride
  AlertOverride -->|Timer expires & pilot switch ON| Pilot
  AlertOverride -->|Timer expires & pilot switch OFF| Off
  WarningOverride -->|Timer expires & pilot switch ON| Pilot
  WarningOverride -->|Timer expires & pilot switch OFF| Off
  AlertOverride -->|Any new override| (Cancel & start new)
```

## Topics & Contracts Snapshot

- `homeassistant/device/<id>/config`: includes `components.pilot_switch`, `components.color_light`, `components.alert_button`, `components.warning_button`, `components.status_binary_sensor`.
- Command Topics:
  - `topics.color`: JSON `{ "state": "ON|OFF", "color": {"r":0-255,...}, "brightness":0-255 }`.
  - `topics.alert`, `topics.warning`: string `ON` (override request) or JSON with `duration` override (optional future).
  - `topics.auto`: payload `ON`/`OFF` retained so HA immediately reflects switch state.
- State Topics:
  - `topics.status`: JSON payload `{ "availability":"online|offline", "mode":"pilot|off|override_*", "pilot_switch":"ON|OFF", "light_state":"ON|OFF", "override_type":null|"alert|warning", "remaining_seconds":int? }` retained.
  - `topics.auto_state`: mirrors switch; may reuse command topic with retain if broker permissions restrict new topics.

## Validation & Error Handling

- Reject switch commands that conflict with Light state (e.g., `pilot switch on` while HA Light entity is explicitly off) by logging and aligning states before applying colors.
- Invalid duration inputs (non-int, <=0, >300) cause config load failure or override command rejection with warning log.
- Overrides persist across MQTT reconnects by re-reading `OverrideAction` state and rescheduling timers if still within window.
