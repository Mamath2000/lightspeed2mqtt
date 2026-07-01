"""Reproduit une rafale de démarrages/arrêts de pattern concurrents.

Avant le correctif, `start_pattern`/`stop_pattern` géraient `self.stop_event` et
`self.pattern_thread` sans verrou : un appel concurrent pouvait réassigner
`self.stop_event` pendant qu'un thread d'animation plus ancien l'observait encore,
laissant ce thread tourner indéfiniment. Un `stop_pattern()` suivant, appelé depuis le
thread réseau MQTT, se bloquait alors pour toujours dans `Thread.join()` -> le service
semblait figé et nécessitait un redémarrage du service NSSM.
"""
from __future__ import annotations

import threading
import time

import lightspeed.lighting as lighting_module


def _patch_sdk(monkeypatch):
    monkeypatch.setattr(lighting_module.logi_led, "logi_led_init", lambda: True)
    monkeypatch.setattr(lighting_module.logi_led, "logi_led_save_current_lighting", lambda: True)
    monkeypatch.setattr(lighting_module.logi_led, "logi_led_restore_lighting", lambda: True)
    monkeypatch.setattr(lighting_module.logi_led, "logi_led_shutdown", lambda: True)
    monkeypatch.setattr(lighting_module.logi_led, "logi_led_set_lighting", lambda r, g, b: True)


def test_concurrent_start_stop_pattern_does_not_deadlock(monkeypatch):
    _patch_sdk(monkeypatch)
    controller = lighting_module.LightingController(dll_path=None, lock_file=None)

    frames = (((255, 0, 0), 0.01), ((0, 255, 0), 0.01))
    errors: list[Exception] = []

    def spam_start() -> None:
        try:
            for _ in range(30):
                controller.start_pattern(frames)
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - défensif
            errors.append(exc)

    def spam_stop() -> None:
        try:
            for _ in range(30):
                controller.stop_pattern()
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - défensif
            errors.append(exc)

    threads = [threading.Thread(target=spam_start) for _ in range(3)]
    threads += [threading.Thread(target=spam_stop) for _ in range(3)]

    for t in threads:
        t.start()
    for t in threads:
        # Timeout généreux : si le correctif régresse, on veut un échec de test net,
        # pas un pytest qui reste bloqué indéfiniment.
        t.join(timeout=10)

    assert all(not t.is_alive() for t in threads), (
        "un thread est resté bloqué : régression sur la concurrence start_pattern/stop_pattern"
    )
    assert not errors, f"erreurs inattendues pendant la rafale: {errors}"

    controller.stop_pattern()
    controller.shutdown()
