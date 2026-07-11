# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.4] — 2026-07-10

### Fixed

- `cotp-web`: username cell colors readable in OS dark theme (`light-dark` text, background, border, row hover).

## [0.7.3] — 2026-07-10

### Changed

- `cotp-web`: split entry rows into **account** and **username** columns; click username to copy (User button removed).
- `cotp-web`: Pwd/OTP button colors; OTP buttons fade green→white (50–59s) while the second display stays green→red.
- `cotp-web`: username cell uses blue border and black text; stays white when the row is hovered.

## [0.7.2] — 2026-07-10

### Added

- `cotp-web`: stop an existing background server before starting a new one (`~/.cotp/cotp-web.pid`).

### Changed

- `cotp-web`: second display uses green (0–49s) and a green→red gradient (50–59s).
- `install.sh`: print installed version on verify; force-reinstall on upgrade (avoid stale pip/git cache).

## [0.7.1] — 2026-07-10

### Added

- `cotp-web`: **User** button copies the vault username to the clipboard.

## [0.7.0] — 2026-07-10

### Added

- `cotp-web`: local web UI (`127.0.0.1`) to copy vault passwords and TOTP from an entry YAML file.
- Disclaimer in README (EN/KO) and on the `cotp-web` page.
- `get -u/--user USERNAME`: match a username across all keys (no KEY required) and print every matching entry. Cannot be combined with the positional username; `cotp -u …` is treated as an implicit `get`.
- `get` wildcard search: the KEY, username (positional or `-u`), and `-l` labels accept `*` (any run of characters; other characters literal and case-sensitive). Applies to `get` only — `put` still matches/writes literally.
- `cotp -v` / `cotp --version`: print the installed package version.
- Open source repository layout (`LICENSE`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, GitHub Actions CI, issue templates).

### Changed

- Vault `labels` no longer include the cluster key or username automatically; only the labels you pass with `-l`/`--labels` are stored. `get` label matching (`-l`) likewise compares only those labels.
- `put -f`: PNG filename suffixes after `QR-<key>-<user>-` are no longer stored as labels (key/username from filename when omitted on the CLI is unchanged).

## [0.6.9] — 2026-05-15

### Added

- `get`: stderr notices when password and/or TOTP are copied to the clipboard successfully.

## [0.6.8] — 2026-05-15

### Changed

- `get` stdout format: `HH:MM:SS <username> <totp>`.

## [0.6.7] — 2026-05-15

### Added

- Optional config file: `vault_path`, `qr_image_dir` (`cotp_cli.config`; `COTP_CONFIG` / XDG paths).

---

Earlier history: see git log and PyPI release notes.

[Unreleased]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.4...HEAD
[0.7.4]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.9...v0.7.0
[0.6.9]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.8...v0.6.9
[0.6.8]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.7...v0.6.8
[0.6.7]: https://github.com/ytensor42/qr-vault-cli/commits/v0.6.7
