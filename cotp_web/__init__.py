"""Local web UI to copy vault passwords and TOTP codes to the clipboard."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__", "package_version"]

__version__ = "0.1.0"


def package_version() -> str:
    try:
        return version("cotp-cli")
    except PackageNotFoundError:
        return __version__
