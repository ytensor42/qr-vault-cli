# Contributing

Thank you for helping improve **qr-vault-cli** (PyPI package **`cotp-cli`**, CLI **`cotp`**).

After you create the GitHub repository, replace the placeholder **`YOUR_GITHUB_USERNAME`** in `README.md`, `README-ko.md`, `pyproject.toml` (`[project.urls]`), `.github/ISSUE_TEMPLATE/config.yml`, `CHANGELOG.md` link footers, and CI badge URLs.

## Ground rules

- **Do not** paste real seeds, TOTP codes, vault passwords, or `qr-vault.yaml` snippets in issues or pull requests. Use fake placeholders.
- Keep changes focused on one topic per pull request when possible.
- Match existing code style; the project uses **Ruff** and **pytest**.

## Development setup

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/qr-vault-cli.git
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
