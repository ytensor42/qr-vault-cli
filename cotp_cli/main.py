"""cotp: QR PNG seed extraction, vault (qr-vault.yaml), TOTP get, random password."""

from __future__ import annotations

import argparse
import base64
import binascii
import re
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from PIL import Image

from cotp_cli import __version__
from cotp_cli.config import load_cotp_settings, vault_path_for_put

_RANDOM_PASSWORD_LENGTH = 12
_RANDOM_SPECIAL = "!@#$%^&*-_=+"


class VaultUpdateError(ValueError):
    """Vault put refused: not exactly one identity match; ``hints`` lists related entries."""

    def __init__(self, message: str, hints: str = "") -> None:
        super().__init__(message)
        self.hints = hints


def random_password_12() -> str:
    """Cryptographically random password: >=1 upper, lower, digit, special; length 12."""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    pool = lower + upper + digits + _RANDOM_SPECIAL

    chars: list[str] = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(_RANDOM_SPECIAL),
    ]
    for _ in range(_RANDOM_PASSWORD_LENGTH - len(chars)):
        chars.append(secrets.choice(pool))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def encode_password_plain_to_vault_b64(plain: str) -> str:
    """Encode a plain password for the vault ``password`` field (standard Base64, UTF-8)."""
    return base64.standard_b64encode(plain.encode("utf-8")).decode("ascii")


def format_random_password_line(plain: str) -> str:
    """``<plain> <base64>`` for stdout (UTF-8 bytes encoded with standard Base64)."""
    return f"{plain} {encode_password_plain_to_vault_b64(plain)}"


def read_password_interactive_b64() -> str:
    """Prompt twice (hidden); on match return vault Base64. ``Ctrl+C`` / EOF → exit 130."""
    import getpass  # noqa: PLC0415

    while True:
        try:
            first = getpass.getpass("Password: ")
            second = getpass.getpass("Verify password: ")
        except (KeyboardInterrupt, EOFError):
            print(file=sys.stderr)
            raise SystemExit(130) from None
        if first != second:
            print("error: passwords do not match", file=sys.stderr)
            continue
        return encode_password_plain_to_vault_b64(first)


def resolve_put_password(password_arg: str | None) -> str | None:
    """``None`` = leave vault password unchanged; ``-p`` alone = interactive Base64."""
    if password_arg is None:
        return None
    if password_arg == "":
        return read_password_interactive_b64()
    return password_arg


def default_qr_dir() -> Path:
    s = load_cotp_settings()
    if s.qr_image_dir is not None:
        return s.qr_image_dir
    return Path.home() / "Downloads" / "Screenshots"


def newest_png_in_dir(dir_path: Path) -> Path:
    if not dir_path.is_dir():
        msg = f"error: default QR folder does not exist or is not a directory: {dir_path}"
        raise FileNotFoundError(msg)
    candidates = [
        p for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() == ".png"
    ]
    if not candidates:
        msg = f"error: no .png files in {dir_path}"
        raise FileNotFoundError(msg)
    return max(candidates, key=lambda p: p.stat().st_mtime)


def with_default_png_suffix(path: Path) -> Path:
    """If ``path`` has no file extension, treat it as ``.png``."""
    return path if path.suffix else path.with_suffix(".png")


def resolve_png_path(raw: Path | None) -> Path:
    """Default folder ``~/Downloads/Screenshots``; relative names are under it."""
    base = default_qr_dir()
    if raw is None:
        return newest_png_in_dir(base)
    p = raw.expanduser()
    if p.is_absolute():
        return with_default_png_suffix(p).resolve()
    return with_default_png_suffix(base / p).resolve()


def otpauth_secret(uri: str) -> str | None:
    if not uri.startswith("otpauth://"):
        return None
    parsed = urlparse(uri)
    if parsed.netloc not in ("totp", "hotp"):
        return None
    secret_vals = parse_qs(parsed.query).get("secret")
    if not secret_vals:
        return None
    return secret_vals[0]


def extract_seeds_from_png(path: Path) -> list[str]:
    try:
        from pyzbar.pyzbar import decode
    except ImportError:
        raise ImportError(
            "pyzbar requires the zbar shared library. "
            "macOS: brew install zbar. Debian/Ubuntu: sudo apt install libzbar0."
        ) from None

    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    out: list[str] = []
    for obj in decode(img):
        try:
            data = obj.data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        secret = otpauth_secret(data)
        if secret:
            out.append(secret)
    return out


def parse_qr_filename(path: Path) -> tuple[str, str] | None:
    """Parse ``QR-<cluster>-<username>[-<ignored>...].png`` → (cluster, username).

    Extra ``-`` segments after username are ignored (not stored as vault labels).
    """
    if path.suffix.lower() != ".png":
        return None
    stem = path.stem
    if not stem.startswith("QR-"):
        return None
    body = stem[3:]
    if not body or body.startswith("-") or body.endswith("-"):
        return None
    parts = body.split("-")
    if len(parts) < 2 or any(p == "" for p in parts):
        return None
    return parts[0], parts[1]


