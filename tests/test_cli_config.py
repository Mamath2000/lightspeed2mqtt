from __future__ import annotations

import importlib.util
import logging
import sys
import textwrap
import types
from pathlib import Path
from typing import Mapping

import pytest

from lightspeed.config import load_config

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


def test_validate_command_failure_override_duration(simple_logi_module, tmp_path, capsys):
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
        effects:
          override_duration_seconds: 999
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
    assert "override_duration_seconds" in captured.out


def test_normalize_global_args_accepts_config_after_command(simple_logi_module):
    raw_args = ["validate-config", "--config", "foo.yaml"]
    normalized = simple_logi_module._normalize_global_args(raw_args)
    assert normalized[:2] == ["--config", "foo.yaml"]
    assert normalized[2:] == ["validate-config"]


def _load_profile(tmp_path: Path):
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
    palettes: {}
    logitech:
      profile_backup: backup.json
    observability:
      log_level: INFO
    """,
  )
  return load_config(config_path)


def test_pilot_state_topic_derives_from_base(simple_logi_module, tmp_path):
  profile = _load_profile(tmp_path)
  assert simple_logi_module._pilot_state_topic(profile) == profile.topics.mode_state


def test_read_pilot_switch_state_returns_bool(simple_logi_module, tmp_path, monkeypatch):
  profile = _load_profile(tmp_path)

  created_clients = []

  class _FakeBootstrapClient:
    def __init__(self, *_, **__):
      self.on_connect = None
      self.on_message = None
      self.subscriptions = []
      created_clients.append(self)

    def username_pw_set(self, *_args, **_kwargs):
      return None

    def connect(self, *_args, **_kwargs):
      if self.on_connect:
        self.on_connect(self, None, None, 0)

    def loop_start(self):
      return None

    def loop_stop(self):
      return None

    def disconnect(self):
      return None

    def subscribe(self, topic: str, qos: int):
      import types as _types

      self.subscriptions.append((topic, qos))
      if self.on_message:
        self.on_message(
          self,
          None,
          _types.SimpleNamespace(topic=topic, payload=b"OFF"),
        )

  monkeypatch.setattr(
    simple_logi_module,
    "bootstrap_mqtt",
    types.SimpleNamespace(Client=_FakeBootstrapClient),
  )
  logger = logging.getLogger("test.bootstrap")

  state = simple_logi_module._read_pilot_switch_state(profile, logger=logger)

  assert state is False
  assert created_clients[0].subscriptions == [(profile.topics.mode_state, 1)]


def test_read_pilot_switch_state_handles_errors(simple_logi_module, tmp_path, monkeypatch):
  profile = _load_profile(tmp_path)

  class _FailClient:
    def __init__(self, *_, **__):
      self.on_connect = None
      self.on_message = None

    def username_pw_set(self, *_args, **_kwargs):
      return None

    def connect(self, *_args, **_kwargs):
      raise RuntimeError("boom")

    def loop_start(self):
      return None

    def loop_stop(self):
      return None

    def disconnect(self):
      return None

  monkeypatch.setattr(
    simple_logi_module,
    "bootstrap_mqtt",
    types.SimpleNamespace(Client=_FailClient),
  )
  logger = logging.getLogger("test.bootstrap.error")

  state = simple_logi_module._read_pilot_switch_state(profile, logger=logger)

  assert state is None