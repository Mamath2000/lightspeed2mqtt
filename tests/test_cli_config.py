from __future__ import annotations

import importlib.util
import sys
import textwrap
import types
from pathlib import Path
from typing import Mapping

import pytest

SIMPLE_LOGI_PATH = Path(__file__).resolve().parents[1] / "simple-logi.py"


class _DummyLogiLed:
  def __init__(self) -> None:
    self.led_dll = object()

  def logi_led_init(self) -> bool:  # pragma: no cover - simple stub
    return True

  def logi_led_save_current_lighting(self) -> None:  # pragma: no cover - simple stub
    return None

  def logi_led_set_lighting(self, *_args, **_kwargs) -> None:  # pragma: no cover - simple stub
    return None

  def logi_led_restore_lighting(self) -> None:  # pragma: no cover - simple stub
    return None

  def logi_led_shutdown(self) -> None:  # pragma: no cover - simple stub
    return None


class _DummyMqttService:
  def __init__(self, *_args, **_kwargs) -> None:  # pragma: no cover - simple stub
    pass

  def start(self) -> None:  # pragma: no cover - simple stub
    return None

  def loop_forever(self) -> None:  # pragma: no cover - simple stub
    return None

  def stop(self) -> None:  # pragma: no cover - simple stub
    return None


def _load_simple_logi_module():
    spec = importlib.util.spec_from_file_location("simple_logi_module", SIMPLE_LOGI_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger simple-logi.py pour les tests")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


def _write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_path


@pytest.fixture
def simple_logi_module(monkeypatch):
  mock_logipy = types.SimpleNamespace(
    logi_led=_DummyLogiLed(),
    __spec__=None,
    __file__="logipy.py",
    __name__="logipy",
  )
  monkeypatch.setitem(sys.modules, "logipy", mock_logipy)
  mock_mqtt = types.SimpleNamespace(
    MqttLightingService=_DummyMqttService,
    __spec__=None,
    __file__="lightspeed/mqtt.py",
    __name__="lightspeed.mqtt",
  )
  monkeypatch.setitem(sys.modules, "lightspeed.mqtt", mock_mqtt)
  return _load_simple_logi_module()


def test_resolve_config_prefers_cli_over_env(simple_logi_module):
    env: Mapping[str, str] = {"LOGI_CONFIG_PATH": "env.yaml"}
    path = simple_logi_module.resolve_config_path("cli.yaml", env)
    assert path.name == "cli.yaml"


def test_resolve_config_uses_env_when_cli_missing(simple_logi_module, tmp_path):
    env_path = tmp_path / "from-env.yaml"
    env: Mapping[str, str] = {"LOGI_CONFIG_PATH": str(env_path)}
    path = simple_logi_module.resolve_config_path(None, env)
    assert path == env_path.resolve()


def test_resolve_config_defaults_to_repo_file(simple_logi_module, tmp_path, monkeypatch):
    default = tmp_path / "config.yaml"
    monkeypatch.chdir(tmp_path)
    path = simple_logi_module.resolve_config_path(None, {})
    assert path == default.resolve()


def test_validate_command_success(simple_logi_module, tmp_path, capsys):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: localhost
          client_id: alerts
        topics:
          base: foo/bar
        home_assistant:
          device_id: foo
          device_name: Foo Device
          manufacturer: TestCo
          model: RevA
        lighting:
          default_color: "#112233"
          lock_file: lock.bin
        palettes:
          alert:
            frames:
            - color: "#FF0000"
              duration_ms: 100
          warning:
            frames:
            - color: "#FFFF00"
              duration_ms: 100
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    exit_code = simple_logi_module.run_validate_command(config_path)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "✅ Config valide" in captured.out
    assert str(config_path) in captured.out


def test_validate_command_failure(simple_logi_module, tmp_path, capsys):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          client_id: alerts
        topics:
          base: foo/bar
        home_assistant:
          device_id: foo
          device_name: Foo Device
          manufacturer: TestCo
          model: RevA
        lighting:
          default_color: "#112233"
          lock_file: lock.bin
        palettes: {}
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    exit_code = simple_logi_module.run_validate_command(config_path)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "❌ Config invalide" in captured.out
    assert str(config_path) in captured.out


def test_normalize_global_args_accepts_config_after_command(simple_logi_module):
    raw_args = ["validate-config", "--config", "foo.yaml"]
    normalized = simple_logi_module._normalize_global_args(raw_args)
    assert normalized[:2] == ["--config", "foo.yaml"]
    assert normalized[2:] == ["validate-config"]