def _looks_like_vault_entry(value: object) -> bool:
    return isinstance(value, dict) and ("seed" in value or "username" in value)


def _iter_slots_under_key(value: object) -> list[tuple[int | None, dict]]:
    """One mapping entry (``idx is None``) or each list element under a vault key."""
    if _looks_like_vault_entry(value):
        return [(None, value)]
    if isinstance(value, list):
        return [(i, item) for i, item in enumerate(value) if _looks_like_vault_entry(item)]
    return []


def entry_matches_identity(entry: dict, username: str, labels: list[str]) -> bool:
    """True when entry username and labels multiset match the query."""
    try:
        vault_user = first_username_from_entry(entry)
    except ValueError:
        return False
    if vault_user != username.strip():
        return False
    raw_labels = entry.get("labels") or []
    if not isinstance(raw_labels, list):
        return False
    vault_labels = [str(x).strip() for x in raw_labels]
    want = [str(x).strip() for x in labels]
    return sorted(vault_labels) == sorted(want)


def find_vault_entry_matches(
    data: dict,
    cluster_key: str,
    username: str,
    labels: list[str],
) -> list[tuple[str, int | None]]:
    """``(vault_key, slot_index)`` for entries under ``cluster_key`` matching identity."""
    value = data.get(cluster_key)
    if value is None:
        return []
    return [
        (cluster_key, idx)
        for idx, entry in _iter_slots_under_key(value)
        if entry_matches_identity(entry, username, labels)
    ]


def find_vault_entry_matches_by_user(
    data: dict,
    cluster_key: str,
    username: str,
) -> list[tuple[str, int | None]]:
    """Entries under ``cluster_key`` with matching username (labels ignored)."""
    value = data.get(cluster_key)
    if value is None:
        return []
    want = username.strip()
    out: list[tuple[str, int | None]] = []
    for idx, entry in _iter_slots_under_key(value):
        try:
            if first_username_from_entry(entry) == want:
                out.append((cluster_key, idx))
        except ValueError:
            continue
    return out


def _seed_from_entry_or_empty(entry: dict) -> str:
    seed = entry.get("seed")
    return seed if isinstance(seed, str) else ""


def iter_all_vault_slots(data: dict) -> list[tuple[str, int | None, dict]]:
    """All ``(vault_key, slot_index, entry)`` in the vault mapping."""
    out: list[tuple[str, int | None, dict]] = []
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        for idx, entry in _iter_slots_under_key(value):
            out.append((key, idx, entry))
    return out


def entry_labels_list(entry: dict) -> list[str]:
    raw = entry.get("labels") or []
    if not isinstance(raw, list):
        return []
    return [s for x in raw if (s := str(x).strip())]


def _format_vault_hint_line(
    key: str,
    idx: int | None,
    entry: dict,
    reasons: list[str] | None = None,
) -> str:
    try:
        vault_user = first_username_from_entry(entry)
    except ValueError:
        vault_user = "?"
    lbl = entry_labels_list(entry)
    slot = f"key={key!r}" if idx is None else f"key={key!r} index={idx}"
    suffix = f"  ({'; '.join(reasons)})" if reasons else ""
    return f"    {slot}  username={vault_user!r}  labels={lbl!r}{suffix}"


def _partial_match_reasons(
    key: str,
    entry: dict,
    cluster_key: str,
    username: str,
    labels: list[str],
) -> list[str]:
    want_user = username.strip()
    want_labels = {s for x in labels if (s := str(x).strip())}
    reasons: list[str] = []
    if key == cluster_key:
        reasons.append("same key")
    try:
        vault_user = first_username_from_entry(entry)
    except ValueError:
        vault_user = None
    if vault_user == want_user:
        reasons.append("username matches")
    overlap = want_labels & set(entry_labels_list(entry))
    if overlap:
        reasons.append(f"shared labels: {sorted(overlap)!r}")
    return reasons


def build_vault_update_hints(
    data: dict,
    cluster_key: str,
    username: str,
    labels: list[str],
    exact_matches: list[tuple[str, int | None]],
) -> str:
    """Human-readable related entries when an update is not allowed."""
    lines = [
        "vault update skipped; adjust key, username, or labels and retry.",
        f"  requested: key={cluster_key!r}  username={username!r}  labels={labels!r}",
    ]
    exact_set = set(exact_matches)

    if len(exact_matches) > 1:
        lines.append(f"  exact matches ({len(exact_matches)}):")
        for key, idx in exact_matches:
            lines.append(_format_vault_hint_line(key, idx, _get_vault_slot(data, key, idx)))

    related: list[tuple[str, int | None, dict, list[str]]] = []
    for key, idx, entry in iter_all_vault_slots(data):
        if (key, idx) in exact_set:
            continue
        reasons = _partial_match_reasons(key, entry, cluster_key, username, labels)
        if reasons:
            related.append((key, idx, entry, reasons))

    if related:
        lines.append("  related vault entries:")
        for key, idx, entry, reasons in related:
            lines.append(_format_vault_hint_line(key, idx, entry, reasons))
    elif cluster_key in data and not _iter_slots_under_key(data[cluster_key]):
        lines.append(f"  (vault key {cluster_key!r} exists but has no valid entries)")
    elif cluster_key not in data and not related:
        lines.append("  (no vault entries share this key, username, or labels)")

    return "\n".join(lines)


