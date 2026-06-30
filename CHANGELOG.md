# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `get -u/--user USERNAME`: match a username across all keys (no KEY required) and print every matching entry. Cannot be combined with the positional username; `cotp -u …` is treated as an implicit `get`.
- `get` wildcard search: the KEY, username (positional or `-u`), and `-l` labels accept `*` (any run of characters; other characters literal and case-sensitive). Applies to `get` only — `put` still matches/writes literally.
- `cotp -v` / `cotp --version`: print the installed package version.

### Changed

- Vault `labels` no longer include the cluster key or username automatically; only the labels you pass with `-l`/`--labels` are stored. `get` label matching (`-l`) likewise compares only those labels.
- `put -f`: PNG filename suffixes after `QR-<key>-<user>-` are no longer stored as labels (key/username from filename when omitted on the CLI is unchanged).

### Added

- Open source repository layout (`LICENSE`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, GitHub Actions CI, issue templates).

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

[Unreleased]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.9...HEAD
[0.6.9]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.8...v0.6.9
[0.6.8]: https://github.com/ytensor42/qr-vault-cli/compare/v0.6.7...v0.6.8
[0.6.7]: https://github.com/ytensor42/qr-vault-cli/commits/v0.6.7
