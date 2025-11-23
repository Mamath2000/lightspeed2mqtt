# Quickstart – Home Assistant MQTT Integration

## 1. Prerequisites

- Windows 10/11 workstation with Logitech G HUB (or LGS) and `LogitechLed.dll` placed next to `simple-logi.py`.
- Python 3.13 with virtual environment activated (`.venv\\Scripts\\activate`).
- MQTT broker credentials (host, port, optional username/password) and Home Assistant configured to listen on the same broker.
- Dependencies installed via `pip install -r requirements.txt` (implementation will add `pyyaml`).

## 2. Configure `config.yaml`

1. Copy `config.example.yaml` (to be added) to `config.yaml`.
2. Fill in:
    - `mqtt.host`, `mqtt.port`, `mqtt.username`, `mqtt.password` (if needed).
    - `topics.base` (e.g., `lightspeed/alerts`).
    - `home_assistant` block (`device_id`, `device_name`, manufacturer info).
    - Optional overrides: palette RGB lists, frame durations, `logitech.dll_path`.
3. Save the file in the project root (same folder as `simple-logi.py`).

## 3. Run the MQTT Service

```pwsh
# From repo root with venv active
python simple-logi.py serve --config config.yaml
```

- On startup the service validates the config, connects to MQTT, publishes HA discovery payloads, and logs readiness.
- Check Home Assistant → Settings → Devices → "Lightspeed Alerts" to confirm entities appear.

## 4. Trigger Manual Jobs (optional)

```pwsh
python simple-logi.py alert   --config config.yaml
python simple-logi.py warning --config config.yaml
python simple-logi.py color   --color "#33AAFF" --config config.yaml
python simple-logi.py auto    --config config.yaml
```

- CLI commands share the same lock with the MQTT worker, so run them only when the service is idle or stopped.

## 5. Validate End-to-End

1. In Home Assistant, open the auto-generated device and test each entity:
    - Alert button → keyboard pulses red/white/black.
    - Warning button → keyboard pulses amber/black.
    - RGB light → pick colors and verify <300 ms latency.
    - Auto switch → returns control to Logitech software.
    - Status sensor → shows `online`; stop the service to see it flip `offline`.
2. Review the retained `lightspeed/alerts/health` topic for JSON telemetry (controller state, `last_error`).
3. Restart the service and confirm HA reuses the same device (no duplicates) thanks to retained discovery payloads.
