# lightspeed2mqtt Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-23

## Active Technologies
- Python 3.13 + `paho-mqtt`, `logipy` (Logitech LED SDK wrapper), `click`, `pyyaml` (001-pilot-mode-switch)
- N/A (in-memory state only) (001-pilot-mode-switch)
- Python 3.13 (single-process CLI + MQTT service) + `paho-mqtt`, `logipy` (LogitechLed.dll bridge), `pyyaml`, `click` (001-pilot-mode-switch)
- In-memory state + retained MQTT topics (no external DB) (001-pilot-mode-switch)

- Python 3.13 (per Principle III) + `logipy` (Logitech LED SDK bindings), `paho-mqtt`, `pyyaml` (safe_load), standard library (`asyncio`, `logging`, `pathlib`). (001-logi-integration)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.13 (per Principle III): Follow standard conventions

## Recent Changes
- 001-pilot-mode-switch: Added Python 3.13 (single-process CLI + MQTT service) + `paho-mqtt`, `logipy` (LogitechLed.dll bridge), `pyyaml`, `click`
- 001-pilot-mode-switch: Added Python 3.13 + `paho-mqtt`, `logipy` (Logitech LED SDK wrapper), `click`, `pyyaml`

- 001-logi-integration: Added Python 3.13 (per Principle III) + `logipy` (Logitech LED SDK bindings), `paho-mqtt`, `pyyaml` (safe_load), standard library (`asyncio`, `logging`, `pathlib`).

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