def _get_vault_slot(data: dict, key: str, idx: int | None) -> dict:
    value = data[key]
    if idx is None:
        if not _looks_like_vault_entry(value):
            raise ValueError(f"error: vault key {key!r} is not a valid entry")
        return value
    if not isinstance(value, list) or idx >= len(value):
        raise ValueError(f"error: vault list slot missing under {key!r}")
    entry = value[idx]
    if not _looks_like_vault_entry(entry):
        raise ValueError(f"error: vault list slot under {key!r} is not a valid entry")
    return entry


def _make_vault_entry(
    username: str,
    labels: list[str],
    seed: str,
    password: str,
) -> dict:
    return {
        "seed": seed,
        "username": username,
        "password": password,
        "labels": list(labels),
    }


def _append_vault_entry(data: dict, key: str, entry: dict) -> None:
    value = data.get(key)
    if value is None:
        data[key] = [entry]
        return
    if _looks_like_vault_entry(value):
        data[key] = [value, entry]
        return
    if isinstance(value, list):
        value.append(entry)
        return
    msg = f"error: vault key {key!r} is not a valid entry or list"
    raise ValueError(msg)


def _replace_vault_slot(data: dict, key: str, idx: int | None, entry: dict) -> None:
    if idx is None:
        data[key] = [entry]
        return
    slot = data[key]
    if not isinstance(slot, list):
        raise ValueError(f"error: vault key {key!r} is not a list")
    slot[idx] = entry


def _set_vault_slot(data: dict, key: str, idx: int | None, entry: dict) -> None:
    _replace_vault_slot(data, key, idx, entry)


def merge_qr_vault_yaml(
    vault_path: Path,
    cluster_name: str,
    username: str,
    labels: list[str],
    seed: str | None,
    password: str | None,
    *,
    match_identity_labels: bool = True,
) -> None:
    """Merge into ``qr-vault.yaml``; update one match, append new username under an existing key."""
    if vault_path.is_file():
        raw = vault_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) if raw.strip() else {}
    else:
        data = {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        msg = f"error: {vault_path} must be a YAML mapping (object) at the top level"
        raise ValueError(msg)

    if match_identity_labels:
        matches = find_vault_entry_matches(data, cluster_name, username, labels)
    else:
        matches = find_vault_entry_matches_by_user(data, cluster_name, username)

    if len(matches) != 1:
        msg = ""
        if len(matches) > 1:
            if match_identity_labels:
                msg = (
                    f"error: {len(matches)} vault entries match key={cluster_name!r} "
                    f"username={username!r} labels={labels!r}; refusing to update"
                )
            else:
                msg = (
                    f"error: {len(matches)} vault entries match key={cluster_name!r} "
                    f"username={username!r}; refusing to update"
                )
        elif cluster_name in data and match_identity_labels:
            user_matches = find_vault_entry_matches_by_user(data, cluster_name, username)
            if user_matches:
                msg = (
                    f"error: vault key {cluster_name!r} has username={username!r} "
                    f"with different labels than {labels!r}; refusing to overwrite"
                )
                hints = build_vault_update_hints(
                    data, cluster_name, username, labels, user_matches
                )
                raise VaultUpdateError(msg, hints)
        if msg:
            hint_matches = (
                matches
                if match_identity_labels
                else find_vault_entry_matches(data, cluster_name, username, labels)
            )
            hints = build_vault_update_hints(
                data, cluster_name, username, labels, hint_matches
            )
            raise VaultUpdateError(msg, hints)

    if len(matches) == 1:
        key, idx = matches[0]
        prev = _get_vault_slot(data, key, idx)
        raw_p = prev.get("password", "")
        prev_pwd = raw_p if isinstance(raw_p, str) else ""
        seed_out = seed if seed is not None else _seed_from_entry_or_empty(prev)
        new_entry = _make_vault_entry(
            username,
            labels,
            seed_out,
            password if password is not None else prev_pwd,
        )
        _set_vault_slot(data, key, idx, new_entry)
    elif cluster_name not in data:
        seed_out = "" if seed is None else seed
        pwd = "" if password is None else password
        data[cluster_name] = [_make_vault_entry(username, labels, seed_out, pwd)]
    else:
        seed_out = "" if seed is None else seed
        pwd = "" if password is None else password
        _append_vault_entry(
            data,
            cluster_name,
            _make_vault_entry(username, labels, seed_out, pwd),
        )

    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    vault_path.write_text(text, encoding="utf-8")


def default_cotp_config_dir() -> Path:
    return Path.home() / ".config" / "cotp"


def default_vault_path() -> Path:
    s = load_cotp_settings()
    if s.vault_path is not None:
        return s.vault_path
    return default_cotp_config_dir() / "qr-vault.yaml"


def load_qr_vault_mapping(path: Path) -> dict:
    if not path.is_file():
        msg = f"error: vault file not found: {path}"
        raise FileNotFoundError(msg)
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) if raw.strip() else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        msg = f"error: {path} must be a YAML mapping (object) at the top level"
        raise ValueError(msg)
    return data


