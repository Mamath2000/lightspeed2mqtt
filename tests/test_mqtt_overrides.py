from __future__ import annotations

import threading
import time
import types
from datetime import datetime, timezone
from unittest import mock

import pytest

import lightspeed.mqtt as mqtt_module
from lightspeed.config import load_config

CONFIG_YAML = """
mqtt:
  host: localhost
  client_id: alerts
topics:
  base: foo/bar
home_assistant:
  device_id: foo
  device_name: Foo
  manufacturer: Test
  model: RevA
lighting:
  default_color: "#112233"
  lock_file: lock
effects:
  override_duration_seconds: 10
palettes:
  alert:
    max_duration_ms: 500
    duration_seconds: 3
    frames:
    - color: "#FF0000"
      duration_ms: 150
  warning: {}
  info: {}
logitech:
  profile_backup: backup.json
observability:
  log_level: INFO
"""


class FakeTimer:
    """Remplace threading.Timer pour ne jamais lancer de vrai thread minuté en test."""

    def __init__(self, interval, function, args=None):
        self.interval = interval
        self.function = function
        self.args = args or ()
        self.started = False
        self.cancelled = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True


class FakeController:
    def __init__(self):
        self.pattern_starts = 0
        self.pattern_stops = 0
        self.static_colors = []
        self.released_calls = []

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def set_static_color(self, rgb) -> None:
        self.static_colors.append(rgb)

    def stop_pattern(self) -> None:
        self.pattern_stops += 1

    def start_pattern(self, frames) -> None:
        self.pattern_starts += 1


@pytest.fixture
def fake_lighting(monkeypatch):
    module = types.SimpleNamespace(
        apply_brightness=lambda color, brightness: color,
        restore_logitech_control=lambda controller: controller.released_calls.append("restore"),
        reapply_cached_color=lambda controller, color, brightness: controller.static_colors.append(color),
        alert_frames=lambda profile: (((255, 0, 0), 0.15),),
        warning_frames=lambda profile: (((255, 140, 0), 0.15),),
        info_frames=lambda profile: (((255, 255, 255), 0.15),),
    )
    monkeypatch.setattr(mqtt_module, "_LIGHTING_MODULE", module)
    return module


def build_service(tmp_path, fake_lighting):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_YAML, encoding="utf-8")
    profile = load_config(config_path)
    controller = FakeController()
    with mock.patch.object(mqtt_module.mqtt, "Client") as client_cls:
        client_cls.return_value = mock.MagicMock()
        service = mqtt_module.MqttLightingService(controller, profile, validated_at=datetime.now(timezone.utc))
    service._connected = True
    service._timer_factory = FakeTimer
    return service, controller


def test_repeated_alert_does_not_restart_pattern(tmp_path, fake_lighting):
    """Une rafale du même effet ne doit pas relancer l'animation depuis sa première frame."""
    service, controller = build_service(tmp_path, fake_lighting)

    service._handle_alert_button()
    assert controller.pattern_starts == 1
    first_timer = service.control.override.timer_handle

    service._handle_alert_button()
    service._handle_alert_button()

    assert controller.pattern_starts == 1, "l'animation ne doit démarrer qu'une fois"
    assert controller.pattern_stops == 0, "aucun stop_pattern ne doit être déclenché par la rafale"
    second_timer = service.control.override.timer_handle
    assert second_timer is not first_timer
    assert first_timer.cancelled is True


def test_switching_effect_kind_restarts_pattern(tmp_path, fake_lighting):
    """Un effet différent doit bien interrompre et relancer une nouvelle animation."""
    service, controller = build_service(tmp_path, fake_lighting)

    service._handle_alert_button()
    assert controller.pattern_starts == 1

    service._handle_warn_button()
    assert controller.pattern_starts == 2
    assert controller.pattern_stops == 1
    assert service.control.override.kind == "warning"


def test_palette_specific_duration_is_used(tmp_path, fake_lighting):
    """La durée globale doit venir de la palette si définie, sinon du défaut effects.*."""
    service, controller = build_service(tmp_path, fake_lighting)

    service._handle_alert_button()
    assert service.control.override.duration_seconds == 3  # palettes.alert.duration_seconds

    service._handle_warn_button()
    assert service.control.override.duration_seconds == 10  # pas de valeur dédiée -> défaut global


def test_override_cleared_even_if_hardware_resume_fails(tmp_path, fake_lighting):
    """Si la reprise matérielle après un effet lève une exception, l'état interne ne
    doit pas rester bloqué en "override actif" (sinon l'effet suivant du même type est
    pris pour une simple prolongation d'un effet déjà arrêté)."""
    fake_lighting.reapply_cached_color = mock.Mock(side_effect=RuntimeError("SDK KO"))
    service, controller = build_service(tmp_path, fake_lighting)

    service._handle_alert_button()
    assert service.control.override is not None

    service._complete_override("alert")

    assert service.control.override is None
    assert controller.pattern_stops == 1


def test_alert_spam_with_real_timers_does_not_deadlock(tmp_path, fake_lighting):
    """Rafale d'alertes avec de vrais threading.Timer à expiration très courte : simule
    la course entre le thread réseau MQTT (nouveaux messages) et le thread du Timer qui
    expire un effet (_complete_override), pour vérifier que _override_lock empêche tout
    blocage (le bug rapporté nécessitait un redémarrage du service NSSM).
    """
    service, controller = build_service(tmp_path, fake_lighting)
    service._timer_factory = threading.Timer  # timers réels, pas de FakeTimer

    errors: list[Exception] = []

    def spam() -> None:
        try:
            for _ in range(40):
                service._handle_override_command(mqtt_module.AlertCommand(kind="alert", duration=0.01))
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - défensif
            errors.append(exc)

    threads = [threading.Thread(target=spam) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert all(not t.is_alive() for t in threads), "un thread est resté bloqué (deadlock)"
    assert not errors, f"erreurs inattendues pendant la rafale: {errors}"

    # Laisser les derniers timers réels expirer avant la fin du test.
    time.sleep(0.05)
