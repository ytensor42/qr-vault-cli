# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.9] — 2026-07-11

### Added

- **cotp fill** browser extension: **Firefox** support (Chrome + Firefox, Manifest V3); shared `browser.js` API shim.
- `browser-extension/` directory (renamed from `chrome-extension/`).

### Changed

- Extension docs and main README (EN/KO) updated for `browser-extension/`, Firefox install, and current `cotp-web` behaviour.

## [0.7.8] — 2026-07-11

### Changed

- `cotp-web`: `-t` treats a bare number as **minutes** (e.g. `-t 60` = 1 hour).
- `cotp-web`: foreground mode shows **FG** (blue); timed mode shows a blue countdown and **Expired** (red) at zero.
- `cotp-web`: username button uses light yellow background and matching border.
- `cotp-web`: click feedback inverts button colors only (no whole-row flash).
- `cotp-web`: row hover highlight is light blue instead of yellow.

## [0.7.7] — 2026-07-11

### Added

- `cotp-web`: favicon (`favicon-32.png`; `/favicon.ico` for Safari).
- `cotp-web`: `-t` / `--time` for background runtime (`1h`, `30m`, `1h30m`, …).
- `cotp-web`: remaining runtime countdown (`HH:MM:SS`) on the page when running with a time limit.

### Changed

- `cotp-web`: default launch stops any background server and runs in the **foreground** (no y/N prompt).
- `cotp-web`: Pwd button readable in dark theme (light red background, white text).
- `cotp-web`: second and countdown shown at left / right of the status bar.

## [0.7.6] — 2026-07-10

### Added

- **cotp fill** browser extension (`browser-extension/`): pick an entry in the popup to fill username, password, and OTP on the active tab (Teleport and generic login forms).

### Changed

- `cotp-web`: entry list uses a table layout (account / username / Pwd / OTP columns aligned); no column header row; narrower page width.
- `cotp-web`: username button padding no longer overridden by Pwd/OTP button styles.

## [0.7.5] — 2026-07-10

### Changed

- CI: upgrade `actions/checkout` to v5 and `actions/setup-python` to v6 (Node.js 24 on GitHub Actions).

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

[Unreleased]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.9...HEAD
[0.7.9]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.8...v0.7.9
[0.7.8]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.7...v0.7.8
[0.7.7]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.6...v0.7.7
[0.7.6]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.5...v0.7.6
[0.7.5]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/ytensor42/qr-vault-cli/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.9...v0.7.0
[0.6.9]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.8...v0.6.9
[0.6.8]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.7...v0.6.8
[0.6.7]: https://github.com/ytensor42/qr-vault-cli/commits/v0.6.7