def labels_from_csv(csv: str) -> list[str]:
    return [p.strip() for p in csv.split(",") if p.strip() != ""]


def labels_for_vault_entry(extra: list[str]) -> list[str]:
    """Vault ``labels``: user-provided extras only (deduped, order kept; no key/username)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in extra:
        label = str(raw).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        out.append(label)
    return out


def query_labels_for_get(labels_csv: str | None) -> list[str]:
    """Labels for ``get``: the CSV extras only (deduped; no key/username)."""
    extra = labels_from_csv(labels_csv) if labels_csv is not None else []
    return labels_for_vault_entry(extra)


def wildcard_match(pattern: str, value: str) -> bool:
    """Match ``value`` against ``pattern`` where ``*`` is any run of characters.

    Without ``*`` this is an exact (case-sensitive) string comparison, so existing
    queries behave unchanged; all other characters are matched literally.
    """
    pat = pattern.strip()
    val = value.strip()
    if "*" not in pat:
        return pat == val
    regex = ".*".join(re.escape(part) for part in pat.split("*"))
    return re.fullmatch(regex, val) is not None


def entry_labels_match_exact(entry: dict, labels: list[str]) -> bool:
    """Every vault label matches some query pattern and vice versa (``*`` allowed)."""
    raw = entry.get("labels") or []
    if not isinstance(raw, list):
        return False
    vault_labels = [s for x in raw if (s := str(x).strip())]
    want = [s for x in labels if (s := str(x).strip())]
    vault_covered = all(any(wildcard_match(p, vl) for p in want) for vl in vault_labels)
    want_covered = all(any(wildcard_match(p, vl) for vl in vault_labels) for p in want)
    return vault_covered and want_covered


def entry_has_all_labels(entry: dict, labels: list[str]) -> bool:
    want = [str(x).strip() for x in labels if str(x).strip()]
    if not want:
        return False
    vault_labels = entry_labels_list(entry)
    return all(any(wildcard_match(p, vl) for vl in vault_labels) for p in want)


def find_get_matches(
    data: dict,
    cluster: str | None,
    username: str | None,
    query_labels: list[str] | None,
    *,
    label_mode: str,
) -> list[tuple[str, int | None, dict]]:
    """``label_mode``: ``none`` | ``subset`` (vault labels ⊇ want) | ``exact`` (multiset equal)."""
    matches: list[tuple[str, int | None, dict]] = []
    for key, idx, entry in iter_all_vault_slots(data):
        if cluster is not None and not wildcard_match(cluster, key):
            continue
        if username is not None:
            try:
                if not wildcard_match(username, first_username_from_entry(entry)):
                    continue
            except ValueError:
                continue
        if label_mode == "subset":
            if query_labels is None or not entry_has_all_labels(entry, query_labels):
                continue
        elif label_mode == "exact":
            if query_labels is None or not entry_labels_match_exact(entry, query_labels):
                continue
        matches.append((key, idx, entry))
    return matches


def _seed_from_entry(entry: dict) -> str:
    seed = entry.get("seed")
    if not isinstance(seed, str) or not seed:
        raise ValueError("entry has no usable seed string")
    return seed


def first_username_from_entry(entry: dict) -> str:
    """Username field as string, or first element if stored as a list."""
    u = entry.get("username")
    if isinstance(u, list):
        if not u:
            raise ValueError("username list is empty")
        first = u[0]
        if not isinstance(first, str) or not first.strip():
            raise ValueError("first username is empty")
        return first.strip()
    if isinstance(u, str) and u.strip():
        return u.strip()
    raise ValueError("entry has no usable username")


def _first_slot_entry_for_key(data: dict, cluster_name: str) -> dict:
    value = data.get(cluster_name)
    if value is None:
        raise KeyError(f"no vault entry for cluster {cluster_name!r}")
    slots = _iter_slots_under_key(value)
    if not slots:
        raise KeyError(f"no vault entry for cluster {cluster_name!r}")
    return slots[0][1]


def seed_for_cluster_name_only(data: dict, cluster_name: str) -> str:
    """Resolve seed for a cluster key; uses the first slot under the key."""
    entry = _first_slot_entry_for_key(data, cluster_name)
    first_username_from_entry(entry)
    return _seed_from_entry(entry)


def seed_for_cluster_username_any_labels(data: dict, cluster_name: str, username: str) -> str:
    matches = find_vault_entry_matches_by_user(data, cluster_name, username)
    if len(matches) != 1:
        if not matches:
            raise ValueError(
                f"username mismatch: no entry for {cluster_name!r} with username {username!r}"
            )
        raise ValueError(
            f"username mismatch: {len(matches)} entries for {cluster_name!r} "
            f"with username {username!r}"
        )
    _key, idx = matches[0]
    return _seed_from_entry(_get_vault_slot(data, cluster_name, idx))


def seed_for_cluster_user_labels(
    data: dict,
    cluster_name: str,
    username: str,
    labels: list[str],
) -> str:
    matches = find_vault_entry_matches(data, cluster_name, username, labels)
    if len(matches) != 1:
        if not matches:
            raise ValueError(
                f"no vault entry for {cluster_name!r} with username {username!r} "
                f"and labels {labels!r}"
            )
        raise ValueError(
            f"{len(matches)} vault entries match {cluster_name!r} "
            f"username={username!r} labels={labels!r}"
        )
    _key, idx = matches[0]
    return _seed_from_entry(_get_vault_slot(data, cluster_name, idx))


def totp_parts(seed: str) -> tuple[str, str]:
    import pyotp  # noqa: PLC0415

    clock = datetime.now().strftime("%H:%M:%S")
    code = pyotp.TOTP(seed).now()
    return clock, code


def entry_has_usable_seed(entry: dict) -> bool:
    seed = entry.get("seed")
    return isinstance(seed, str) and bool(seed.strip())


def format_labels_csv_for_line(entry: dict) -> str:
    """Comma-separated labels for one-line ``get`` output (no spaces around commas)."""
    return ",".join(entry_labels_list(entry))


def clipboard_marker_for_get_line(
    entry: dict,
    otp_code: str | None,
    *,
    totp_to_clipboard: bool,
) -> str | None:
    """``password`` or ``totp`` when that value is copied to the clipboard; else ``None``."""
    if totp_to_clipboard and otp_code is not None:
        return "totp"
    if not totp_to_clipboard:
        raw_pw = entry.get("password", "")
        pw_field = raw_pw if isinstance(raw_pw, str) else ""
        if decode_vault_password_for_clipboard(pw_field) is not None:
            return "password"
    return None


def format_get_output_line(
    vault_key: str,
    username: str,
    entry: dict,
    *,
    timestamp: str | None = None,
    otp_code: str | None = None,
    clipboard: str | None = None,
) -> str:
    """One line: ``HH:MM:SS key/username/… [otp] [labels]`` (clipboard marker in the line)."""
    ts = timestamp if timestamp is not None else datetime.now().strftime("%H:%M:%S")
    if clipboard == "password":
        identity = f"{vault_key}/{username}/[**pwd**]"
    elif clipboard == "totp":
        identity = f"{vault_key}/{username}/pwd"
    else:
        identity = f"{vault_key}/{username}"
    parts = [ts, identity]
    if otp_code is not None:
        if clipboard == "totp":
            parts.append(f"[**{otp_code}**]")
        else:
            parts.append(otp_code)
    labels_csv = format_labels_csv_for_line(entry)
    if labels_csv:
        parts.append(labels_csv)
    return " ".join(parts)


def format_get_output(
    vault_key: str,
    username: str,
    entry: dict,
    *,
    timestamp: str | None = None,
    otp_code: str | None = None,
) -> str:
    """Multi-line stdout for a single ``get`` match (OTP line omitted when ``otp_code`` is None)."""
    ts = timestamp if timestamp is not None else datetime.now().strftime("%H:%M:%S")
    fields: list[tuple[str, str]] = [
        ("Timestamp", ts),
        ("Key", vault_key),
        ("Username", username),
    ]
    if otp_code is not None:
        fields.append(("OTP", otp_code))
    fields.append(("Labels", ", ".join(entry_labels_list(entry))))
    label_width = max(len(name) for name, _ in fields)
    return "\n".join(f"{name:{label_width}}: {value}" for name, value in fields)


def _otp_for_get_entry(entry: dict, default_clock: str) -> tuple[str, str | None]:
    """Return ``(timestamp, otp_code)``; ``otp_code`` is None when the entry has no seed."""
    if not entry_has_usable_seed(entry):
        return default_clock, None
    try:
        return totp_parts(_seed_from_entry(entry))
    except ValueError:
        return default_clock, None


def format_totp_with_clock(seed: str) -> str:
    clock, code = totp_parts(seed)
    return f"{clock} {code}"


NO_MATCH_LINE = "no matched data"


def decode_vault_password_for_clipboard(raw: str) -> str | None:
    """Decode vault ``password`` field from standard Base64 to UTF-8 text, or None."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return base64.standard_b64decode(raw.strip()).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None


