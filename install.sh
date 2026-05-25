#!/usr/bin/env bash
# Install cotp into ~/bin (or INSTALL_BINDIR). Leaves only ~/bin/cotp on the system;
# removes this script and other files in the install directory when done.
#
# Usage:
#   ./install.sh              # install + remove files in this directory (except during run)
#   ./install.sh --no-cleanup # keep repo (developers)
#   ./install.sh --cleanup    # remove install dir even in a git clone
#
# Prerequisites (install first):
#   macOS:  brew install zbar
#           brew install python@3.12   # if python3 < 3.11
#   Linux:  sudo apt install libzbar0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_BINDIR="${INSTALL_BINDIR:-$HOME/bin}"
CONFIG_DIR="${HOME}/.config/cotp"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
VENV_DIR="${HOME}/.local/share/cotp/venv"
MIN_PYTHON=311
NO_CLEANUP=0
FORCE_CLEANUP=0
GITHUB_PKG='cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git'

die() {
  echo "cotp install: error: $*" >&2
  exit 1
}

note() {
  echo "cotp install: $*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  die "python3 not found (need Python 3.11+; macOS: brew install python@3.12)"
}

check_python_version() {
  local py="$1"
  local ver
  ver="$("$py" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")')"
  if [[ "$ver" -lt "$MIN_PYTHON" ]]; then
    die "Python 3.11+ required (found $($py --version 2>&1)); macOS: brew install python@3.12"
  fi
}

check_zbar_system() {
  case "$(uname -s)" in
    Darwin)
      command -v brew >/dev/null 2>&1 || die "Homebrew not found; install zbar manually, then re-run"
      brew list zbar &>/dev/null || die "install zbar first: brew install zbar"
      ;;
    Linux)
      note "Linux: ensure libzbar is installed (e.g. sudo apt install libzbar0)"
      ;;
  esac
}

verify_pyzbar() {
  local py="$1"
  "$py" -c "from pyzbar.pyzbar import zbar_version; zbar_version()" \
    || die "pyzbar cannot load zbar — install the system zbar library, then re-run"
}

ensure_venv_python() {
  local system_py="$1"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    note "creating private venv at $VENV_DIR (avoids PEP 668 / externally-managed-environment)..."
    "$system_py" -m venv "$VENV_DIR"
  fi
  echo "$VENV_DIR/bin/python"
}

stage_source_in_tmp() {
  local stage
  stage="$(mktemp -d /tmp/cotp-src.XXXXXX)"
  cp "$ROOT/pyproject.toml" "$stage/"
  cp -R "$ROOT/cotp_cli" "$stage/"
  [[ -f "$ROOT/README.md" ]] && cp "$ROOT/README.md" "$stage/"
  [[ -f "$ROOT/LICENSE" ]] && cp "$ROOT/LICENSE" "$stage/"
  echo "$stage"
}

pip_install_package() {
  local system_py="$1"
  local venv_py stage
  export TMPDIR="${TMPDIR:-/tmp}"
  mkdir -p "$TMPDIR"
  venv_py="$(ensure_venv_python "$system_py")"
  note "installing cotp into $VENV_DIR (system Python packages are not modified)..."
  "$venv_py" -m pip install --upgrade pip wheel >/dev/null 2>&1 || true

  if [[ "${COTP_INSTALL_FROM:-}" == pypi ]]; then
    note "installing cotp-cli from PyPI..."
    "$venv_py" -m pip install --upgrade cotp-cli || die "pip install cotp-cli from PyPI failed"
    echo "$venv_py"
    return 0
  fi

  if [[ -f "$ROOT/pyproject.toml" ]]; then
    stage="$(stage_source_in_tmp)"
    note "building from $stage (avoids long-path pip errors)..."
    if ! "$venv_py" -m pip install --upgrade "$stage"; then
      rm -rf "$stage"
      die "pip install failed (if 'filename too long': use a short folder, e.g. ~/cotp-install, or COTP_INSTALL_FROM=pypi ./install.sh)"
    fi
    rm -rf "$stage"
  else
    note "no pyproject.toml here; installing from GitHub..."
    "$venv_py" -m pip install --upgrade "$GITHUB_PKG" \
      || die "pip install from GitHub failed"
  fi
  echo "$venv_py"
}

