#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_formatter_linter.sh
#
# PURPOSE
# -------
# Install Python code formatters and linters: ruff, black, isort, mypy,
# flake8, pylint. Tools are installed into the active Python environment
# (system pip or uv) and are available host-wide.
#
# USAGE
# -----
#   ./install_formatter_linter.sh
#   ./install_formatter_linter.sh --check   # verify without installing
#   (Does NOT require root when installing into user site-packages)

set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PATH="$THIS_DIR/.$(basename "$0").log"
echo >"$LOG_PATH"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}" | tee -a "$LOG_PATH"; }
echo_success() { echo -e "${GREEN}$1${NC}" | tee -a "$LOG_PATH"; }
echo_warning() { echo -e "${YELLOW}$1${NC}" | tee -a "$LOG_PATH"; }
echo_error() {
    echo -e "${RED}$1${NC}" | tee -a "$LOG_PATH" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------

PYTHON_TOOLS=(
    ruff
    black
    isort
    mypy
    flake8
    pylint
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pick_installer() {
    # Prefer uv pip (faster), fall back to pip3 / pip
    if command -v uv &>/dev/null; then
        echo "uv pip install"
    elif command -v pip3 &>/dev/null; then
        echo "pip3 install --user"
    elif command -v pip &>/dev/null; then
        echo "pip install --user"
    else
        echo_error "No pip installer found. Install Python/pip first."
    fi
}

install_python_tools() {
    local installer
    installer="$(pick_installer)"
    echo_info "Using installer: ${installer}"

    for pkg in "${PYTHON_TOOLS[@]}"; do
        echo_info "  Installing ${pkg}..."
        ${installer} "${pkg}" 2>&1 | tee -a "$LOG_PATH"
    done
}

verify_python_tools() {
    echo_info "Verifying Python formatter/linter tools..."
    local failed=0

    # Ensure user local bin is on PATH
    export PATH="$HOME/.local/bin:$PATH"

    declare -A TOOL_CMDS=(
        [ruff]="ruff --version"
        [black]="black --version"
        [isort]="isort --version"
        [mypy]="mypy --version"
        [flake8]="flake8 --version"
        [pylint]="pylint --version"
    )

    for tool in "${!TOOL_CMDS[@]}"; do
        if command -v "$tool" &>/dev/null; then
            version_line="$(${TOOL_CMDS[$tool]} 2>&1 | head -1)"
            echo_success "  $tool: $version_line"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done

    if [[ $failed -eq 0 ]]; then
        echo_success "All Python formatter/linter tools verified."
    else
        echo_warning "$failed tool(s) not found."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --check)
        CHECK_ONLY=true
        shift
        ;;
    -h | --help)
        echo "Usage: $0 [--check]"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "Python Formatter/Linter Installation Script"
echo_info "=========================================="
echo_info "Tools: ${PYTHON_TOOLS[*]}"

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_python_tools
    exit $?
fi

# Idempotency check — pip install is inherently idempotent (upgrades if needed)
echo_info "Installation is idempotent — existing tools will be upgraded if outdated."

install_python_tools
verify_python_tools

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  PATH=\$HOME/.local/bin:\$PATH"
echo_info ""
echo_info "Usage examples:"
echo_info "  Format:  ruff format .  |  black .  |  isort ."
echo_info "  Lint:    ruff check .   |  flake8 . |  pylint src/"
echo_info "  Type:    mypy src/"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind \$HOME/.local/bin:\$HOME/.local/bin:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