def copy_text_to_clipboard(text: str) -> None:
    """Copy UTF-8 text to the OS clipboard (macOS ``pbcopy``, Linux ``wl-copy`` / ``xclip`` / ``xsel``)."""
    import platform
    import shutil
    import subprocess

    data = text.encode("utf-8")
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["pbcopy"], input=data, check=True)
        return
    if system == "Linux":
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=data, check=True)
            return
        if shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=data, check=True)
            return
        if shutil.which("xsel"):
            subprocess.run(["xsel", "--clipboard", "--input"], input=data, check=True)
            return
    msg = "clipboard: need pbcopy (macOS), or wl-copy / xclip / xsel (Linux)"
    raise OSError(msg)


def find_get_matches_for_query(
    data: dict,
    cluster: str | None,
    username: str | None,
    query_labels: list[str] | None,
    *,
    strict_labels: bool = False,
) -> list[tuple[str, int | None, dict]]:
    """All vault slots matching a ``get`` query (may be empty)."""
    if strict_labels:
        if cluster is not None and username is not None:
            label_mode = "exact"
        else:
            label_mode = "subset"
        return find_get_matches(data, cluster, username, query_labels, label_mode=label_mode)
    if cluster is not None or username is not None:
        return find_get_matches(data, cluster, username, None, label_mode="none")
    raise ValueError("get requires a cluster (KEY), username (-u), or --labels")


