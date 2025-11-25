"""Lighting helpers powered by ConfigProfile palettes."""
from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple


from lightspeed.config import ConfigProfile, PaletteDefinition

# Charger explicitement la DLL LogitechLed depuis lib/ avant d'importer logipy
import importlib
_dll_name = "LogitechLed.dll"
_dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', _dll_name))
_dll_handle = None
if os.path.exists(_dll_path):
    try:
        _dll_handle = ctypes.WinDLL(_dll_path)
    except Exception as e:
        sys.stderr.write(f"[ERREUR] Impossible de charger la DLL LogitechLed depuis {_dll_path}: {e}\n")
        sys.exit(1)
else:
    sys.stderr.write(f"[ERREUR] DLL LogitechLed non trouvée à l'emplacement attendu : {_dll_path}\n")
    sys.exit(1)

from logipy import logi_led
# Injecter le handle pour forcer logipy à utiliser la bonne DLL
logi_led.led_dll = _dll_handle

RGB = Tuple[int, int, int]
PatternFrame = Tuple[RGB, float]
logger = logging.getLogger(__name__)


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
    def __init__(self, dll_path: Optional[str] = None, *, lock_file: Optional[str] = None) -> None:
        self.lock = threading.Lock()
        self.pattern_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.initialized = False
        self.released = False
        # Si dll_path est relatif, le rendre absolu par rapport au cwd
        if dll_path:
            dll_path = os.path.expanduser(dll_path)
            self.dll_path = Path(dll_path)
            if not self.dll_path.is_absolute():
                self.dll_path = (Path.cwd() / self.dll_path).resolve()
        else:
            self.dll_path = None
        self.lock_file = Path(lock_file).expanduser() if lock_file else None

    def _acquire_lock(self) -> None:
        if not self.lock_file:
            return
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:  # pragma: no cover - best effort path creation
            pass
        if self.lock_file.exists():
            raise RuntimeError(
                f"Le verrou {self.lock_file} existe déjà. Assurez-vous qu'aucune autre instance n'est en cours ou supprimez le fichier."
            )
        payload = {
            "pid": os.getpid(),
            "timestamp": time.time(),
        }
        self.lock_file.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    def _release_lock(self) -> None:
        if not self.lock_file:
            return
        try:
            self.lock_file.unlink()
        except FileNotFoundError:  # pragma: no cover - already absent
            return
        except OSError:  # pragma: no cover - removable warning only
            logger.warning("Impossible de supprimer le verrou %s", self.lock_file)

    def _reattach_control(self) -> None:
        if not self.released:
            return
        self._acquire_lock()
        with self.lock:
            logi_led.logi_led_save_current_lighting()
        self.released = False

    def start(self) -> None:
        if self.initialized:
            return
        if not ensure_logi_dll_loaded(self.dll_path):
            sys.stderr.write("\nERREUR CRITIQUE : DLL LogitechLed manquante\n\n")
            sys.stderr.write("Impossible de trouver 'LogitechLed.dll'.\n")
            sys.stderr.write("Définissez la variable d'environnement LOGI_LED_DLL ou placez la DLL dans le dossier 'lib' à la racine du projet.\n\n")
            sys.stderr.write("Cette DLL est fournie avec le SDK Logitech LED.\n")
            sys.stderr.write("Téléchargez-la sur le site Logitech ou récupérez-la depuis une installation G HUB/LGS.\n\n")
            sys.exit(1)
        self._acquire_lock()
        try:
            if not logi_led.logi_led_init():
                raise RuntimeError(
                    "Impossible d'initialiser le SDK Logitech. Vérifiez que G Hub / LGS est en cours d'exécution."
                )
            logi_led.logi_led_save_current_lighting()
            self.initialized = True
            self.released = False
        except Exception:
            self._release_lock()
            self.initialized = False
            self.released = False
            raise

    def shutdown(self) -> None:
        self.stop_pattern()
        if self.initialized:
            with self.lock:
                logi_led.logi_led_restore_lighting()
                logi_led.logi_led_shutdown()
        self._release_lock()
        self.initialized = False
        self.released = False

    def _set_color_now(self, rgb: RGB) -> None:
        r, g, b = (clamp_channel(channel) for channel in rgb)
        with self.lock:
            logi_led.logi_led_set_lighting(to_pct(r), to_pct(g), to_pct(b))

    def set_static_color(self, rgb: RGB) -> None:
        self.start()
        self._reattach_control()
        self.stop_pattern()
        self._set_color_now(rgb)

    def start_pattern(self, frames: Sequence[PatternFrame]) -> None:
        if not frames:
            raise ValueError("Aucun frame fourni pour le pattern")
        self.start()
        self.stop_pattern()
        self._reattach_control()
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
            # Force la restauration en désactivant temporairement notre contrôle
            logi_led.logi_led_shutdown()
        self._release_lock()
        self.released = True
        self.initialized = False


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
    frames = tuple((frame.color, frame.duration_ms / 1000.0) for frame in palette.frames)
    logger.debug(
        "palette_frames: Palette '%s' utilisée: %s",
        getattr(palette, 'name', '?'),
        [
            {"color": f"#{r:02X}{g:02X}{b:02X}", "duration": d}
            for (r, g, b), d in frames
        ]
    )
    return frames


def alert_frames(profile: ConfigProfile) -> Tuple[PatternFrame, ...]:
    """Retourne les frames de la palette d'alerte."""
    return palette_frames(profile.palettes.alert)


def warning_frames(profile: ConfigProfile) -> Tuple[PatternFrame, ...]:
    return palette_frames(profile.palettes.warning)

def info_frames(profile: ConfigProfile) -> Tuple[PatternFrame, ...]:
    return palette_frames(profile.palettes.info)


def default_color(profile: ConfigProfile) -> RGB:
    return profile.lighting.default_color
