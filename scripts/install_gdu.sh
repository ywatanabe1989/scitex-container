#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_gdu.sh
#
# PURPOSE
# -------
# Install gdu (Go Disk Usage) on the host. A fast disk usage analyzer
# with an interactive TUI, useful for managing container image storage.
#
# USAGE
# -----
#   ./install_gdu.sh
#   ./install_gdu.sh --check   # verify without installing

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

GDU_VERSION="v5.29.0"
INSTALL_DIR="${HOME}/.local/bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

verify_gdu() {
    echo_info "Verifying gdu installation..."
    if command -v gdu &>/dev/null; then
        version="$(gdu --version 2>&1 | head -1)"
        echo_success "  gdu: $version"
    else
        echo_warning "  gdu: NOT FOUND"
        return 1
    fi
    echo_success "gdu verified."
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
echo_info "gdu Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_gdu
    exit $?
fi

# Check if already installed (idempotent)
if command -v gdu &>/dev/null; then
    CURRENT_VERSION="$(gdu --version 2>&1 | head -1)"
    echo_warning "gdu already installed: $CURRENT_VERSION"
    echo_info "Re-downloading will overwrite with version ${GDU_VERSION} — continuing."
fi

echo_info "Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo_info "Downloading gdu ${GDU_VERSION}..."
TEMP_DIR="$(mktemp -d)"
curl -fsSL \
    "https://github.com/dundee/gdu/releases/download/${GDU_VERSION}/gdu_linux_amd64.tgz" \
    -o "$TEMP_DIR/gdu.tgz" 2>&1 | tee -a "$LOG_PATH"

echo_info "Extracting archive..."
tar -xzf "$TEMP_DIR/gdu.tgz" -C "$TEMP_DIR" 2>&1 | tee -a "$LOG_PATH"

# Binary may be named gdu_linux_amd64 or gdu
BINARY="$(find "$TEMP_DIR" -maxdepth 1 -name 'gdu*' -type f | head -1)"
if [[ -z "$BINARY" ]]; then
    echo_error "ERROR: gdu binary not found in archive."
fi

cp "$BINARY" "$INSTALL_DIR/gdu"
chmod +x "$INSTALL_DIR/gdu"
rm -rf "$TEMP_DIR"

verify_gdu

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  GDU_BIN=${INSTALL_DIR}/gdu"
echo_info ""
echo_info "Ensure ${INSTALL_DIR} is on your PATH:"
echo_info "  export PATH=\"${INSTALL_DIR}:\$PATH\""
echo_success "Log saved to: $LOG_PATH"

# EOF
