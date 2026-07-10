#!/usr/bin/env bash
# Install cotp into ~/bin (or INSTALL_BINDIR). Uses ~/.cotp/venv (isolated; no PEP 668).
#
# Usage:
#   ./install.sh                 # full install (local tree if pyproject.toml present, else GitHub)
#   ./install.sh --preflight     # check prerequisites only; exit 0 if ready
#   ./install.sh --verify        # verify existing install; exit 0 if OK
#   ./install.sh --no-cleanup    # keep repo (developers)
#   ./install.sh --cleanup       # remove install dir even in a git clone
#   ./install.sh --bin-only      # only ~/bin/cotp and ~/bin/cotp-web (venv already at ~/.cotp/venv)
#
#   COTP_INSTALL_LOCAL=1 ./install.sh   # force build from this directory
#   COTP_INSTALL_GITHUB=1 ./install.sh  # force GitHub (ignore local tree)
#
# Prerequisites (macOS):
#   brew install zbar git python@3.12
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_BINDIR="${INSTALL_BINDIR:-${HOME:-}/bin}"
CONFIG_DIR="${HOME:-}/.config/cotp"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
VENV_DIR="${HOME:-}/.cotp/venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
MIN_PYTHON=311
NO_CLEANUP=0
FORCE_CLEANUP=0
BIN_ONLY=0
PREFLIGHT_ONLY=0
VERIFY_ONLY=0
GITHUB_PKG='cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git'
OLD_VENV_DIRS=(
  "${HOME:-}/.local/share/cotp/venv"
  "${HOME:-}/.cotp/venv"
)

die() {
  echo "cotp install: error: $*" >&2
  exit 1
}

note() {
  echo "cotp install: $*" >&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

python_bin() {
  local c
  for c in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.13 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3.12 \
           /usr/local/bin/python3 /usr/bin/python3; do
    if [[ -x "$c" ]]; then
      echo "$c"
      return
    fi
  done
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  die "python3 not found — macOS: brew install python@3.12"
}

check_python_version() {
  local py="$1"
  local ver
  ver="$("$py" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")')"
  if [[ "$ver" -lt "$MIN_PYTHON" ]]; then
    die "Python 3.11+ required (found $($py --version 2>&1)) — macOS: brew install python@3.12"
  fi
}

check_home() {
  [[ -n "${HOME:-}" ]] || die "HOME is not set; cannot install to ~/bin"
  INSTALL_BINDIR="${INSTALL_BINDIR:-${HOME}/bin}"
  CONFIG_DIR="${HOME}/.config/cotp"
  CONFIG_FILE="${CONFIG_DIR}/config.yaml"
  VENV_DIR="${HOME}/.cotp/venv"
  VENV_PYTHON="${VENV_DIR}/bin/python"
}

check_zbar_system() {
  case "$(uname -s)" in
    Darwin)
      command -v brew >/dev/null 2>&1 || die "Homebrew not found — install from https://brew.sh then: brew install zbar"
      if ! brew list zbar &>/dev/null; then
        die "zbar not installed — run: brew install zbar"
      fi
      ;;
    Linux)
      if [[ -f /usr/lib/x86_64-linux-gnu/libzbar.so ]] \
        || [[ -f /usr/lib/libzbar.so ]] \
        || ldconfig -p 2>/dev/null | grep -q libzbar; then
        return 0
      fi
      die "libzbar not found — run: sudo apt install libzbar0"
      ;;
  esac
}

verify_pyzbar() {
  local py="$1"
  "$py" -c "from pyzbar.pyzbar import decode  # noqa: F401" \
    || die "pyzbar cannot load zbar — macOS: brew install zbar; then re-run ./install.sh"
}

use_local_source() {
  [[ "${COTP_INSTALL_GITHUB:-0}" == 1 ]] && return 1
  [[ "${COTP_INSTALL_LOCAL:-0}" == 1 ]] && return 0
  [[ -f "$ROOT/pyproject.toml" && -f "$ROOT/cotp_cli/main.py" && -f "$ROOT/cotp_web/__main__.py" ]]
}

