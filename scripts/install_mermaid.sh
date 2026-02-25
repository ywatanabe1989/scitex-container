#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_mermaid.sh
#
# PURPOSE
# -------
# Install Mermaid CLI (mmdc) as a global npm package in ~/.npm-global and
# install chrome-headless-shell via puppeteer for headless diagram rendering.
# Does NOT require root — all files are installed in the user home directory.
#
# USAGE
# -----
#   ./install_mermaid.sh
#   ./install_mermaid.sh --check   # verify without installing
#
# PREREQUISITE
# ------------
#   Node.js and npm must be installed first:
#     sudo ./install_nodejs.sh

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
# Config
# ---------------------------------------------------------------------------

NPM_GLOBAL_PATH="${HOME}/.npm-global"
NPM_GLOBAL_BIN="${NPM_GLOBAL_PATH}/bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_node_available() {
    if ! command -v node &>/dev/null; then
        echo_error "ERROR: node not found. Install Node.js first: sudo ./install_nodejs.sh"
    fi
    if ! command -v npm &>/dev/null; then
        echo_error "ERROR: npm not found. Install Node.js first: sudo ./install_nodejs.sh"
    fi
    echo_info "  node: $(node --version 2>&1)"
    echo_info "  npm:  $(npm --version 2>&1)"
}

verify_mermaid() {
    echo_info "Verifying Mermaid CLI installation..."
    local failed=0
    local mmdc_bin="${NPM_GLOBAL_BIN}/mmdc"

    if command -v mmdc &>/dev/null || [[ -x "${mmdc_bin}" ]]; then
        local mmdc_cmd
        mmdc_cmd="$(command -v mmdc 2>/dev/null || echo "${mmdc_bin}")"
        local version
        version="$("${mmdc_cmd}" --version 2>&1 | head -1)"
        echo_success "  mmdc: $version (${mmdc_cmd})"
    else
        echo_warning "  mmdc: NOT FOUND (looked in PATH and ${mmdc_bin})"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "Mermaid CLI verified."
        echo_info "  Ensure PATH includes: ${NPM_GLOBAL_BIN}"
    else
        echo_warning "mmdc not found."
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
echo_info "Mermaid CLI Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_mermaid
    exit $?
fi

# Require Node.js
check_node_available

# Idempotency check
if [[ -x "${NPM_GLOBAL_BIN}/mmdc" ]] || command -v mmdc &>/dev/null; then
    echo_warning "mmdc already installed."
    echo_info "Reinstalling to ensure up-to-date version — continuing."
fi

echo_info "Configuring npm global prefix to ${NPM_GLOBAL_PATH}..."
mkdir -p "${NPM_GLOBAL_PATH}"
npm config set prefix "${NPM_GLOBAL_PATH}"

# Ensure global bin is in PATH for this session
export PATH="${NPM_GLOBAL_BIN}:${PATH}"

echo_info "Clearing stale npm cache..."
npm cache clean --force 2>&1 | tee -a "$LOG_PATH"

echo_info "Removing any existing mermaid-cli installation..."
npm uninstall -g @mermaid-js/mermaid-cli 2>&1 | tee -a "$LOG_PATH" || true
rm -rf "${NPM_GLOBAL_PATH}/lib/node_modules/@mermaid-js/mermaid-cli"

echo_info "Installing @mermaid-js/mermaid-cli globally..."
npm install -g @mermaid-js/mermaid-cli 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing chrome-headless-shell via puppeteer..."
npx puppeteer browsers install chrome-headless-shell 2>&1 | tee -a "$LOG_PATH"

verify_mermaid

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  MMDC_BIN=${NPM_GLOBAL_BIN}/mmdc"
echo_info ""
echo_info "Add to ~/.bashrc or ~/.profile:"
echo_info "  export PATH=\"${NPM_GLOBAL_BIN}:\$PATH\""
echo_info ""
echo_info "Basic usage:"
echo_info "  mmdc -i diagram.mmd -o diagram.png"
echo_success "Log saved to: $LOG_PATH"

# EOF
