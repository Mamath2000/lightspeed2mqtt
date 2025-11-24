"""Lighting helpers powered by ConfigProfile palettes."""
from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple

from lightspeed.config import ConfigProfile, PaletteDefinition

try:
    from logipy import logi_led
except ImportError as exc:  # pragma: no cover - logipy is required at runtime
    raise ImportError(
        "Le module 'logipy' est requis. Installez-le avec: pip install logipy"
    ) from exc

RGB = Tuple[int, int, int]
PatternFrame = Tuple[RGB, float]


def clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


def to_pct(value: int) -> int:
    return int(round((clamp_channel(value) / 255) * 100))


def apply_brightness(color: RGB, brightness: int) -> RGB:
    value = max(0, min(255, int(brightness)))
    if value >= 255:
        return color
    ratio = value / 255 if value else 0
    return tuple(int(channel * ratio) for channel in color)


def parse_color_string(value: str) -> RGB:
    if not value:
        raise ValueError("Couleur vide")
    text = value.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return clamp_channel(data['r']), clamp_channel(data['g']), clamp_channel(data['b'])
        if isinstance(data, list) and len(data) == 3:
            r, g, b = data
            return clamp_channel(r), clamp_channel(g), clamp_channel(b)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass

    if text.startswith('#'):
        hex_value = text.lstrip('#')
        if len(hex_value) != 6:
            raise ValueError('Format hex attendu: #RRGGBB')
        return tuple(int(hex_value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    separators = ',' if ',' in text else ' '
    parts = [p for p in text.split(separators) if p]
    if len(parts) == 3:
        r, g, b = (int(part) for part in parts)
        return clamp_channel(r), clamp_channel(g), clamp_channel(b)

    raise ValueError("Impossible de lire la couleur (attendu #RRGGBB ou R,G,B)")


class LightingController:
    def __init__(self, dll_path: Optional[str] = None) -> None:
        self.lock = threading.Lock()
        self.pattern_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.initialized = False
        self.released = False
        self.dll_path = Path(dll_path).expanduser() if dll_path else None

    def start(self) -> None:
        if self.initialized:
            return
        if not ensure_logi_dll_loaded(self.dll_path):
            raise RuntimeError("Impossible de trouver 'LogitechLed.dll'. Définissez LOGI_LED_DLL ou placez la DLL à la racine.")
        if not logi_led.logi_led_init():
            raise RuntimeError("Impossible d'initialiser le SDK Logitech. Vérifiez que G Hub / LGS est en cours d'exécution.")
        logi_led.logi_led_save_current_lighting()
        self.initialized = True
        self.released = False

    def shutdown(self) -> None:
        self.stop_pattern()
        if self.initialized:
            with self.lock:
                logi_led.logi_led_restore_lighting()
                logi_led.logi_led_shutdown()
        self.initialized = False

    def _set_color_now(self, rgb: RGB) -> None:
        r, g, b = (clamp_channel(channel) for channel in rgb)
        with self.lock:
            logi_led.logi_led_set_lighting(to_pct(r), to_pct(g), to_pct(b))

    def set_static_color(self, rgb: RGB) -> None:
        self.start()
        if self.released:
            with self.lock:
                logi_led.logi_led_save_current_lighting()
            self.released = False
        self.stop_pattern()
        self._set_color_now(rgb)

    def start_pattern(self, frames: Sequence[PatternFrame]) -> None:
        if not frames:
            raise ValueError("Aucun frame fourni pour le pattern")
        self.start()
        self.stop_pattern()
        self.released = False
        self.stop_event = threading.Event()

        def worker() -> None:
            palette = list(frames)
            if not palette:
                return
            while not self.stop_event.is_set():
                for color, duration in palette:
                    if self.stop_event.is_set():
                        break
                    self._set_color_now(color)
                    wait_time = max(duration, 0.05)
                    if self.stop_event.wait(wait_time):
                        break

        self.pattern_thread = threading.Thread(target=worker, daemon=True)
        self.pattern_thread.start()

    def stop_pattern(self) -> None:
        if self.pattern_thread and self.pattern_thread.is_alive():
            self.stop_event.set()
            self.pattern_thread.join()
        self.pattern_thread = None

    def release(self) -> None:
        if not self.initialized:
            return
        self.stop_pattern()
        with self.lock:
            logi_led.logi_led_restore_lighting()
        self.released = True


def restore_logitech_control(controller: LightingController) -> None:
    """Return keyboard control to Logitech Options+/G HUB via the controller."""
    controller.release()


def reapply_cached_color(controller: LightingController, base_color: RGB, brightness: int) -> None:
    """Reapply the cached automation color/brightness after regaining pilot control."""
    controller.set_static_color(apply_brightness(base_color, brightness))


def ensure_logi_dll_loaded(override_path: Optional[Path] = None) -> bool:
    if getattr(logi_led, 'led_dll', None):
        return True

    candidates = []
    if override_path:
        candidates.append(override_path)
    env_override = os.environ.get('LOGI_LED_DLL')
    if env_override:
        candidates.append(Path(env_override))

    script_dir = Path(__file__).resolve().parent.parent
    candidates.append(script_dir / 'LogitechLed.dll')

    program_files = [os.environ.get('ProgramFiles'), os.environ.get('ProgramW6432')]
    ghub_rel = Path('LGHUB/SDK/LED/x64/LogitechLed.dll')
    lgs_rel = Path('Logitech Gaming Software/SDK/LED/x64/LogitechLed.dll')
    lgs_rel_x86 = Path('Logitech Gaming Software/SDK/LED/x86/LogitechLed.dll')
    for base in program_files:
        if not base:
            continue
        path_base = Path(base)
        candidates.append(path_base / ghub_rel)
        candidates.append(path_base / lgs_rel)
        candidates.append(path_base / lgs_rel_x86)

    for dll_path in candidates:
        if dll_path and dll_path.exists():
            logi_led.led_dll = ctypes.cdll.LoadLibrary(str(dll_path))
            return True
    return False


def palette_frames(palette: PaletteDefinition) -> Tuple[PatternFrame, ...]:
    return tuple((frame.color, frame.duration_ms / 1000.0) for frame in palette.frames)


def alert_frames(profile: ConfigProfile) -> Tuple[PatternFrame, ...]:
    return palette_frames(profile.palettes.alert)


def warning_frames(profile: ConfigProfile) -> Tuple[PatternFrame, ...]:
    return palette_frames(profile.palettes.warning)


def default_color(profile: ConfigProfile) -> RGB:
    return profile.lighting.default_color
