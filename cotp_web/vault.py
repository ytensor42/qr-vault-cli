"""Resolve ``key.username`` entry refs against a qr-vault.yaml mapping."""

from __future__ import annotations

from pathlib import Path

import pyotp
import yaml

from cotp_cli.main import (
    _get_vault_slot,
    _seed_from_entry,
    decode_vault_password_for_clipboard,
    entry_has_usable_seed,
    find_vault_entry_matches_by_user,
    first_username_from_entry,
    load_qr_vault_mapping,
)


class EntryRefError(ValueError):
    """Invalid entry reference or vault lookup failure."""


def parse_entry_ref(line: str) -> tuple[str, str]:
    """Parse ``key.username`` (split on the first ``.`` only)."""
    text = line.strip()
    if not text or text.startswith("#"):
        msg = "empty entry reference"
        raise EntryRefError(msg)
    if "." not in text:
        msg = f"entry reference must be key.username, got {text!r}"
        raise EntryRefError(msg)
    key, username = text.split(".", 1)
    key = key.strip()
    username = username.strip()
    if not key or not username:
        msg = f"entry reference must be key.username, got {text!r}"
        raise EntryRefError(msg)
    return key, username


def entry_ref(key: str, username: str) -> str:
    """Build internal entry id ``key.username``."""
    return f"{key.strip()}.{username.strip()}"


def load_entry_refs(path: Path) -> list[str]:
    """Load entry refs from a YAML file (vault key → list of ``{username: …}``)."""
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) if raw.strip() else None
    if not isinstance(data, dict):
        msg = f"{path} must be a YAML mapping (object) at the top level"
        raise EntryRefError(msg)

    refs: list[str] = []
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            msg = f"invalid vault key in {path!s}"
            raise EntryRefError(msg)
        cluster = key.strip()
        if isinstance(value, dict):
            slots = [value]
        elif isinstance(value, list):
            slots = value
        else:
            msg = f"key {cluster!r} must be a list of entries or one entry mapping"
            raise EntryRefError(msg)

        for item in slots:
            if not isinstance(item, dict):
                msg = f"entry under {cluster!r} must be a mapping with username"
                raise EntryRefError(msg)
            username = item.get("username")
            if not isinstance(username, str) or not username.strip():
                msg = f"entry under {cluster!r} missing username"
                raise EntryRefError(msg)
            refs.append(entry_ref(cluster, username))

    if not refs:
        msg = f"no entries in {path}"
        raise EntryRefError(msg)
    return refs


def entry_has_otp(entry: dict) -> bool:
    return entry_has_usable_seed(entry)


def summarize_entry_ref(vault_data: dict, entry_ref: str) -> dict[str, str | bool]:
    """Public fields for the web UI (no secrets)."""
    key, query_user = parse_entry_ref(entry_ref)
    entry = resolve_vault_entry(vault_data, entry_ref)
    vault_user = first_username_from_entry(entry)
    username = vault_user or query_user
    return {
        "id": entry_ref,
        "key": key,
        "username": username,
        "has_otp": entry_has_otp(entry),
    }


def resolve_vault_entry(vault_data: dict, entry_ref: str) -> dict:
    """Return the vault entry dict for ``key.username``."""
    key, username = parse_entry_ref(entry_ref)
    matches = find_vault_entry_matches_by_user(vault_data, key, username)
    if not matches:
        msg = f"no vault entry for {entry_ref!r}"
        raise EntryRefError(msg)
    if len(matches) > 1:
        msg = f"ambiguous vault entry for {entry_ref!r} ({len(matches)} matches)"
        raise EntryRefError(msg)
    _match_key, idx = matches[0]
    return _get_vault_slot(vault_data, key, idx)


def username_for_entry(entry: dict) -> str:
    username = first_username_from_entry(entry)
    if not username:
        msg = "entry has no username"
        raise EntryRefError(msg)
    return username


def password_plaintext_for_entry(entry: dict) -> str:
    raw = entry.get("password", "")
    text = raw if isinstance(raw, str) else ""
    decoded = decode_vault_password_for_clipboard(text)
    if decoded is None:
        msg = "entry has no decodable password"
        raise EntryRefError(msg)
    return decoded


def totp_code_for_entry(entry: dict) -> str:
    try:
        seed = _seed_from_entry(entry)
    except ValueError as exc:
        msg = "entry has no usable seed for TOTP"
        raise EntryRefError(msg) from exc
    return pyotp.TOTP(seed).now()


def load_vault(path: Path) -> dict:
    return load_qr_vault_mapping(path)


def resolve_entries_path(
    entries: Path,
    vault_path: Path,
    *,
    entries_raw: str | None = None,
) -> Path:
    """Resolve the entries list file path.

    - Path with a directory prefix (absolute, ``~/…``, ``foo/bar``, ``./x``):
      try that OS path first; if missing, try ``<vault-dir>/<basename>``.
    - Bare filename (``entries.yaml``): only ``<vault-dir>/<filename>``.
    """
    user = entries.expanduser()
    vault_dir = vault_path.expanduser().resolve().parent
    raw = (entries_raw if entries_raw is not None else str(entries)).strip()
    has_prefix = (
        user.is_absolute()
        or raw.startswith(("/", "~/", "./", "../"))
        or (raw.startswith("~") and len(raw) > 1)
        or "/" in raw
    )

    if has_prefix:
        os_candidate = (user if user.is_absolute() else (Path.cwd() / user)).resolve()
        if os_candidate.is_file():
            return os_candidate
        vault_candidate = vault_dir / user.name
        if vault_candidate.is_file():
            return vault_candidate.resolve()
        return os_candidate

    vault_candidate = vault_dir / user.name
    if vault_candidate.is_file():
        return vault_candidate.resolve()
    return vault_candidate
