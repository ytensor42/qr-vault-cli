"""Background cotp-web process tracking via a PID file."""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import time
from pathlib import Path

PID_DIR = Path.home() / ".cotp"
PID_FILE = PID_DIR / "cotp-web.pid"

_TERMINATE_TIMEOUT_SEC = 3.0


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def _command_for_pid(pid: int) -> str | None:
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    text = out.strip()
    return text or None


def is_cotp_web_process(pid: int) -> bool:
    command = _command_for_pid(pid)
    if command is None:
        return False
    return "cotp_web" in command


def read_background_pid() -> int | None:
    try:
        text = PID_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    try:
        return int(text.split()[0])
    except ValueError:
        return None


def remove_pid_file() -> None:
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _terminate_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + _TERMINATE_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if not _process_alive(pid):
            return
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def stop_existing_background() -> int | None:
    """Stop a prior background cotp-web if its PID file points at a live process."""
    pid = read_background_pid()
    if pid is None:
        return None
    if not _process_alive(pid):
        remove_pid_file()
        return None
    if not is_cotp_web_process(pid):
        remove_pid_file()
        return None
    _terminate_pid(pid)
    remove_pid_file()
    return pid


def _cleanup_registered_pid(pid: int) -> None:
    if read_background_pid() == pid:
        remove_pid_file()


def register_background_pid(pid: int | None = None) -> None:
    """Record the background server PID and remove the file on exit."""
    current = pid if pid is not None else os.getpid()
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(f"{current}\n", encoding="utf-8")
    atexit.register(_cleanup_registered_pid, current)
