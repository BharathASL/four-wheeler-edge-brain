#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv"
SKIP_SYSTEM_PACKAGES=0
SKIP_PIP=0
RUN_SMOKE_TEST=0
DRY_RUN=0

APT_PACKAGES=(
    python3
    python3-venv
    python3-pip
    python3-dev
    build-essential
    git
    cmake
    ninja-build
    pkg-config
    libgomp1
    libopenblas-dev
    portaudio19-dev
    libsndfile1
    espeak-ng
    ffmpeg
    v4l-utils
)

usage() {
    cat <<'EOF'
Usage: scripts/setup_wsl_dev.sh [options]

Bootstraps a WSL Ubuntu machine for this repository.

Options:
  --venv-path PATH          Virtual environment path (default: .venv)
  --skip-system-packages    Skip apt-get update/install
  --skip-pip                Skip pip install -r requirements.txt
  --run-smoke-test          Run tests/test_smoke.py after setup
  --dry-run                 Print commands without executing them
  -h, --help                Show this help text

Examples:
  scripts/setup_wsl_dev.sh
  scripts/setup_wsl_dev.sh --dry-run
  scripts/setup_wsl_dev.sh --venv-path .venv-wsl --run-smoke-test
EOF
}

log() {
    printf '[setup] %s\n' "$*"
}

run_cmd() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        printf '[dry-run] %s\n' "$*"
        return 0
    fi
    "$@"
}

is_wsl() {
    grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$1" >&2
        exit 1
    fi
}

install_system_packages() {
    local apt_packages=("${APT_PACKAGES[@]}")

    if command -v python3 >/dev/null 2>&1; then
        local py_minor
        py_minor="$(python3 - <<'PY'
import sys
print(f"python{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
        apt_packages+=("${py_minor}-venv" "${py_minor}-dev")
    fi

    if [[ "$SKIP_SYSTEM_PACKAGES" -eq 1 ]]; then
        log "Skipping system package installation"
        return 0
    fi

    if [[ "$EUID" -eq 0 ]]; then
        run_cmd apt-get update
        run_cmd apt-get install -y "${apt_packages[@]}"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        run_cmd sudo apt-get update
        run_cmd sudo apt-get install -y "${apt_packages[@]}"
        return 0
    fi

    printf 'System package install requires root or sudo. Re-run with sudo or use --skip-system-packages.\n' >&2
    exit 1
}

create_venv() {
    require_command python3
    local python_bin="$VENV_PATH/bin/python"

    if [[ -d "$VENV_PATH" ]]; then
        if [[ -x "$python_bin" ]] && "$python_bin" -m pip --version >/dev/null 2>&1; then
            log "Using existing virtual environment at $VENV_PATH"
            return 0
        fi

        log "Existing virtual environment at $VENV_PATH is incomplete; recreating it"
        run_cmd rm -rf "$VENV_PATH"
    fi

    log "Creating virtual environment at $VENV_PATH"
    if ! run_cmd python3 -m venv "$VENV_PATH"; then
        local py_minor
        py_minor="$(python3 - <<'PY'
import sys
print(f"python{sys.version_info.major}.{sys.version_info.minor}-venv")
PY
)"
        printf 'Failed to create virtual environment. Install %s or re-run without --skip-system-packages.\n' "$py_minor" >&2
        exit 1
    fi
}

install_python_packages() {
    if [[ "$SKIP_PIP" -eq 1 ]]; then
        log "Skipping Python dependency installation"
        return 0
    fi

    local pip_bin="$VENV_PATH/bin/pip"
    run_cmd "$pip_bin" install --upgrade pip setuptools wheel
    run_cmd "$pip_bin" install -r "$REPO_ROOT/requirements.txt"
}

run_smoke_test() {
    if [[ "$RUN_SMOKE_TEST" -ne 1 ]]; then
        return 0
    fi

    local python_bin="$VENV_PATH/bin/python"
    run_cmd "$python_bin" -m pytest -q "$REPO_ROOT/tests/test_smoke.py"
}

write_activation_hint() {
    cat <<EOF

Setup complete.

Next steps:
  source "$VENV_PATH/bin/activate"
  python -m pytest -q
  python main.py
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv-path)
            if [[ $# -lt 2 ]]; then
                printf 'Missing value for --venv-path\n' >&2
                exit 1
            fi
            VENV_PATH="$2"
            shift 2
            ;;
        --skip-system-packages)
            SKIP_SYSTEM_PACKAGES=1
            shift
            ;;
        --skip-pip)
            SKIP_PIP=1
            shift
            ;;
        --run-smoke-test)
            RUN_SMOKE_TEST=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ "$VENV_PATH" != /* ]]; then
    VENV_PATH="$REPO_ROOT/$VENV_PATH"
fi

log "Repository root: $REPO_ROOT"
if is_wsl; then
    log "WSL environment detected"
else
    log "WSL environment not detected; continuing anyway"
fi

install_system_packages
create_venv
install_python_packages
run_smoke_test
write_activation_hint