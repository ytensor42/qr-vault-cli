"""Parse ``h`` / ``m`` duration strings for cotp-web background runtime."""

from __future__ import annotations

import re

_DURATION_RE = re.compile(r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?$", re.IGNORECASE)
_PLAIN_MINUTES_RE = re.compile(r"^\d+$")


def parse_duration(value: str) -> int:
    """Parse ``30``, ``30m``, ``1h``, or ``1h30m`` into total seconds.

    A bare number is treated as minutes (default unit).
    """
    text = value.strip().lower().replace(" ", "")
    if _PLAIN_MINUTES_RE.fullmatch(text):
        minutes = int(text)
        if minutes <= 0:
            raise ValueError(f"invalid duration: {value!r} (must be greater than zero)")
        return minutes * 60
    match = _DURATION_RE.fullmatch(text)
    if not match:
        msg = f"invalid duration: {value!r} (use forms like 30, 30m, 1h, 1h30m)"
        raise ValueError(msg)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    if hours == 0 and minutes == 0:
        msg = f"invalid duration: {value!r} (must include at least one of h or m)"
        raise ValueError(msg)
    total = hours * 3600 + minutes * 60
    if total <= 0:
        raise ValueError(f"invalid duration: {value!r} (must be greater than zero)")
    return total