preflight_checks() {
  local py ver failures=0
  check_home
  note "preflight: HOME=$HOME"
  note "preflight: will install to $INSTALL_BINDIR/cotp, $INSTALL_BINDIR/cotp-web and $CONFIG_FILE"

  py=""
  for c in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.13 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3.12 \
           /usr/local/bin/python3 /usr/bin/python3; do
    [[ -x "$c" ]] && py="$c" && break
  done
  if [[ -z "$py" ]] && command -v python3 >/dev/null 2>&1; then
    py="$(command -v python3)"
  fi
  if [[ -z "$py" ]]; then
    note "preflight: FAIL python3 not found — brew install python@3.12"
    failures=$((failures + 1))
  else
    note "preflight: ok python=$py ($($py --version 2>&1))"
    ver="$("$py" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")')"
    if [[ "$ver" -lt "$MIN_PYTHON" ]]; then
      note "preflight: FAIL Python 3.11+ required"
      failures=$((failures + 1))
    fi
  fi

  if command -v git >/dev/null 2>&1; then
    note "preflight: ok git"
  else
    note "preflight: FAIL git not found — brew install git"
    failures=$((failures + 1))
  fi

  case "$(uname -s)" in
    Darwin)
      if ! command -v brew >/dev/null 2>&1; then
        note "preflight: FAIL Homebrew missing"
        failures=$((failures + 1))
      elif ! brew list zbar &>/dev/null; then
        note "preflight: FAIL run: brew install zbar"
        failures=$((failures + 1))
      else
        note "preflight: ok zbar (brew)"
      fi
      ;;
    Linux)
      if [[ -f /usr/lib/x86_64-linux-gnu/libzbar.so ]] \
        || [[ -f /usr/lib/libzbar.so ]] \
        || ldconfig -p 2>/dev/null | grep -q libzbar; then
        note "preflight: ok libzbar"
      else
        note "preflight: FAIL run: sudo apt install libzbar0"
        failures=$((failures + 1))
      fi
      ;;
  esac

  if use_local_source; then
    note "preflight: ok install source=local ($ROOT)"
  else
    note "preflight: install source=GitHub (needs network)"
    if ! git ls-remote https://github.com/ytensor42/qr-vault-cli.git HEAD &>/dev/null; then
      note "preflight: FAIL cannot reach GitHub (or copy this repo and run from it for offline local install)"
      failures=$((failures + 1))
    else
      note "preflight: ok GitHub reachable"
    fi
  fi

  local parent="${INSTALL_BINDIR%/*}"
  if [[ -d "$INSTALL_BINDIR" ]] || [[ -w "$parent" ]]; then
    note "preflight: ok writable install dir parent ($parent)"
  else
    note "preflight: FAIL cannot create $INSTALL_BINDIR (check permissions)"
    failures=$((failures + 1))
  fi

  if [[ -d "$CONFIG_DIR" ]] || [[ -w "${HOME}/.config" ]] || [[ -w "$HOME" ]]; then
    note "preflight: ok writable config dir"
  else
    note "preflight: FAIL cannot create $CONFIG_DIR"
    failures=$((failures + 1))
  fi

  [[ "$failures" -eq 0 ]]
}

verify_installation() {
  local dest="$INSTALL_BINDIR/cotp"
  local dest_web="$INSTALL_BINDIR/cotp-web"
  check_home
  [[ -f "$CONFIG_FILE" ]] || die "verify FAIL: missing $CONFIG_FILE"
  [[ -x "$dest" ]] || die "verify FAIL: missing or not executable: $dest"
  [[ -x "$dest_web" ]] || die "verify FAIL: missing or not executable: $dest_web"
  [[ -x "$VENV_PYTHON" ]] || die "verify FAIL: missing venv python: $VENV_PYTHON"
  "$VENV_PYTHON" -c "import cotp_cli, cotp_web" || die "verify FAIL: cotp_cli/cotp_web not importable in venv"
  verify_pyzbar "$VENV_PYTHON"
  "$dest" --help >/dev/null 2>&1 || die "verify FAIL: $dest --help failed"
  "$dest_web" --help >/dev/null 2>&1 || die "verify FAIL: $dest_web --help failed"
  note "verify OK:"
  note "  cotp:     $dest"
  note "  cotp-web: $dest_web"
  note "  config:   $CONFIG_FILE"
  note "  venv:     $VENV_DIR"
}

