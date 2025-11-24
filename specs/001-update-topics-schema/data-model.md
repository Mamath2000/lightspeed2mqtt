# Data Model: Base-Relative Topic Schema

## TopicMap Entity

| Field | Type | Default Suffix | Description |
|-------|------|----------------|-------------|
| `base` | string | `lightspeed/alerts` | Namespace root; all child topics derive from here. Stored fully qualified. |
| `power` | string | `power` | Suffix for `ON/OFF` retained ownership topic. Derived absolute topic = `<base>/<power>`. |
| `power_state` | string | `<power>/state` | Retained mirror of last processed `power` payload for HA dashboards. |
| `mode` | string | `mode` | Suffix for retained Pilot control topic (`pilot` vs `logi`). |
| `mode_state` | string | `<mode>/state` | Retained indicator ensuring HA sees current mode even if it missed the command. |
| `color` | string | `color` | Suffix for RGB commands; payloads accepted as `#RRGGBB`, `R,G,B`, or JSON `{ r,g,b }`. |
| `color_state` | string | `<color>/state` | Retained state-mirror used by dashboards to restore after restart. |
| `brightness` | string | `brightness` | Suffix for brightness-only commands (`0-100`). Implies power `ON`. |
| `brightness_state` | string | `<brightness>/state` | Retained brightness confirmation. |
| `alert` | string | `alert` | Suffix for JSON override requests `{ type, duration? }`. Non-retained commands. |
| `status` | string | `status` | Suffix for retained structured health payload `{ "state": "online", "attributes": {...} }`. |
| `lwt` | string | `lwt` | Availability topic. Service publishes retained `online`; broker Last Will publishes `offline`. |

### Validation Rules

1. All suffix fields **must** be relative (no `/` characters) except for derived state topics which are computed automatically.
2. `topics.base` must be non-empty, contain no whitespace, and end without a trailing slash (normalization handled at load time).
3. Each derived topic is concatenated as `f"{base}/{suffix}"` at runtime; duplicates and whitespace trigger `ConfigError`.
4. Schema revision changes whenever TopicMap dataclass fields change, ensuring CLI detects outdated configs.

## Mode State Machine

| Event | From State | To State | Side Effects |
|-------|------------|----------|--------------|
| MQTT `pilot` | `logi` | `pilot` | Acquire lighting lock, replay cached color/brightness, publish retained `pilot` to `<base>/mode` & `<base>/mode/state`, set `power=ON`. |
| MQTT `logi` | `pilot` | `logi` | Stop overrides, release lock, restore Logitech profile, publish retained `logi`. |
| Invalid payload | Any | unchanged | Log warning, re-publish current state to reassert ownership. |

## AlertRequest Payload

```json
{
  "type": "alert" | "warning" | "info",
  "duration": 1-300 (optional seconds)
}
```

- Parsed from `topics.alert`.
- Validation failure -> log + ignore.
- Accepted payload triggers `EffectsSettings` override respecting configured palette durations.

## Availability Contract

- `topics.status`: retained JSON `{ "state": "online" | "offline", "attributes": { "mode": "pilot"|"logi", "power": "ON"|"OFF" } }`.
- `topics.lwt`: retained string `online` on connect; MQTT Last Will configured to `offline`.
