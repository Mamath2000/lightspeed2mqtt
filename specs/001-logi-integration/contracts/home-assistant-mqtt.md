# MQTT Contract – Home Assistant Device Discovery & Control

All topics live under `<base>` from `config.yaml` (example: `lightspeed/alerts`). Replace `<base>` accordingly.

## 1. Discovery Payloads (Retained)

Publish once at startup + on reconnect using `$homeassistant/<component>/<object_id>/config` topics.

### 1.1 Device Object (shared)

- Used in every discovery payload via `"device"` field:

```json
{
  "identifiers": ["lightspeed2mqtt:{{device_id}}"],
  "manufacturer": "{{manufacturer}}",
  "model": "{{model}}",
  "name": "{{device_name}}",
  "sw_version": "{{sw_version}}"
}
```

### 1.2 Alert Button

- Topic: `$homeassistant/button/{{device_id}}_alert/config`

```json
{
  "name": "Logitech Alert",
  "unique_id": "{{device_id}}_alert",
  "command_topic": "<base>/alert/set",
  "payload_press": "trigger",
  "availability": [{"topic": "<base>/status", "payload_available": "online", "payload_not_available": "offline"}],
  "device": { /* device object */ }
}
```

### 1.3 Warning Button

- Same schema as alert with `command_topic: <base>/warning/set` and `unique_id: {{device_id}}_warning`.

### 1.4 RGB Light

- Topic: `$homeassistant/light/{{device_id}}_color/config`

```json
{
  "name": "Logitech Color",
  "unique_id": "{{device_id}}_color",
  "schema": "json",
  "command_topic": "<base>/color/set",
  "state_topic": "<base>/color/state",
  "availability": [{"topic": "<base>/status", "payload_available": "online", "payload_not_available": "offline"}],
  "brightness": false,
  "rgb": true,
  "qos": 1,
  "device": { /* device object */ }
}
```

### 1.5 Auto Switch

- Topic: `$homeassistant/switch/{{device_id}}_auto/config`

```json
{
  "name": "Logitech Auto Mode",
  "unique_id": "{{device_id}}_auto",
  "command_topic": "<base>/auto/set",
  "state_topic": "<base>/auto/state",
  "payload_on": "auto",
  "payload_off": "manual",
  "availability": [{"topic": "<base>/status", "payload_available": "online", "payload_not_available": "offline"}],
  "device": { /* device object */ }
}
```

### 1.6 Status Binary Sensor

- Topic: `$homeassistant/binary_sensor/{{device_id}}_status/config`

```json
{
  "name": "Logitech Alerts Status",
  "unique_id": "{{device_id}}_status",
  "state_topic": "<base>/status",
  "payload_on": "online",
  "payload_off": "offline",
  "availability": [{"topic": "<base>/status", "payload_available": "online", "payload_not_available": "offline"}],
  "device_class": "connectivity",
  "device": { /* device object */ }
}
```

## 2. Command Topics

| Topic | Payload Format | Description |
|-------|----------------|-------------|
| `<base>/alert/set` | `trigger` (string) | Start high-contrast alert animation until canceled. |
| `<base>/warning/set` | `trigger` | Start amber warning animation until canceled. |
| `<base>/color/set` | JSON `{ "r":0-255, "g":0-255, "b":0-255 }` or string `#RRGGBB` or CSV `R,G,B`. |
| `<base>/auto/set` | `auto` or `manual` | `auto` releases control back to Logitech; `manual` acquires control without changing color. |

## 3. State & Telemetry Topics

| Topic | Payload | Retained | Purpose |
|-------|---------|----------|---------|
| `<base>/color/state` | JSON `{ "state":"ON","effect":"alert\|warning\|static","color":{"r":..}}` | Yes | Mirrors current effect and RGB value. |
| `<base>/auto/state` | `auto` or `manual` | Yes | Indicates whether middleware currently owns lighting. |
| `<base>/status` | `online` / `offline` | Yes (also LWT) | Availability for HA entities. |
| `<base>/health` | JSON `{ "connected":bool, "controller_state":str, "last_effect":str, "last_error":str }` | Yes | Diagnostics for dashboards/templating. |

## 4. QoS & Retain Rules

- Discovery, state, status, and health topics MUST be retained (`retain=true`).
- Command topics use QoS 1, retain false.
- MQTT keep-alive defaults to 60 s; LWT publishes `offline` to `<base>/status` with QoS 1 retain true.

## 5. Error Handling

- Invalid payloads produce a log entry and reply on the corresponding state topic with `"error": "<message>"` inside the JSON attributes.
- When Logitech SDK is unavailable, the service publishes `<base>/status = offline` and marks `controller_state` as `hardware_unavailable` in `<base>/health`.
