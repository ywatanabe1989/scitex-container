#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_nodejs.sh
#
# PURPOSE
# -------
# Install Node.js 20.x LTS on the host via the official NodeSource apt
# repository. Node.js is required for mermaid-cli (mmdc) diagram rendering.
#
# USAGE
# -----
#   sudo ./install_nodejs.sh
#   sudo ./install_nodejs.sh --check   # verify without installing

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

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

verify_nodejs() {
    echo_info "Verifying Node.js installation..."
    local failed=0

    if command -v node &>/dev/null; then
        echo_success "  node: $(node --version 2>&1)"
    else
        echo_warning "  node: NOT FOUND"
        ((failed++)) || true
    fi

    if command -v npm &>/dev/null; then
        echo_success "  npm: $(npm --version 2>&1)"
    else
        echo_warning "  npm: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "All Node.js tools verified."
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
echo_info "Node.js 20.x LTS Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_nodejs
    exit $?
fi

check_root

# Idempotency check
if command -v node &>/dev/null; then
    CURRENT_VERSION="$(node --version 2>&1)"
    echo_warning "Node.js already installed: $CURRENT_VERSION"
    echo_info "Re-running NodeSource setup is idempotent — continuing."
fi

echo_info "Installing prerequisites (curl, ca-certificates)..."
apt-get install -y ca-certificates curl 2>&1 | tee -a "$LOG_PATH"

echo_info "Fetching and running NodeSource setup script for Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh
bash /tmp/nodesource_setup.sh 2>&1 | tee -a "$LOG_PATH"
rm -f /tmp/nodesource_setup.sh

echo_info "Installing nodejs..."
apt-get install -y nodejs 2>&1 | tee -a "$LOG_PATH"

verify_nodejs

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  NODE_BIN=/usr/bin/node"
echo_info "  NPM_BIN=/usr/bin/npm"
echo_info ""
echo_info "After installation, install global npm tools as your user (no sudo):"
echo_info "  npm config set prefix ~/.npm-global"
echo_info "  export PATH=~/.npm-global/bin:\$PATH"
echo_success "Log saved to: $LOG_PATH"

# EOF
