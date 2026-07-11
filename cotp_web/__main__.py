"""``python -m cotp_web`` — local web UI for vault clipboard copy."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from cotp_cli.main import default_vault_path

from cotp_web.duration import parse_duration
from cotp_web.process import register_background_pid, stop_existing_background
from cotp_web.server import format_serving_message, run_server
from cotp_web.vault import resolve_entries_path


def _duration_type(value: str) -> int:
    try:
        return parse_duration(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _stop_existing_if_any() -> int | None:
    stopped = stop_existing_background()
    if stopped is not None:
        print(f"stopped existing cotp-web (pid {stopped})", file=sys.stderr)
    return stopped


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
    _stop_existing_if_any()
    return subprocess.Popen(
        [sys.executable, "-m", "cotp_web", *child_argv],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_foreground(
    args: argparse.Namespace,
    *,
    vault_path: Path,
    entries_path: Path,
    max_runtime: int | None,
) -> None:
    if max_runtime is not None and max_runtime > 0:
        register_background_pid()
    run_server(
        vault_path=vault_path,
        entries_path=entries_path,
        host=args.host,
        port=args.port,
        max_runtime=max_runtime,
        started_at=time.time(),
        interactive=not args.foreground,
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
    parser.add_argument(
        "-t",
        "--time",
        dest="time_limit",
        metavar="DURATION",
        type=_duration_type,
        help="Background runtime in minutes by default (e.g. 60, 90m, 1h, 1h30m).",
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

    if args.foreground:
        _run_foreground(args, vault_path=vault_path, entries_path=entries_path, max_runtime=args.max_runtime)
        return 0

    if args.time_limit is not None:
        _spawn_background(_child_argv(args, args.time_limit))
        print(format_serving_message(args.host, args.port))
        return 0

    _stop_existing_if_any()
    _run_foreground(args, vault_path=vault_path, entries_path=entries_path, max_runtime=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
