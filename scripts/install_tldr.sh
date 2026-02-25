#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_tldr.sh
#
# PURPOSE
# -------
# Install tldr (community-maintained help pages) on the host.
# Provides concise, practical command examples inside and outside containers.
#
# USAGE
# -----
#   ./install_tldr.sh
#   ./install_tldr.sh --check   # verify without installing

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
# Helpers
# ---------------------------------------------------------------------------

verify_tldr() {
    echo_info "Verifying tldr installation..."
    if command -v tldr &>/dev/null; then
        version="$(tldr --version 2>&1 | head -1)"
        echo_success "  tldr: $version"
    else
        echo_warning "  tldr: NOT FOUND"
        return 1
    fi
    echo_success "tldr verified."
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
echo_info "tldr Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_tldr
    exit $?
fi

# Check if already installed (idempotent)
if command -v tldr &>/dev/null; then
    CURRENT_VERSION="$(tldr --version 2>&1 | head -1)"
    echo_warning "tldr already installed: $CURRENT_VERSION"
    echo_info "pip install --upgrade is idempotent — continuing."
fi

if ! command -v pip &>/dev/null && ! command -v pip3 &>/dev/null; then
    echo_error "ERROR: pip/pip3 not found. Install Python and pip first."
fi

PIP_CMD="$(command -v pip3 2>/dev/null || command -v pip)"

echo_info "Installing tldr via pip (user install)..."
"$PIP_CMD" install --user --upgrade tldr 2>&1 | tee -a "$LOG_PATH"

# Ensure SSL certificates are in place for tldr to fetch pages
echo_info "Checking SSL certificate configuration..."
if python3 -m certifi &>/dev/null 2>&1; then
    SSL_CERT_FILE="$(python3 -m certifi 2>/dev/null)"
    echo_info "  certifi CA bundle: $SSL_CERT_FILE"
    export SSL_CERT_FILE
else
    echo_warning "  certifi not found; tldr will use system certificates."
fi

verify_tldr

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  SSL_CERT_FILE=\$(python3 -m certifi)   # if page downloads fail"
echo_info "  REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
echo_info ""
echo_info "Ensure ~/.local/bin is on your PATH:"
echo_info "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo_success "Log saved to: $LOG_PATH"

# EOF
