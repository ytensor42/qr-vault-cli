# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Repository:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — install from **GitHub source** (see below). Commands: **`cotp`** (CLI) and **`cotp-web`** (local web UI).

**cotp** is a short CLI for working with `qr-vault.yaml`, PNG QR codes, TOTP, and random passwords. **`cotp-web`** is a minimal localhost web UI to copy vault passwords and OTP codes to the clipboard.

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
| `vault_path` | Path to `qr-vault.yaml`. Used by **`get`**, **`put`**, and **`cotp-web`**. If omitted, defaults to `~/.config/cotp/qr-vault.yaml` (or `$XDG_CONFIG_HOME/cotp/qr-vault.yaml`). |
| `qr_image_dir` | Default directory for **`put`** / **`read`** when `-f` is omitted (newest `.png` there), and the base for relative `-f` paths. If omitted, defaults to `~/Downloads/Screenshots`. |

## Commands

After install, run **`cotp`** (or `python -m cotp_cli` inside the install venv).

### `cotp put` — read QR, print seed, update the vault

Vault **`labels`** store only the labels you pass with **`-l` / `--labels`** (the **cluster key** and **username** are **not** added as labels; PNG filename suffixes are not used as labels). **Updates** only when exactly **one** existing entry matches the same key, username, and label set (no overwrite on mismatch or ambiguity).

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

**`-u` / `--user`** matches a username across **all** keys (no KEY needed) and prints **every** matching entry, one line each. It cannot be combined with the positional `username`.

**Wildcards:** the KEY, the username (positional or `-u`), and each `-l` label support `*` as "any run of characters" (everything else is literal, case-sensitive). Quote patterns in the shell so `*` is not expanded, e.g. `cotp 'tc*'`, `cotp -u 'admin*'`, `cotp tc00 -l 'prod*'`. Wildcards apply to `get` searches only; `put` always writes/matches literally.

> **Heads up (zsh/bash):** an unquoted `cotp git*` is expanded by the shell first. In zsh, when nothing matches you get `zsh: no matches found: git*` and cotp never runs. Quote the pattern (`cotp 'git*'`), escape it (`cotp git\*`), or run it through `noglob` (`noglob cotp git*`). To skip quoting every time, add an alias to your shell rc:
>
> ```bash
> alias cotp='noglob cotp'
> ```
>
> (Aliases apply to interactive shells only; prefer quoting inside scripts.)

- stdout default (one line): `HH:MM:SS key/username [otp] [labels]` (labels comma-separated; OTP omitted if no seed). When the clipboard is used (single match only), the line marks what was copied: `key/user/[**pwd**]` for password, or `key/user/pwd [**otp**]` with **`-t`**.
- **`-w`**: multi-line aligned output (`Timestamp:`, `Key:`, `Username:`, …); clipboard success messages go to **stderr** as before.
- The vault entry **`password`** is assumed to be **Base64 (UTF-8)**; the decoded **plaintext is copied to the clipboard**. With **`-t`**, only the **TOTP code** is copied (password is not copied).

