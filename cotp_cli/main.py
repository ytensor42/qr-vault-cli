"""cotp: QR PNG seed extraction, vault (qr-vault.yaml), TOTP get, random password."""

from __future__ import annotations

import argparse
import base64
import binascii
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from PIL import Image

from cotp_cli.config import load_cotp_settings, vault_path_for_put

_RANDOM_PASSWORD_LENGTH = 12
_RANDOM_SPECIAL = "!@#$%^&*-_=+"


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


def format_random_password_line(plain: str) -> str:
    """``<plain> <base64>`` for stdout (UTF-8 bytes encoded with standard Base64)."""
    b64 = base64.standard_b64encode(plain.encode("utf-8")).decode("ascii")
    return f"{plain} {b64}"


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


def parse_qr_filename(path: Path) -> tuple[str, str, list[str]] | None:
    """Parse ``QR-<cluster>-<username>-<label1>-....png`` → (cluster, username, [labels...])."""
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
    return parts[0], parts[1], list(parts[2:])


def merge_qr_vault_yaml(
    vault_path: Path,
    cluster_name: str,
    username: str,
    labels: list[str],
    seed: str,
    password: str | None,
) -> None:
    """Load or create ``qr-vault.yaml``; set cluster entry; preserve other top-level keys."""
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

    prev = data.get(cluster_name)
    prev_pwd = ""
    if isinstance(prev, dict):
        raw_p = prev.get("password", "")
        prev_pwd = raw_p if isinstance(raw_p, str) else ""

    pwd_out = password if password is not None else prev_pwd

    data[cluster_name] = {
        "seed": seed,
        "username": username,
        "password": pwd_out,
        "labels": list(labels),
    }
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    vault_path.write_text(text, encoding="utf-8")


def default_vault_path() -> Path:
    s = load_cotp_settings()
    if s.vault_path is not None:
        return s.vault_path
    return default_qr_dir() / "qr-vault.yaml"


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


def seed_for_cluster_name_only(data: dict, cluster_name: str) -> str:
    """Resolve seed for a cluster key; requires a usable username (first if list)."""
    entry = data.get(cluster_name)
    if not isinstance(entry, dict):
        raise KeyError(f"no vault entry for cluster {cluster_name!r}")
    first_username_from_entry(entry)
    return _seed_from_entry(entry)


def seed_for_cluster_username_any_labels(data: dict, cluster_name: str, username: str) -> str:
    entry = data.get(cluster_name)
    if not isinstance(entry, dict):
        raise KeyError(f"no vault entry for cluster {cluster_name!r}")
    vault_user = first_username_from_entry(entry)
    if vault_user != username.strip():
        raise ValueError(
            "username mismatch: vault has "
            f"{vault_user!r} (first if list), expected {username!r}"
        )
    return _seed_from_entry(entry)


def seed_for_cluster_user_labels(
    data: dict,
    cluster_name: str,
    username: str,
    labels: list[str],
) -> str:
    entry = data.get(cluster_name)
    if not isinstance(entry, dict):
        raise KeyError(f"no vault entry for cluster {cluster_name!r}")
    vault_user = first_username_from_entry(entry)
    if vault_user != username.strip():
        raise ValueError(
            "username mismatch: vault has "
            f"{vault_user!r} (first if list), expected {username!r}"
        )
    raw_labels = entry.get("labels") or []
    if not isinstance(raw_labels, list):
        raise ValueError("entry labels must be a YAML list")
    vault_labels = [str(x).strip() for x in raw_labels]
    want = [str(x).strip() for x in labels]
    if sorted(vault_labels) != sorted(want):
        raise ValueError(
            f"labels mismatch: vault has {vault_labels!r}, expected (same multiset) {want!r}"
        )
    return _seed_from_entry(entry)


def totp_parts(seed: str) -> tuple[str, str]:
    import pyotp  # noqa: PLC0415

    clock = datetime.now().strftime("%H:%M:%S")
    code = pyotp.TOTP(seed).now()
    return clock, code


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


