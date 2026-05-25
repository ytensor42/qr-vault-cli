# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cotp-cli)](https://pypi.org/project/cotp-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Open-source repository:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — distributed on PyPI as [**cotp-cli**](https://pypi.org/project/cotp-cli/) with the **`cotp`** command.

**cotp** is a short CLI for working with `qr-vault.yaml`, PNG QR codes, TOTP, and random passwords.

(Korean: [README-ko.md](README-ko.md))

## Requirements

- **Python 3.11+**
- **zbar** (for pyzbar): macOS `brew install zbar` · Debian/Ubuntu `sudo apt install libzbar0`

## Configuration

Optional YAML (see repository [`config.example.yaml`](config.example.yaml)):

| Location | |
|----------|--|
| Default | `~/.config/cotp/config.yaml`, or `$XDG_CONFIG_HOME/cotp/config.yaml` when `XDG_CONFIG_HOME` is set |
| Override | Set environment variable **`COTP_CONFIG`** to the file path |

| Key | Meaning |
|-----|---------|
| `vault_path` | Path to `qr-vault.yaml`. Used by **`get`**. If set, **`put`** merges into this file instead of creating/updating `qr-vault.yaml` next to the PNG. |
| `qr_image_dir` | Default directory for **`put`** / **`read`** when `-f` is omitted (newest `.png` there), and the base for relative `-f` paths. If omitted, defaults to `~/Downloads/Screenshots`. |

## Commands

Package name on PyPI: **`cotp-cli`** (`pip install cotp-cli` or locally `pip install -e .`). Console script: **`cotp`**. Module entry: `python -m cotp_cli …`.

### `cotp put` — read QR, print seed, update the vault

Vault **`labels`** always include the **cluster key** and **username**; extra labels come from a `QR-<key>-<user>-<label>…` filename when present. **Updates** only when exactly **one** existing entry matches the same key, username, and label set (no overwrite on mismatch or ambiguity).

```bash
cotp put
cotp put -f QR-tp00-alice-admin.png
cotp put tp00 alice -f /path/to/qr.png      # read seed from QR PNG
cotp put tp00 admin -l test                 # no -f: metadata-only (labels/password; keep seed)
cotp put tp00 admin -p                      # -p only: prompt twice, store Base64 (Ctrl+C aborts)
cotp put tp00 admin -p 'Base64-string'      # store password field as given (for get clipboard)
cotp put tp00 admin -l test -f qr.png
cotp tp00 admin -p                          # implicit put (-f or -p; else get)
```

### `cotp get` — TOTP from vault + password to clipboard

If the first token is not `put`, `get`, `read`, or `random`, and it does not start with `-`, it is treated as **`get` with that argument list**. For example, `cotp tp00 alice` is the same as `cotp get tp00 alice`. With **no arguments**, `cotp` prints help (same as `cotp -h`).

- stdout (multi-line): `Timestamp:`, `Key:`, `Username:`, `OTP:` (only when a seed exists), `Labels:` (comma-separated).
- The vault entry **`password`** is assumed to be **Base64 (UTF-8)**; the decoded **plaintext is copied to the clipboard**. With **`-t`**, only the **TOTP code** is copied (password is not copied).
- On success, **stderr** prints `password is copied to clipboard` and/or `totp value is copied to clipboard` so you know what was copied.

```bash
cotp get tp00
cotp get tp00 alice
cotp get tp00 alice -l admin,prod
cotp tp00 admin -l test
cotp get tp00 alice -t
```

- macOS: `pbcopy` · Linux: one of `wl-copy` / `xclip` / `xsel`.

### `cotp read` — print seed from a PNG QR only (no vault)

```bash
cotp read
cotp read -f ~/Downloads/Screenshots/cap.png
```

### `cotp random` — 12-character random password (plain + Base64)

One line: **`<plain> <base64>`** — 12-character plain text, then standard Base64 of the UTF-8 bytes.

```bash
cotp random
```

## Install on another Mac

Use this when you move to a **new Mac** or a second machine and want the same `cotp` CLI and vault.

### 1. System dependencies

```bash
brew install zbar
python3 --version   # must be 3.11 or newer
```

Install Python 3.11+ if needed (e.g. `brew install python@3.12`).

### 2. Install `cotp` (pick one)

**Recommended — PyPI (no clone):**

```bash
pipx install cotp-cli
# or: python3 -m pip install --user cotp-cli
cotp --help
```

If `cotp` is not found, add `~/.local/bin` (pip `--user`) or ensure pipx’s bin directory is on your `PATH`.

**From GitHub (latest `main`):**

```bash
pipx install "cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git"
```

**From a local clone** (your checkout, including unpublished changes):

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
python3 -m pip install --user -e .
# or use a venv in the repo:
# python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

### 3. Configuration (optional)

```bash
mkdir -p ~/.config/cotp
cp config.example.yaml ~/.config/cotp/config.yaml
```

Edit `vault_path` and `qr_image_dir` if you do not use the defaults. Or point at a custom file:

```bash
export COTP_CONFIG=~/.config/cotp/config.yaml
```

| Default (no config) | |
|---------------------|--|
| Vault file for **`get`** | `~/Downloads/Screenshots/qr-vault.yaml` |
| QR folder for **`put`** / **`read`** without `-f` | `~/Downloads/Screenshots` |

When **`vault_path`** is set, **`put`** always merges into that file (not beside the PNG).

### 4. Copy your vault

`cotp` does not sync vault data for you. Copy **`qr-vault.yaml`** (or the path in `vault_path`) from the old Mac to the new one, e.g. AirDrop, `scp`, or encrypted backup.

```bash
chmod 600 ~/path/to/qr-vault.yaml
```

Treat this file like a password manager export (seeds and Base64-encoded passwords).

### 5. Verify

```bash
cotp --help
cotp get tp00 admin          # or: cotp -l your-label
```

You should see TOTP on stdout; if the entry has a valid Base64 **`password`**, stderr reports `password is copied to clipboard` (use **`-t`** for TOTP-only clipboard).

---

## Development

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

## Community

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- Licensed under the [MIT License](LICENSE).

See also [`AGENTS.md`](AGENTS.md) (maintainer & agent context).
