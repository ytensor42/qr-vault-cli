"""``python -m cotp_web`` — local web UI for vault clipboard copy."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cotp_cli.main import default_vault_path

from cotp_web.server import format_serving_message, run_server
from cotp_web.vault import resolve_entries_path

DEFAULT_BACKGROUND_SECONDS = 3600


def _ask_background() -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input("Run in background for 1 hour? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return False
    return answer in ("y", "yes")


def _child_argv(args: argparse.Namespace, max_runtime: int) -> list[str]:
    child = [
        args.entries,
        "--foreground",
        "--max-runtime",
        str(max_runtime),
    ]
    if args.vault is not None:
        child.extend(["--vault", str(args.vault)])
    if args.host != "127.0.0.1":
        child.extend(["--host", args.host])
    if args.port != 8765:
        child.extend(["--port", str(args.port)])
    return child


def _spawn_background(child_argv: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-m", "cotp_web", *child_argv],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local web UI: copy vault password or OTP to the clipboard.",
    )
    parser.add_argument(
        "entries",
        help=(
            "Entry list YAML (vault key → list of username entries). "
            "Bare filename → vault directory; otherwise OS path, then vault directory."
        ),
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="qr-vault.yaml path (default: cotp config vault_path).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="TCP port (default: 8765).",
    )
    parser.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--max-runtime", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    vault_path = (args.vault or default_vault_path()).expanduser()
    if not vault_path.is_file():
        print(f"error: vault file not found: {vault_path}", file=sys.stderr)
        return 1

    entries_path = resolve_entries_path(
        Path(args.entries),
        vault_path,
        entries_raw=args.entries,
    )
    if not entries_path.is_file():
        print(f"error: entries file not found: {entries_path}", file=sys.stderr)
        return 1

    if not args.foreground and _ask_background():
        _spawn_background(_child_argv(args, DEFAULT_BACKGROUND_SECONDS))
        print(format_serving_message(args.host, args.port))
        return 0

    run_server(
        vault_path=vault_path,
        entries_path=entries_path,
        host=args.host,
        port=args.port,
        max_runtime=args.max_runtime,
        interactive=not args.foreground,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
