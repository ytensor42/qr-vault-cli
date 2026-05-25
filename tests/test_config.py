from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import cotp_cli.main as main_mod
from cotp_cli.config import (
    CotpSettings,
    config_file_path,
    load_cotp_settings,
    vault_path_for_put,
)


def test_config_file_path_respects_cotp_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    p = tmp_path / "my.yaml"
    monkeypatch.setenv("COTP_CONFIG", str(p))
    assert config_file_path() == p


def test_config_file_path_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("COTP_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config_file_path() == tmp_path / "cotp" / "config.yaml"


def test_load_cotp_settings_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("COTP_CONFIG", str(tmp_path / "nope.yaml"))
    assert load_cotp_settings() == CotpSettings(None, None)


def test_load_cotp_settings_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "vault_path": str(tmp_path / "vault" / "qr-vault.yaml"),
                "qr_image_dir": str(tmp_path / "qr"),
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("COTP_CONFIG", str(cfg))
    s = load_cotp_settings()
    assert s.vault_path == tmp_path / "vault" / "qr-vault.yaml"
    assert s.qr_image_dir == tmp_path / "qr"


def test_vault_path_for_put_uses_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "central" / "qr-vault.yaml"
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"vault_path": str(vault)}), encoding="utf-8")
    monkeypatch.setenv("COTP_CONFIG", str(cfg))
    png = tmp_path / "elsewhere" / "QR-c-u.png"
    assert vault_path_for_put(png) == vault


def test_vault_path_for_put_fallback_beside_png(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("COTP_CONFIG", str(tmp_path / "missing.yaml"))
    png = tmp_path / "shots" / "QR-c-u.png"
    assert vault_path_for_put(png) == png.parent / "qr-vault.yaml"


def test_default_qr_dir_from_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    qr = tmp_path / "custom-qr"
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"qr_image_dir": str(qr)}), encoding="utf-8")
    monkeypatch.setenv("COTP_CONFIG", str(cfg))
    assert main_mod.default_qr_dir() == qr


def test_default_vault_path_from_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "v.yaml"
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"vault_path": str(vault)}), encoding="utf-8")
    monkeypatch.setenv("COTP_CONFIG", str(cfg))
    assert main_mod.default_vault_path() == vault


def test_default_vault_path_without_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COTP_CONFIG", str(tmp_path / "missing.yaml"))
    assert main_mod.default_vault_path() == tmp_path / ".config" / "cotp" / "qr-vault.yaml"
