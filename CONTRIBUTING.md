# Contributing

Thank you for helping improve [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) (PyPI package **`cotp-cli`**, CLI **`cotp`**).

## Ground rules

- **Do not** paste real seeds, TOTP codes, vault passwords, or `qr-vault.yaml` snippets in issues or pull requests. Use fake placeholders.
- Keep changes focused on one topic per pull request when possible.
- Match existing code style; the project uses **Ruff** and **pytest**.

## Development setup

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**System dependency:** pyzbar needs the **zbar** shared library (e.g. macOS `brew install zbar`, Debian/Ubuntu `sudo apt install libzbar0`).

## Checks

```bash
ruff check .
pytest
```

## Pull requests

- Describe **what** changed and **why**.
- Add or update tests when behavior changes.
- Update `CHANGELOG.md` under **Unreleased** (or the release section maintainers use).