```bash
cotp get tp00
cotp get tp00 alice
cotp get tp00 alice -l admin,prod
cotp tp00 admin -l test
cotp get tp00 alice -t
cotp get tp00 admin -w
cotp get -u admin          # all entries (any key) with username admin
cotp -u admin              # same (implicit get)
cotp 'tc*'                 # every key matching tc* (quote * in the shell)
cotp -u 'admin*'           # usernames starting with admin
cotp tc00 -l 'prod*'       # labels matching prod*
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

## `cotp-web` — local web UI (clipboard)

A small **localhost-only** server that lists selected vault entries and copies **password** or **TOTP** to the clipboard when you click a button. Seeds and passwords are **not** included in the HTML or the initial API response; values are fetched only when you press **Pwd** or **OTP**.

### Features

- Entry list from a YAML file (see below); vault path from **`COTP_CONFIG`** / `vault_path` (same as `cotp`).
- Page layout: `cotp-web v<version>`, current **second** (sticky header), then one row per entry with **Pwd** / **OTP** buttons.
- **OTP** button is shown only when the vault entry has a usable seed; **Pwd** stays in the same column on every row.
- Hover highlight (yellow); brief green flash on successful copy.
- Foreground: `==> 127.0.0.1:<port>  until CTRL-C` · optional background run for **1 hour** (interactive prompt).

### Entry list YAML (`cotp-web.yaml`)

Place the file next to your vault (recommended) or pass a path. Example: [`cotp_web/entries.example.yaml`](cotp_web/entries.example.yaml).

```yaml
test:
- username: admin
- username: alica
github:
- username: deepsolo
```

Top-level keys are vault **KEY**s; each list item needs **`username`**. Rows are matched as `key.username` (first `.` only).

**Path resolution:** a bare filename (e.g. `cotp-web.yaml`) is looked up in the **vault directory**. With a path prefix (`./x`, `~/x`, `dir/x`), the OS path is tried first, then the vault directory.

### Run

```bash
cotp-web cotp-web.yaml
cotp-web cotp-web.yaml --vault ~/path/to/qr-vault.yaml   # optional override
cotp-web cotp-web.yaml --port 8765
```

Open `http://127.0.0.1:8765` (default). Binds to **127.0.0.1** only.

Development: `python -m cotp_web cotp-web.yaml` from an editable install.

## Install on another Mac

Install from the **GitHub repository** (not PyPI). Push your latest changes to GitHub before installing on another machine.

### 1. Prerequisites (run once per machine)

```bash
brew install zbar git
python3 --version   # must be 3.11 or newer
```

If Python is older than 3.11: `brew install python@3.12` and ensure `python3` points at it.

### 2. Recommended: `install.sh` (puts `cotp` and `cotp-web` in `~/bin`)

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
./install.sh --preflight    # optional: check prerequisites only
./install.sh --no-cleanup   # keep clone (developers)
./install.sh --verify       # verify existing install
```

The script will:

1. Create a fresh **private venv** at **`~/.cotp/venv`** and install **`cotp-cli`** (local tree if `pyproject.toml` is present, else GitHub `main`).
2. Create **`~/.config/cotp/config.yaml`** if missing (default `vault_path` and `qr_image_dir`).
3. Install **`~/bin/cotp`** and **`~/bin/cotp-web`** (wrappers → venv Python + `COTP_CONFIG`).
4. Optionally **delete** the clone folder when finished (see script output).

**Success line:** `cotp install: === cotp is installed correctly on this machine ===`

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

Add `~/bin/cotp` and `~/bin/cotp-web` wrappers (see `install.sh`).

### 4. Configuration

`install.sh` creates **`~/.config/cotp/config.yaml`** when missing; the installed **`cotp`** command sets **`COTP_CONFIG`** to that path by default.

| Defaults written by `install.sh` | |
|----------------------------------|--|
| **`vault_path`** | `~/.config/cotp/qr-vault.yaml` |
| **`qr_image_dir`** | `~/Downloads/Screenshots` |

`put` writes to `vault_path` when set; otherwise it writes to the default config-dir vault path.

### 5. Copy your vault

Copy **`qr-vault.yaml`** (and **`cotp-web.yaml`** if you use the web UI) to the new Mac — same directory as `vault_path` is easiest.

```bash
chmod 600 ~/.config/cotp/qr-vault.yaml
```

### 6. Verify

```bash
ls -la ~/bin/cotp ~/bin/cotp-web ~/.cotp/venv/bin/python
cotp --help
cotp-web --help
cotp get tp00 admin
cotp-web cotp-web.yaml    # if cotp-web.yaml is in the vault directory
```

If **`~/bin/cotp` or `~/bin/cotp-web` is missing**, the install did not finish. Retry:

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
