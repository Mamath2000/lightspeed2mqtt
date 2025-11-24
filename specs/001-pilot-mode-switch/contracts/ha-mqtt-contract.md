# Home Assistant MQTT Contract

## Overview

- **Device Topic Prefix**: `homeassistant/device/<device_id>/config`
- **Command Topics** (from HA to service) use QoS 1, non-retained except switch commands (retained = true).
- **State Topics** (from service to HA) are retained.

## Pilot Switch (`components.pilot_switch`)

- **Discovery Payload Snippet**:

  ```json
  {
    "platform": "switch",
    "unique_id": "<device_id>_pilot",
    "command_topic": "<topics.auto>",
    "state_topic": "<topics.auto_state>",
    "payload_on": "ON",
    "payload_off": "OFF",
    "availability": [{"topic": "<topics.status>"}],
    "retain": true
  }
  ```

- **Command Payloads**: Literal strings `ON` or `OFF` (commands retained to keep HA UI in sync across reboots).
- **State Payloads**: Literal strings `ON` or `OFF` (retained).
- **Behavior**:
  - `ON`: integration claims lighting control (Pilot mode) and replays cached color if light is also `ON`.
  - `OFF`: integration stops issuing Logitech commands; `LogiLedRestoreLighting()` is invoked immediately.

## Light Entity (`components.color_light`)

- **Discovery Payload Snippet**:

  ```json
  {
    "platform": "light",
    "schema": "json",
    "command_topic": "<topics.color>",
    "state_topic": "<topics.color_state>",
    "supported_color_modes": ["rgb"],
    "optimistic": true
  }
  ```

- **Command Payload** (JSON):

  ```json
  {
    "state": "ON" | "OFF",
    "color": { "r": 0-255, "g": 0-255, "b": 0-255 },
    "brightness": 0-255
  }
  ```

- **State Payload** mirrors command payloads but always includes cached `color`/`brightness` for HA dashboards.
- **Behavior**:
  - `state = "ON"` and Pilot switch `ON`: apply color immediately, cache values.
  - `state = "OFF"`: release control (even if Pilot switch remains `ON`), remember cached color for future resume.
  - Commands received while Pilot switch `OFF` are ignored but acknowledged by echoing last-known state with `state="OFF"`.

## Alert Button (`components.alert_button`)

- **Discovery Snippet**:

  ```json
  {
    "platform": "button",
    "command_topic": "<topics.alert>",
    "payload_press": "ON"
  }
  ```

- **Command Payload**: Literal `ON` (optional JSON extension `{ "duration": int }`).
- **Behavior**:
  - Starts alert override (red/white pattern) for `duration` seconds (default config value).
  - Publishes override state to `topics.status` log message `mode=override_alert`.
  - After timer, resumes `Pilot` or `Off` depending on switch/light state.

## Warning Button (`components.warning_button`)

- Same contract as Alert but uses amber pattern and state label `override_warning`.

## Status Sensor (`components.status_binary_sensor`)

- **State Topic**: `topics.status`
- **Payloads**: Retained JSON object; `availability` (string) still indicates `online` / `offline` for compatibility.
- **Attributes** (JSON fields within the same payload):

  ```json
  {
    "availability": "online" | "offline",
    "mode": "pilot" | "off" | "override_alert" | "override_warning",
    "pilot_switch": "ON" | "OFF",
    "light_state": "ON" | "OFF",
    "override_type": null | "alert" | "warning",
    "remaining_seconds": null | int
  }
  ```

- **Behavior**: Service publishes `online` retained on startup, `offline` via LWT. Attributes update whenever mode changes.

## Error Handling

- Invalid command payloads (missing fields, bad JSON) trigger log entries and an `invalid_payload` attribute on the next status publish but do not crash the service.
- Duration outside `[1,300]` results in warning log and ignored override request.

