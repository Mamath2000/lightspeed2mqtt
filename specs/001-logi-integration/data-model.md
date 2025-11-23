# Data Model – Home Assistant MQTT Integration

## 1. ConfigProfile

- **Description**: Parsed representation of `config.yaml` containing every runtime knob for MQTT + lighting behavior.
- **Fields**:
  - `mqtt.host` (str, required)
  - `mqtt.port` (int, default 1883)
  - `mqtt.username` (str, optional)
  - `mqtt.password` (str, optional, stored only in memory)
  - `mqtt.keepalive` (int seconds, default 60)
  - `mqtt.client_id` (str, default `lightspeed-alerts`)
  - `topics.base` (str, required, e.g., `lightspeed/alerts`)
  - `topics.color_command`, `topics.color_state`, `topics.auto_command`, `topics.auto_state`, `topics.alert_command`, `topics.warning_command`, `topics.status`, `topics.health` (derived automatically from base unless overridden)
  - `home_assistant.device_id` (str)
  - `home_assistant.device_name` (str)
  - `home_assistant.manufacturer` (str)
  - `home_assistant.model` (str)
  - `home_assistant.sw_version` (str, default from package version)
  - `palettes.alert` (list of RGB tuples, default `[(255,0,0),(255,255,255),(0,0,0)]`)
  - `palettes.warning` (list of RGB tuples, default `[(255,191,0),(0,0,0)]`)
  - `palettes.frame_ms` (dict: `alert` ≤500, `warning` ≤350)
  - `defaults.color` (RGB tuple, fallback `#33AAFF`)
  - `logitech.dll_path` (str, optional override)
- **Validation Rules**: Missing required keys fail fast. Frame intervals must satisfy Principle IV. Credentials never logged.

## 2. LightingState

- **Description**: Runtime state for Logitech control.
- **Fields**:
  - `active_mode` (enum: `auto`, `manual`, `alert`, `warning`)
  - `current_color` (RGB tuple)
  - `saved_profile` (SDK snapshot for restore)
  - `last_alert_at` (timestamp)
  - `lock_owner` (enum: `mqtt`, `cli`)
- **Relationships**: Depends on `ConfigProfile` for palette definitions. Exposed to MQTT session for reporting.

## 3. HaDeviceDescriptor

- **Description**: Canonical device metadata reused across discovery payloads.
- **Fields**:
  - `identifiers` (list[str]) containing `lightspeed2mqtt:{device_id}`
  - `name`, `manufacturer`, `model`, `sw_version`
  - `via_device` (optional) for future expansions
- **Relationships**: Embedded inside each entity discovery config; referenced by contracts file.

## 4. MqttSession

- **Description**: Wrapper around `paho.mqtt.client.Client` controlling lifecycle.
- **Fields**:
  - `client` (paho client instance)
  - `status_topic` (str) for online/offline
  - `health_topic` (str) for JSON status
  - `subscriptions` (dict topic -> handler)
  - `lwt_payload` (str `offline`)
  - `is_connected` (bool)
- **Relationships**: Created with `ConfigProfile`, publishes `HaDeviceDescriptor` payloads, invokes `LightingState` operations.

## 5. Command Events

- **Description**: In-memory objects representing parsed MQTT payloads.
- **Variants**:
  - `ColorCommand` (fields: `rgb`, `source`)
  - `AlertCommand` (fields: `severity`, `source`)
  - `AutoCommand` (fields: `enabled: bool`, `source`)
- **Validation**: Color parsing enforces `#RRGGBB` or numeric triplets; invalid payloads logged and cause state topic updates with `error` attribute.

## 6. HealthSnapshot

- **Description**: Data published to the retained JSON health topic.
- **Fields**:
  - `connected` (bool)
  - `controller_state` (enum)
  - `last_effect` (nullable string)
  - `last_error` (nullable string)
  - `timestamp` (ISO 8601)
- **Relationships**: Derived from `LightingState` + `MqttSession`; consumed by Home Assistant templates or dashboards.
