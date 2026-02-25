#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_gemini.sh
#
# PURPOSE
# -------
# Install Gemini CLI (@google/gemini-cli) as a global npm package in
# ~/.npm-global. Does NOT require root — all files are installed in the
# user home directory.
#
# USAGE
# -----
#   ./install_gemini.sh
#   ./install_gemini.sh --check   # verify without installing
#   ./install_gemini.sh --version 0.1.5
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
GEMINI_VERSION="latest"

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

verify_gemini() {
    echo_info "Verifying Gemini CLI installation..."
    local failed=0
    local gemini_bin="${NPM_GLOBAL_BIN}/gemini"

    if command -v gemini &>/dev/null || [[ -x "${gemini_bin}" ]]; then
        local gemini_cmd
        gemini_cmd="$(command -v gemini 2>/dev/null || echo "${gemini_bin}")"
        local version
        version="$("${gemini_cmd}" --version 2>&1 | head -1)"
        echo_success "  gemini: $version (${gemini_cmd})"
    else
        echo_warning "  gemini: NOT FOUND (looked in PATH and ${gemini_bin})"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "Gemini CLI verified."
        echo_info "  Ensure PATH includes: ${NPM_GLOBAL_BIN}"
    else
        echo_warning "gemini not found."
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
    --version)
        shift
        if [[ $# -gt 0 && "$1" != -* ]]; then
            GEMINI_VERSION="$1"
            shift
        else
            echo_error "ERROR: --version requires a version argument."
        fi
        ;;
    -h | --help)
        echo "Usage: $0 [--check] [--version VERSION]"
        echo ""
        echo "Options:"
        echo "  --check              Verify installation without installing"
        echo "  --version VERSION    Install specific version (default: latest)"
        echo "  -h, --help           Show this help message"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "Gemini CLI Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_gemini
    exit $?
fi

# Require Node.js
check_node_available

# Idempotency check
if [[ -x "${NPM_GLOBAL_BIN}/gemini" ]] || command -v gemini &>/dev/null; then
    echo_warning "gemini already installed."
    echo_info "Reinstalling to ensure up-to-date version — continuing."
fi

echo_info "Configuring npm global prefix to ${NPM_GLOBAL_PATH}..."
mkdir -p "${NPM_GLOBAL_PATH}"
npm config set prefix "${NPM_GLOBAL_PATH}"

# Ensure global bin is in PATH for this session
export PATH="${NPM_GLOBAL_BIN}:${PATH}"

echo_info "Clearing stale npm cache..."
npm cache clean --force 2>&1 | tee -a "$LOG_PATH"

echo_info "Removing any existing Gemini CLI installation..."
npm uninstall -g @google/gemini-cli 2>&1 | tee -a "$LOG_PATH" || true
rm -rf "${NPM_GLOBAL_PATH}/lib/node_modules/@google/gemini-cli"

if [[ "${GEMINI_VERSION}" == "latest" ]]; then
    echo_info "Installing @google/gemini-cli@latest globally..."
    npm install -g @google/gemini-cli 2>&1 | tee -a "$LOG_PATH"
else
    echo_info "Installing @google/gemini-cli@${GEMINI_VERSION} globally..."
    npm install -g "@google/gemini-cli@${GEMINI_VERSION}" 2>&1 | tee -a "$LOG_PATH"
fi

verify_gemini

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  GEMINI_BIN=${NPM_GLOBAL_BIN}/gemini"
echo_info "  GEMINI_API_KEY=<your-api-key>"
echo_info ""
echo_info "Add to ~/.bashrc or ~/.profile:"
echo_info "  export PATH=\"${NPM_GLOBAL_BIN}:\$PATH\""
echo_info "  export GEMINI_API_KEY=\"your-api-key-here\""
echo_info ""
echo_info "Basic usage:"
echo_info "  gemini                 # interactive mode"
echo_info "  gemini --version       # show version"
echo_success "Log saved to: $LOG_PATH"

# EOF