ensure_config_yaml() {
  mkdir -p "$CONFIG_DIR"
  if [[ -f "$CONFIG_FILE" ]]; then
    note "config exists: $CONFIG_FILE"
    return 0
  fi
  cat >"$CONFIG_FILE" <<'EOF'
# Default cotp configuration (created by install.sh).
# Override path: export COTP_CONFIG=/path/to/config.yaml

vault_path: ~/.config/cotp/qr-vault.yaml
qr_image_dir: ~/Downloads/Screenshots
EOF
  chmod 600 "$CONFIG_FILE"
  note "created config: $CONFIG_FILE"
}

write_cotp_wrapper() {
  local py="$1"
  local dest="$2"
  local tmp
  tmp="$(mktemp)"
  cat >"$tmp" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export COTP_CONFIG="\${COTP_CONFIG:-${CONFIG_FILE}}"
exec "$py" -m cotp_cli "\$@"
EOF
  if [[ -w "$(dirname "$dest")" ]]; then
    install -m 755 "$tmp" "$dest"
  else
    note "need permission to write $(dirname "$dest")"
    sudo install -m 755 "$tmp" "$dest"
  fi
  rm -f "$tmp"
}

ensure_bindir() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    return 0
  fi
  if [[ -w "$(dirname "$dir")" ]]; then
    mkdir -p "$dir"
    return 0
  fi
  note "creating $dir (sudo)"
  sudo mkdir -p "$dir"
}

path_hint() {
  local dir="$1"
  case ":$PATH:" in
    *:"$dir":*) return 0 ;;
  esac
  echo "" >&2
  echo "cotp install: add $dir to PATH, for example:" >&2
  echo '  echo export PATH="$HOME/bin:$PATH" >> ~/.zshrc' >&2
}

should_cleanup() {
  [[ "$NO_CLEANUP" -eq 1 ]] && return 1
  [[ "$FORCE_CLEANUP" -eq 1 ]] && return 0
  if [[ -d "$ROOT/.git" ]]; then
    note "git checkout detected; keeping files here (use --cleanup to remove install tree)"
    return 1
  fi
  return 0
}

cleanup_skip_name() {
  case "$1" in
    .venv | .git) return 0 ;;
  esac
  return 1
}

cleanup_install_tree() {
  if ! should_cleanup; then
    return 0
  fi
  local item name
  note "removing install files under $ROOT (cotp is already in $INSTALL_BINDIR/cotp)"
  for item in "$ROOT"/* "$ROOT"/.[!.]* "$ROOT"/..?*; do
    [[ -e "$item" ]] || continue
    name="$(basename "$item")"
    [[ "$name" == "." || "$name" == ".." ]] && continue
    if cleanup_skip_name "$name"; then
      note "skipping $name (remove manually if needed: rm -rf $(printf '%q' "$item"))"
      continue
    fi
    rm -rf "$item" 2>/dev/null || note "warning: could not remove $name (delete manually)"
  done
  rm -f "$ROOT/install.sh" 2>/dev/null || true
  note "done. on this machine you only need:"
  note "  $INSTALL_BINDIR/cotp"
  note "  $CONFIG_FILE"
  note "  $VENV_DIR"
  note "delete this empty folder if it remains: rmdir $ROOT 2>/dev/null || true"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-cleanup)
        NO_CLEANUP=1
        ;;
      --cleanup)
        FORCE_CLEANUP=1
        ;;
      -h | --help)
        sed -n '2,12p' "$0"
        exit 0
        ;;
      *)
        die "unknown option: $1 (try --help)"
        ;;
    esac
    shift
  done
}

main() {
  local system_py venv_py dest
  parse_args "$@"
  system_py="$(python_bin)"
  check_python_version "$system_py"

  note "step 1 — prerequisites (run these first if missing):"
  note "  macOS:  brew install zbar"
  note "          brew install python@3.12   # if python3 < 3.11"
  note "  Linux:  sudo apt install libzbar0"

  check_zbar_system
  venv_py="$(pip_install_package "$system_py")"
  "$venv_py" -c "import cotp_cli" || die "cotp_cli import failed after pip install"
  verify_pyzbar "$venv_py"

  ensure_config_yaml
  ensure_bindir "$INSTALL_BINDIR"
  dest="$INSTALL_BINDIR/cotp"
  write_cotp_wrapper "$venv_py" "$dest"

  note "installed: $dest (venv: $VENV_DIR)"
  if "$dest" --help >/dev/null 2>&1; then
    note "smoke test: ok"
  fi
  path_hint "$INSTALL_BINDIR"
  note "copy qr-vault.yaml to the vault_path in $CONFIG_FILE if needed"
  cleanup_install_tree
}

main "$@"