def _display_username(entry: dict, cli_username: str | None) -> str:
    """Show the entry's real username; fall back to a concrete (non-wildcard) CLI value."""
    try:
        return first_username_from_entry(entry)
    except ValueError:
        if cli_username is not None and "*" not in cli_username:
            return cli_username.strip()
        raise


def run_query(
    cluster: str | None,
    username: str | None,
    query_labels: list[str] | None,
    *,
    strict_labels: bool = False,
    totp_to_clipboard: bool = False,
    wide_output: bool = False,
) -> None:
    path = default_vault_path()
    try:
        data = load_qr_vault_mapping(path)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    try:
        matches = find_get_matches_for_query(
            data, cluster, username, query_labels, strict_labels=strict_labels
        )
    except ValueError:
        print(NO_MATCH_LINE)
        return

    if not matches:
        print(NO_MATCH_LINE)
        return

    if len(matches) > 1:
        default_clock = datetime.now().strftime("%H:%M:%S")
        for match_key, _idx, entry in matches:
            try:
                show_user = _display_username(entry, username)
            except ValueError:
                continue
            clock, otp_code = _otp_for_get_entry(entry, default_clock)
            print(format_get_output_line(match_key, show_user, entry, timestamp=clock, otp_code=otp_code))
        return

    match_key, _idx, entry = matches[0]
    try:
        show_user = _display_username(entry, username)
    except ValueError:
        print(NO_MATCH_LINE)
        return

    clock, otp_code = _otp_for_get_entry(entry, datetime.now().strftime("%H:%M:%S"))
    if wide_output:
        print(format_get_output(match_key, show_user, entry, timestamp=clock, otp_code=otp_code))
        if not totp_to_clipboard:
            raw_pw = entry.get("password", "")
            pw_field = raw_pw if isinstance(raw_pw, str) else ""
            decoded_pw = decode_vault_password_for_clipboard(pw_field)
            if pw_field.strip() and decoded_pw is None:
                print(
                    "warning: password is not valid standard Base64 (UTF-8); skipping password clipboard",
                    file=sys.stderr,
                )
            if decoded_pw is not None:
                try:
                    copy_text_to_clipboard(decoded_pw)
                except OSError as e:
                    print(f"warning: could not copy password to clipboard: {e}", file=sys.stderr)
                else:
                    print("password is copied to clipboard", file=sys.stderr)
        if totp_to_clipboard and otp_code is not None:
            try:
                copy_text_to_clipboard(otp_code)
            except OSError as e:
                print(f"warning: could not copy TOTP to clipboard: {e}", file=sys.stderr)
            else:
                print("totp value is copied to clipboard", file=sys.stderr)
        return

    line_clipboard = clipboard_marker_for_get_line(
        entry, otp_code, totp_to_clipboard=totp_to_clipboard
    )
    print(
        format_get_output_line(
            match_key,
            show_user,
            entry,
            timestamp=clock,
            otp_code=otp_code,
            clipboard=line_clipboard,
        )
    )

    if line_clipboard == "password":
        raw_pw = entry.get("password", "")
        pw_field = raw_pw if isinstance(raw_pw, str) else ""
        decoded_pw = decode_vault_password_for_clipboard(pw_field)
        assert decoded_pw is not None
        try:
            copy_text_to_clipboard(decoded_pw)
        except OSError as e:
            print(f"warning: could not copy password to clipboard: {e}", file=sys.stderr)
    elif not totp_to_clipboard:
        raw_pw = entry.get("password", "")
        pw_field = raw_pw if isinstance(raw_pw, str) else ""
        if pw_field.strip() and decode_vault_password_for_clipboard(pw_field) is None:
            print(
                "warning: password is not valid standard Base64 (UTF-8); skipping password clipboard",
                file=sys.stderr,
            )

    if line_clipboard == "totp" and otp_code is not None:
        try:
            copy_text_to_clipboard(otp_code)
        except OSError as e:
            print(f"warning: could not copy TOTP to clipboard: {e}", file=sys.stderr)


