"""Optional YAML config: vault file path and QR image directory."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CotpSettings:
    """Paths from ``config.yaml``; ``None`` means use built-in defaults."""

    vault_path: Path | None
    qr_image_dir: Path | None


def config_file_path() -> Path:
    """Path to the active config file (may not exist)."""
    env = os.environ.get("COTP_CONFIG", "").strip()
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "cotp" / "config.yaml"
    return Path.home() / ".config" / "cotp" / "config.yaml"


def _optional_path_field(raw: object, key: str) -> Path | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        print(
            f"cotp: warning: config key {key!r} must be a non-empty string, ignoring",
            file=sys.stderr,
        )
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    return Path(stripped).expanduser()


def load_cotp_settings() -> CotpSettings:
    path = config_file_path()
    if not path.is_file():
        return CotpSettings(None, None)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"cotp: warning: could not read config {path}: {e}", file=sys.stderr)
        return CotpSettings(None, None)
    try:
        doc = yaml.safe_load(raw_text) if raw_text.strip() else {}
    except yaml.YAMLError as e:
        print(f"cotp: warning: invalid YAML in {path}: {e}", file=sys.stderr)
        return CotpSettings(None, None)
    if doc is None:
        return CotpSettings(None, None)
    if not isinstance(doc, dict):
        print(
            f"cotp: warning: config root must be a YAML mapping in {path}, ignoring",
            file=sys.stderr,
        )
        return CotpSettings(None, None)
    vault = _optional_path_field(doc.get("vault_path"), "vault_path")
    qr_dir = _optional_path_field(doc.get("qr_image_dir"), "qr_image_dir")
    return CotpSettings(vault_path=vault, qr_image_dir=qr_dir)


def vault_path_for_put(_png_path: Path) -> Path:
    """Vault path for ``put`` (config ``vault_path`` or the default config directory vault)."""
    s = load_cotp_settings()
    if s.vault_path is not None:
        return s.vault_path
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "cotp" / "qr-vault.yaml"
    return Path.home() / ".config" / "cotp" / "qr-vault.yaml"