install_failed_hint() {
  local rc="${1:-1}"
  echo "" >&2
  echo "cotp install: === install FAILED (exit $rc) ===" >&2
  echo "cotp install:   $INSTALL_BINDIR/cotp — $([[ -x "${INSTALL_BINDIR}/cotp" ]] && echo OK || echo MISSING)" >&2
  echo "cotp install:   $INSTALL_BINDIR/cotp-web — $([[ -x "${INSTALL_BINDIR}/cotp-web" ]] && echo OK || echo MISSING)" >&2
  echo "cotp install:   $CONFIG_FILE — $([[ -f "$CONFIG_FILE" ]] && echo OK || echo MISSING)" >&2
  echo "cotp install:   $VENV_PYTHON — $([[ -x "$VENV_PYTHON" ]] && echo OK || echo MISSING)" >&2
  if [[ -x "$VENV_PYTHON" ]] && "$VENV_PYTHON" -c "import cotp_cli, cotp_web" 2>/dev/null; then
    echo "cotp install: venv OK — retry: ./install.sh --bin-only" >&2
  else
    echo "cotp install: macOS: brew install zbar git python@3.12 && ./install.sh" >&2
  fi
}

remove_old_venvs() {
  local d
  for d in "${OLD_VENV_DIRS[@]}"; do
    if [[ -d "$d" ]]; then
      note "removing old venv: $d"
      rm -rf "$d"
    fi
  done
  rm -rf "${HOME}/.local/share/cotp" 2>/dev/null || true
}

create_venv() {
  local system_py="$1"
  remove_old_venvs
  mkdir -p "${HOME}/.cotp"
  note "creating venv at $VENV_DIR ..."
  "$system_py" -m venv --copies "$VENV_DIR" || die "python -m venv failed"
  if ! "$VENV_PYTHON" -c 'import sys; print(sys.version_info[:2])' >/dev/null 2>&1; then
    rm -rf "$VENV_DIR"
    die "venv broken — rm -rf ~/.cotp ~/.local/share/cotp and re-run ./install.sh"
  fi
}

pip_install_with_retry() {
  local attempt
  for attempt in 1 2 3; do
    if "$@"; then
      return 0
    fi
    note "pip attempt $attempt failed; retrying..."
    sleep 2
  done
  return 1
}

pip_install_package() {
  local system_py="$1"
  export TMPDIR="${TMPDIR:-/tmp}"
  mkdir -p "$TMPDIR"
  create_venv "$system_py"
  note "upgrading pip in venv..."
  "$VENV_PYTHON" -m pip install --upgrade pip wheel >/dev/null 2>&1 || true

  if use_local_source; then
    note "installing from local tree: $ROOT"
    pip_install_with_retry "$VENV_PYTHON" -m pip install --upgrade "$ROOT" >&2 \
      || die "pip install from $ROOT failed"
  else
    note "installing from GitHub (main)..."
    pip_install_with_retry "$VENV_PYTHON" -m pip install --upgrade "$GITHUB_PKG" >&2 \
      || die "pip install from GitHub failed (offline? copy this repo folder and re-run ./install.sh)"
  fi
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
  local dest="$1"
  local tmp
  tmp="$(mktemp)"
  cat >"$tmp" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export COTP_CONFIG="\${COTP_CONFIG:-${CONFIG_FILE}}"
exec "\${HOME}/.cotp/venv/bin/python" -m cotp_cli "\$@"
EOF
  if [[ -w "$(dirname "$dest")" ]] 2>/dev/null || [[ ! -e "$(dirname "$dest")" ]]; then
    mkdir -p "$(dirname "$dest")"
    install -m 755 "$tmp" "$dest"
  else
    note "need sudo to write $(dirname "$dest")"
    sudo mkdir -p "$(dirname "$dest")"
    sudo install -m 755 "$tmp" "$dest"
  fi
  rm -f "$tmp"
}

write_cotp_web_wrapper() {
  local dest="$1"
  local tmp
  tmp="$(mktemp)"
  cat >"$tmp" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export COTP_CONFIG="\${COTP_CONFIG:-${CONFIG_FILE}}"
exec "\${HOME}/.cotp/venv/bin/python" -m cotp_web "\$@"
EOF
  if [[ -w "$(dirname "$dest")" ]] 2>/dev/null || [[ ! -e "$(dirname "$dest")" ]]; then
    mkdir -p "$(dirname "$dest")"
    install -m 755 "$tmp" "$dest"
  else
    note "need sudo to write $(dirname "$dest")"
    sudo mkdir -p "$(dirname "$dest")"
    sudo install -m 755 "$tmp" "$dest"
  fi
  rm -f "$tmp"
}

