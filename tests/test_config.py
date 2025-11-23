from __future__ import annotations

import textwrap

import pytest

from lightspeed.config import ConfigError, load_config


def _write_config(tmp_path, content: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_path


def test_load_config_happy_path(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: broker.local
          port: 1884
          username: admin
          password: secret
          client_id: alerts
          keepalive: 45
        topics:
          base: foo/bar
        home_assistant:
          device_id: foo
          device_name: Foo Device
          manufacturer: TestCo
          model: RevA
        lighting:
          default_color: "#336699"
          auto_restore: false
          lock_file: lock.bin
        palettes:
          alert:
            max_duration_ms: 450
            frames:
            - color: "#FF0000"
              duration_ms: 100
            - color: "#FFFFFF"
              duration_ms: 100
          warning:
            max_duration_ms: 300
            frames:
            - color: "#FFFF00"
              duration_ms: 200
        logitech:
          profile_backup: backup.json
        observability:
          health_topic: foo/bar/health
          log_level: INFO
        """,
    )

    config = load_config(config_path)

    assert config.mqtt.port == 1884
    assert config.mqtt.keepalive == 45
    assert config.topics.color == "foo/bar/color"
    assert config.lighting.default_color == (51, 102, 153)
    assert config.palettes.alert.max_duration_ms == 450
    assert len(config.palettes.alert.frames) == 2


def test_missing_required_key_raises(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          port: 1883
          client_id: missing-host
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
        palettes: {}
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_palette_duration_limit_enforced(tmp_path):
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
          device_name: Foo
          manufacturer: Test
          model: RevA
        lighting:
          default_color: "#112233"
          lock_file: lock
        palettes:
          alert:
            max_duration_ms: 600
            frames:
            - color: "#FF0000"
              duration_ms: 600
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_env_substitution_applies_values(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: localhost
          password: "${SECRET}"
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
        palettes: {}
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    config = load_config(config_path, env={"SECRET": "s3cr3t"})

    assert config.mqtt.password == "s3cr3t"


def test_missing_env_logs_warning(tmp_path, caplog):
    config_path = _write_config(
        tmp_path,
        """
        mqtt:
          host: localhost
          password: "${SECRET}"
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
        palettes: {}
        logitech:
          profile_backup: backup.json
        observability:
          log_level: INFO
        """,
    )

    caplog.set_level("WARNING")
    config = load_config(config_path, env={})

    assert config.mqtt.password is None
    assert any("SECRET" in record.message for record in caplog.records)