def resolve_vault_query(
    data: dict,
    cluster: str,
    username: str | None,
    labels_csv: str | None,
) -> tuple[str, dict]:
    if username is None and labels_csv is None:
        seed = seed_for_cluster_name_only(data, cluster)
    elif username is not None and labels_csv is None:
        seed = seed_for_cluster_username_any_labels(data, cluster, username)
    else:
        seed = seed_for_cluster_user_labels(
            data, cluster, username, labels_from_csv(labels_csv or "")
        )
    entry = data.get(cluster)
    if not isinstance(entry, dict):
        raise RuntimeError("internal: vault entry missing after match")
    return seed, entry


def run_query(
    cluster: str,
    username: str | None,
    labels_csv: str | None,
    *,
    totp_to_clipboard: bool = False,
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
        seed, entry = resolve_vault_query(data, cluster, username, labels_csv)
    except (KeyError, ValueError):
        print(NO_MATCH_LINE)
        return

    clock, code = totp_parts(seed)
    show_user = username.strip() if username is not None else first_username_from_entry(entry)
    print(f"{clock} {show_user} {code}")

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

    if totp_to_clipboard:
        try:
            copy_text_to_clipboard(code)
        except OSError as e:
            print(f"warning: could not copy TOTP to clipboard: {e}", file=sys.stderr)
        else:
            print("totp value is copied to clipboard", file=sys.stderr)


def run_save_from_png(png_arg: Path | None, password: str | None) -> None:
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
    if parsed is None:
        print(
            "warning: filename is not QR-<cluster>-<username>-<label1>-...-<labeln>.png; "
            "skipping qr-vault.yaml.",
            file=sys.stderr,
        )
        return
    cluster_name, username, extra_labels = parsed
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
            username,
            extra_labels,
            seed_for_vault,
            password,
        )
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


def argv_for_dispatch(argv: list[str] | None) -> list[str]:
    """If the first token is not a subcommand and not a global flag, prepend ``get``."""
    if argv is None:
        argv = sys.argv[1:]
    else:
        argv = list(argv)
    if not argv:
        return ["get"]
    first = argv[0]
    if first in _COMMANDS:
        return argv
    if first.startswith("-"):
        return argv
    return ["get", *argv]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cotp",
        description="cotp: put (vault from QR), get (TOTP from vault), read (seed from QR), random (password).",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p_put = sub.add_parser(
        "put",
        help="Decode QR PNG and merge into the vault (beside the PNG, or vault_path in config).",
    )
    p_put.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="PNG path (default: newest .png under configured qr_image_dir or ~/Downloads/Screenshots).",
    )
    p_put.add_argument(
        "-p",
        "--password",
        default=None,
        metavar="PWD",
        help="Password in vault entry (omit on update to keep existing).",
    )

    p_get = sub.add_parser(
        "get",
        help="Print TOTP; copy Base64-decoded password to clipboard; -t also copies TOTP.",
    )
    p_get.add_argument("cluster", help="cluster_name (YAML top-level key)")
    p_get.add_argument("username", nargs="?", default=None, help="optional username")
    p_get.add_argument(
        "labels_csv",
        nargs="?",
        default=None,
        help="optional comma-separated labels (use '' for none, requires username)",
    )
    p_get.add_argument(
        "-t",
        "--totp-clipboard",
        action="store_true",
        dest="totp_clipboard",
        help="Also copy the TOTP code to the clipboard (after decoded password).",
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
        run_save_from_png(args.file, args.password)
    elif args.command == "get":
        if args.labels_csv is not None and args.username is None:
            parser.error("get: username is required when labels_csv is given")
        run_query(
            args.cluster,
            args.username,
            args.labels_csv,
            totp_to_clipboard=args.totp_clipboard,
        )
    elif args.command == "read":
        run_read_png(args.file)
    elif args.command == "random":
        print(format_random_password_line(random_password_12()))
    else:  # pragma: no cover
        parser.error(f"unknown command: {args.command!r}")


if __name__ == "__main__":
    main()
