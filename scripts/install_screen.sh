#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_screen.sh
#
# PURPOSE
# -------
# Install GNU Screen from source (screen-4.9.1). Built to the system prefix
# so it can be bind-mounted or used directly on the host.
#
# USAGE
# -----
#   sudo ./install_screen.sh
#   sudo ./install_screen.sh --check   # verify without installing

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
# Configuration
# ---------------------------------------------------------------------------

SCREEN_VERSION="4.9.1"
SCREEN_URL="https://ftp.gnu.org/gnu/screen/screen-${SCREEN_VERSION}.tar.gz"
INSTALL_PREFIX="/usr/local"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

install_screen_deps() {
    echo_info "Installing build dependencies..."
    apt-get install -y \
        build-essential \
        libncurses5-dev \
        libncursesw5-dev \
        wget \
        2>&1 | tee -a "$LOG_PATH"
}

build_screen() {
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT

    echo_info "Downloading screen-${SCREEN_VERSION}..."
    wget -q "${SCREEN_URL}" -O "${tmp_dir}/screen-${SCREEN_VERSION}.tar.gz" 2>&1 | tee -a "$LOG_PATH"

    echo_info "Extracting source..."
    tar -xzf "${tmp_dir}/screen-${SCREEN_VERSION}.tar.gz" -C "${tmp_dir}"

    echo_info "Configuring screen-${SCREEN_VERSION}..."
    cd "${tmp_dir}/screen-${SCREEN_VERSION}"
    ./configure --prefix="${INSTALL_PREFIX}" 2>&1 | tee -a "$LOG_PATH"

    echo_info "Building screen (make -j$(nproc))..."
    make -j"$(nproc)" 2>&1 | tee -a "$LOG_PATH"

    echo_info "Installing screen..."
    make install 2>&1 | tee -a "$LOG_PATH"

    cd /
}

verify_screen() {
    echo_info "Verifying GNU Screen installation..."
    local failed=0

    if command -v screen &>/dev/null; then
        echo_success "  screen: $(screen --version 2>&1 | head -1)"
    else
        echo_warning "  screen: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "GNU Screen verified."
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
        echo "Usage: sudo $0 [--check]"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "GNU Screen Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_screen
    exit $?
fi

check_root

# Idempotency check
if command -v screen &>/dev/null; then
    CURRENT_VERSION="$(screen --version 2>&1 | head -1)"
    echo_warning "screen already installed: $CURRENT_VERSION"
    echo_info "Proceeding to rebuild from source — this is idempotent."
fi

apt-get update -qq 2>&1 | tee -a "$LOG_PATH"
install_screen_deps
build_screen
verify_screen

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  SCREENDIR=/tmp/.screen-\$USER"
echo_info "  SCREENRC=\$HOME/.screenrc"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind ${INSTALL_PREFIX}/bin/screen:${INSTALL_PREFIX}/bin/screen:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