def run_put_metadata_only(
    password: str | None,
    *,
    cluster: str,
    username: str,
    labels_csv: str | None = None,
) -> None:
    """Update vault metadata (labels/password) without reading a QR PNG; seed unchanged if present."""
    cluster_name = cluster.strip()
    username_val = username.strip()
    if not cluster_name or not username_val:
        print("error: cluster (key) and username must be non-empty", file=sys.stderr)
        sys.exit(1)
    cli_extra = labels_from_csv(labels_csv) if labels_csv is not None else []
    vault_labels = labels_for_vault_entry(cli_extra)
    vault_file = default_vault_path()
    try:
        merge_qr_vault_yaml(
            vault_file,
            cluster_name,
            username_val,
            vault_labels,
            None,
            password,
            match_identity_labels=False,
        )
    except VaultUpdateError as e:
        print(str(e), file=sys.stderr)
        if e.hints:
            print(e.hints, file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def run_save_from_png(
    png_arg: Path | None,
    password: str | None,
    *,
    cluster: str | None = None,
    username: str | None = None,
    labels_csv: str | None = None,
) -> None:
    if (cluster is None) != (username is None):
        print("error: cluster (key) and username must be given together", file=sys.stderr)
        sys.exit(1)
    if png_arg is None:
        if cluster is None or username is None:
            print(
                "error: put without -f requires KEY and username "
                "(metadata-only: existing entry or no QR seed)",
                file=sys.stderr,
            )
            sys.exit(1)
        run_put_metadata_only(
            password,
            cluster=cluster,
            username=username,
            labels_csv=labels_csv,
        )
        return
    try:
        png_path = resolve_png_path(png_arg)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if not png_path.is_file():
        print(f"error: not a file: {png_path}", file=sys.stderr)
        sys.exit(1)
    try:
        seeds = extract_seeds_from_png(png_path)
    except ImportError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if not seeds:
        print("error: no otpauth://totp or otpauth://hotp QR with secret= found", file=sys.stderr)
        sys.exit(1)
    for s in seeds:
        print(s)

    parsed = parse_qr_filename(png_path)

    if cluster is not None and username is not None:
        cluster_name = cluster.strip()
        username_val = username.strip()
        if not cluster_name or not username_val:
            print("error: cluster (key) and username must be non-empty", file=sys.stderr)
            sys.exit(1)
    elif parsed is not None:
        cluster_name, username_val = parsed
    else:
        print(
            "warning: filename is not QR-<cluster>-<username>[...].png; "
            "skipping qr-vault.yaml (use: cotp put <key> <username> [-l labels] [-f png]).",
            file=sys.stderr,
        )
        return

    cli_extra = labels_from_csv(labels_csv) if labels_csv is not None else []
    vault_labels = labels_for_vault_entry(cli_extra)
    seed_for_vault = seeds[0]
    if len(seeds) > 1:
        print(
            "warning: multiple secrets in image; using the first for qr-vault.yaml.",
            file=sys.stderr,
        )
    vault_file = vault_path_for_put(png_path)
    try:
        merge_qr_vault_yaml(
            vault_file,
            cluster_name,
            username_val,
            vault_labels,
            seed_for_vault,
            password,
        )
    except VaultUpdateError as e:
        print(str(e), file=sys.stderr)
        if e.hints:
            print(e.hints, file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def run_read_png(png_arg: Path | None) -> None:
    """Print MFA seeds from PNG QR only (no vault)."""
    try:
        png_path = resolve_png_path(png_arg)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if not png_path.is_file():
        print(f"error: not a file: {png_path}", file=sys.stderr)
        sys.exit(1)
    try:
        seeds = extract_seeds_from_png(png_path)
    except ImportError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if not seeds:
        print("error: no otpauth://totp or otpauth://hotp QR with secret= found", file=sys.stderr)
        sys.exit(1)
    for s in seeds:
        print(s)


_COMMANDS = frozenset({"put", "get", "read", "random"})


# Implicit ``put`` dispatch only; ``get`` also uses ``-l`` but must not imply ``put``.
_PUT_IMPLICIT_FLAGS = frozenset({"-f", "--file", "-p", "--password"})


def _argv_has_put_implicit_flags(argv: list[str]) -> bool:
    return any(tok in _PUT_IMPLICIT_FLAGS for tok in argv)


def looks_like_implicit_put(argv: list[str]) -> bool:
    """``cotp <key> <username>`` with ``-f`` or ``-p`` → ``put`` (``-f`` omitted = metadata-only)."""
    if not argv:
        return False
    first = argv[0]
    if first in _COMMANDS or first.startswith("-"):
        return False
    if len(argv) < 2 or argv[1].startswith("-"):
        return False
    if "-t" in argv or "--totp-clipboard" in argv:
        return False
    return _argv_has_put_implicit_flags(argv)


def argv_for_dispatch(argv: list[str] | None) -> list[str]:
    """No args → help; implicit ``put`` when ``<key> <username>`` + put flags; else implicit ``get``."""
    if argv is None:
        argv = sys.argv[1:]
    else:
        argv = list(argv)
    if not argv:
        return ["-h"]
    first = argv[0]
    if first in _COMMANDS:
        return argv
    if first.startswith("-"):
        if any(
            t in argv
            for t in ("-l", "--labels", "-u", "--user", "-t", "--totp-clipboard", "-w", "--wide")
        ):
            return ["get", *argv]
        return argv
    if looks_like_implicit_put(argv):
        return ["put", *argv]
    return ["get", *argv]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cotp",
        description="cotp: put (vault from QR), get (TOTP from vault), read (seed from QR), random (password).",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p_put = sub.add_parser(
        "put",
        help="Decode QR PNG and merge into the configured vault (vault_path or default config dir).",
    )
    p_put.add_argument(
        "cluster",
        nargs="?",
        default=None,
        metavar="KEY",
        help="vault top-level key (used with username; not stored as a label)",
    )
    p_put.add_argument(
        "username",
        nargs="?",
        default=None,
        help="vault username (requires KEY when set; not stored as a label)",
    )
    p_put.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="PNG with QR code (omit to update vault metadata only; requires KEY and username).",
    )
    p_put.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="",
        default=None,
        metavar="PWD",
        help=(
            "Vault password (standard Base64). Omit flag to keep existing; "
            "-p alone prompts twice and stores Base64 of the verified plain text."
        ),
    )
    p_put.add_argument(
        "-l",
        "--labels",
        default=None,
        metavar="LABELS",
        help="Comma-separated labels to store (key and username are not added as labels).",
    )

    p_get = sub.add_parser(
        "get",
        help="Print TOTP; copy Base64-decoded password to clipboard; -t also copies TOTP.",
    )
    p_get.add_argument(
        "cluster",
        nargs="?",
        default=None,
        metavar="KEY",
        help="optional vault top-level key (supports '*' wildcard; quote it in the shell)",
    )
    p_get.add_argument(
        "username",
        nargs="?",
        default=None,
        help="optional username (supports '*' wildcard)",
    )
    p_get.add_argument(
        "-u",
        "--user",
        default=None,
        metavar="USERNAME",
        help="Match this username across all keys (no KEY needed); prints every match. '*' wildcard ok.",
    )
    p_get.add_argument(
        "-l",
        "--labels",
        default=None,
        metavar="LABELS",
        help="Comma-separated labels (with KEY+username: exact set; else vault must include all). '*' wildcard ok.",
    )
    p_get.add_argument(
        "-t",
        "--totp-clipboard",
        action="store_true",
        dest="totp_clipboard",
        help="Also copy the TOTP code to the clipboard (after decoded password).",
    )
    p_get.add_argument(
        "-w",
        "--wide",
        action="store_true",
        help="Multi-line aligned output (Timestamp/Key/Username/…); default is one line.",
    )

    p_read = sub.add_parser(
        "read",
        help="Print otpauth seed(s) from a QR PNG (stdout only, no vault).",
    )
    p_read.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="PNG path (default: newest .png under configured qr_image_dir or ~/Downloads/Screenshots).",
    )

    sub.add_parser(
        "random",
        help="Print random 12-char password: plain then standard Base64 of UTF-8 bytes.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv_for_dispatch(argv))

    if args.command == "put":
        if (args.cluster is None) != (args.username is None):
            parser.error("put: KEY and username must be given together")
        run_save_from_png(
            args.file,
            resolve_put_password(args.password),
            cluster=args.cluster,
            username=args.username,
            labels_csv=args.labels,
        )
    elif args.command == "get":
        if args.user is not None and args.username is not None:
            parser.error("get: give username either positionally (with KEY) or with -u, not both")
        username = args.user if args.user is not None else args.username
        if args.cluster is None and username is None and args.labels is None:
            parser.error("get: KEY, username (-u), and/or --labels required")
        strict_labels = args.labels is not None
        get_labels: list[str] | None = None
        if strict_labels:
            get_labels = query_labels_for_get(args.labels)
        run_query(
            args.cluster,
            username,
            get_labels,
            strict_labels=strict_labels,
            totp_to_clipboard=args.totp_clipboard,
            wide_output=args.wide,
        )
    elif args.command == "read":
        run_read_png(args.file)
    elif args.command == "random":
        print(format_random_password_line(random_password_12()))
    else:  # pragma: no cover
        parser.error(f"unknown command: {args.command!r}")


if __name__ == "__main__":
    main()