install_bin_wrappers() {
  write_cotp_wrapper "$INSTALL_BINDIR/cotp"
  write_cotp_web_wrapper "$INSTALL_BINDIR/cotp-web"
}

ensure_bindir() {
  local dir="$1"
  [[ -d "$dir" ]] && return 0
  local parent
  parent="$(dirname "$dir")"
  if [[ -w "$parent" ]] 2>/dev/null || [[ ! -e "$parent" ]]; then
    mkdir -p "$dir"
    return 0
  fi
  note "creating $dir with sudo"
  sudo mkdir -p "$dir"
}

path_hint() {
  local dir="$1"
  case ":$PATH:" in
    *:"$dir":*) return 0 ;;
  esac
  echo "" >&2
  note "add $dir to PATH, e.g.:"
  echo '  echo '\''export PATH="$HOME/bin:$PATH"'\'' >> ~/.zshrc && source ~/.zshrc' >&2
}

should_cleanup() {
  [[ "$NO_CLEANUP" -eq 1 ]] && return 1
  [[ "$FORCE_CLEANUP" -eq 1 ]] && return 0
  if [[ -d "$ROOT/.git" ]]; then
    note "git checkout detected; keeping files (use --cleanup to remove tree)"
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
  note "removing install files under $ROOT"
  for item in "$ROOT"/* "$ROOT"/.[!.]* "$ROOT"/..?*; do
    [[ -e "$item" ]] || continue
    name="$(basename "$item")"
    [[ "$name" == "." || "$name" == ".." ]] && continue
    if cleanup_skip_name "$name"; then
      continue
    fi
    rm -rf "$item" 2>/dev/null || note "warning: could not remove $name"
  done
  rm -f "$ROOT/install.sh" 2>/dev/null || true
}

install_wrapper_only() {
  check_home
  [[ -x "$VENV_PYTHON" ]] || die "venv missing at $VENV_DIR — run ./install.sh"
  "$VENV_PYTHON" -c "import cotp_cli, cotp_web" || die "cotp_cli/cotp_web missing in venv — run ./install.sh"
  ensure_config_yaml
  ensure_bindir "$INSTALL_BINDIR"
  install_bin_wrappers
  verify_installation
  path_hint "$INSTALL_BINDIR"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-cleanup) NO_CLEANUP=1 ;;
      --cleanup) FORCE_CLEANUP=1 ;;
      --bin-only) BIN_ONLY=1 ;;
      --preflight) PREFLIGHT_ONLY=1 ;;
      --verify) VERIFY_ONLY=1 ;;
      -h | --help)
        sed -n '2,20p' "$0"
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
  local system_py venv_py
  parse_args "$@"
  check_home

  if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    verify_installation
    note "=== cotp is installed correctly on this machine ==="
    exit 0
  fi

  if [[ "$PREFLIGHT_ONLY" -eq 1 ]]; then
  preflight_checks || die "preflight failed (see messages above)"
    note "=== preflight OK — run ./install.sh ==="
    exit 0
  fi

  if [[ "$BIN_ONLY" -eq 1 ]]; then
    trap 'install_failed_hint $?' ERR
    install_wrapper_only
    trap - ERR
    note "=== cotp is installed correctly on this machine ==="
    exit 0
  fi

  trap 'install_failed_hint $?' ERR

  note "=== cotp install start ==="
  note "HOME=$HOME  INSTALL_BINDIR=$INSTALL_BINDIR"

  preflight_checks || die "preflight failed — fix items above, or run: ./install.sh --preflight"

  ensure_config_yaml
  ensure_bindir "$INSTALL_BINDIR"

  system_py="$(python_bin)"
  check_python_version "$system_py"
  check_zbar_system

  pip_install_package "$system_py"
  [[ -x "$VENV_PYTHON" ]] || die "venv python missing: $VENV_PYTHON"
  "$VENV_PYTHON" -c "import cotp_cli, cotp_web" || die "cotp_cli/cotp_web import failed"
  verify_pyzbar "$VENV_PYTHON"

  install_bin_wrappers
  verify_installation
  path_hint "$INSTALL_BINDIR"
  note "copy qr-vault.yaml to vault_path in $CONFIG_FILE if needed"
  note "cotp-web: place cotp-web.yaml next to vault (see cotp_web/entries.example.yaml)"

  trap - ERR
  cleanup_install_tree
  note "=== cotp is installed correctly on this machine ==="
}

main "$@"
