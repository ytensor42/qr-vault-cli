# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Repository:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — install from **GitHub source** (see below). CLI command: **`cotp`**.

**cotp** is a short CLI for working with `qr-vault.yaml`, PNG QR codes, TOTP, and random passwords.

(Korean: [README-ko.md](README-ko.md))

## Requirements

- **Python 3.11+**
- **zbar** (for pyzbar): macOS `brew install zbar` · Debian/Ubuntu `sudo apt install libzbar0`
- **git** (for clone / `pip install` from GitHub)

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

After install, run **`cotp`** (or `python -m cotp_cli` inside the install venv).

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

- stdout default (one line): `HH:MM:SS key/username [otp] [labels]` (labels comma-separated; OTP omitted if no seed).
- **`-w`**: multi-line aligned output (`Timestamp:`, `Key:`, `Username:`, …).
- The vault entry **`password`** is assumed to be **Base64 (UTF-8)**; the decoded **plaintext is copied to the clipboard**. With **`-t`**, only the **TOTP code** is copied (password is not copied).
- On success, **stderr** prints `password is copied to clipboard` and/or `totp value is copied to clipboard` so you know what was copied.

```bash
cotp get tp00
cotp get tp00 alice
cotp get tp00 alice -l admin,prod
cotp tp00 admin -l test
cotp get tp00 alice -t
cotp get tp00 admin -w
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

Install from the **GitHub repository** (not PyPI). Push your latest changes to GitHub before installing on another machine.

### 1. Prerequisites (run once per machine)

```bash
brew install zbar git
python3 --version   # must be 3.11 or newer
```

If Python is older than 3.11: `brew install python@3.12` and ensure `python3` points at it.

### 2. Recommended: `install.sh` (puts `cotp` in `~/bin`)

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
./install.sh
```

The script will:

1. Create a fresh **private venv** at **`~/.cotp/venv`** and install **`cotp-cli` from GitHub** (`main` branch).
2. Create **`~/.config/cotp/config.yaml`** if missing (default `vault_path` and `qr_image_dir`).
3. Install **`~/bin/cotp`** (wrapper → venv Python + `COTP_CONFIG`).
4. Optionally **delete** the clone folder when finished (see script output).

**Unpublished changes on this Mac only** (install from the working tree, not GitHub):

```bash
COTP_INSTALL_LOCAL=1 ./install.sh
```

**Broken venv (`File name too long`):** `rm -rf ~/.cotp ~/.local/share/cotp`, then run `./install.sh` again.

In a **git clone**, file cleanup is skipped by default. Use `./install.sh --cleanup` to remove the clone after install. Install elsewhere: `INSTALL_BINDIR=/usr/local/bin ./install.sh`.

Ensure `~/bin` is on your `PATH`, then `cotp --help`.

### 3. Manual: `pip install` from GitHub

```bash
python3 -m venv ~/.cotp/venv
~/.cotp/venv/bin/pip install -U pip wheel
~/.cotp/venv/bin/pip install "cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git"
```

Add a `~/bin/cotp` wrapper that runs `~/.cotp/venv/bin/python -m cotp_cli "$@"` and set `COTP_CONFIG=~/.config/cotp/config.yaml` (see `install.sh`).

### 4. Configuration

`install.sh` creates **`~/.config/cotp/config.yaml`** when missing; the installed **`cotp`** command sets **`COTP_CONFIG`** to that path by default.

| Defaults written by `install.sh` | |
|----------------------------------|--|
| **`vault_path`** | `~/.config/cotp/qr-vault.yaml` |
| **`qr_image_dir`** | `~/Downloads/Screenshots` |

When **`vault_path`** is set, **`put`** always merges into that file (not beside the PNG).

### 5. Copy your vault

Copy **`qr-vault.yaml`** (or the path in `vault_path`) from the old Mac to the new one.

```bash
chmod 600 ~/.config/cotp/qr-vault.yaml
```

### 6. Verify

```bash
ls -la ~/bin/cotp ~/.cotp/venv/bin/python
cotp --help
cotp get tp00 admin          # or: cotp -l your-label
```

If **`~/bin/cotp` is missing**, the install did not finish. You should see `cotp install: install complete:` and `cotp command: /Users/you/bin/cotp`. Retry:

```bash
rm -rf ~/.cotp ~/.local/share/cotp
git pull
./install.sh --no-cleanup
find "$HOME" -name cotp -type f 2>/dev/null   # in case INSTALL_BINDIR was overridden
```

---

## Development

Clone the repo and use an editable install (same tree you are hacking on):

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
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
