#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_google_chrome.sh
#
# PURPOSE
# -------
# Install Google Chrome on the host for headless rendering (puppeteer/mermaid).
# These tools are bind-mounted into Apptainer/Docker containers at runtime
# instead of baking them into images.
#
# USAGE
# -----
#   sudo ./install_google_chrome.sh
#   ./install_google_chrome.sh --check   # verify without installing

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

verify_google_chrome() {
    echo_info "Verifying Google Chrome installation..."
    if command -v google-chrome &>/dev/null; then
        version="$(google-chrome --version 2>&1 | head -1)"
        echo_success "  google-chrome: $version"
    else
        echo_warning "  google-chrome: NOT FOUND"
        return 1
    fi
    echo_success "Google Chrome verified."
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
echo_info "Google Chrome Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_google_chrome
    exit $?
fi

check_root

# Check if already installed (idempotent)
if command -v google-chrome &>/dev/null; then
    CURRENT_VERSION="$(google-chrome --version 2>&1 | head -1)"
    echo_warning "google-chrome already installed: $CURRENT_VERSION"
    echo_info "Re-running installation is idempotent — continuing."
fi

echo_info "Updating apt cache..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing dependencies..."
apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    apt-transport-https \
    2>&1 | tee -a "$LOG_PATH"

echo_info "Adding Google Chrome apt repository..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub |
    gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg 2>&1 | tee -a "$LOG_PATH"

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
https://dl.google.com/linux/chrome/deb/ stable main" \
    >/etc/apt/sources.list.d/google-chrome.list

echo_info "Updating apt cache with Chrome repository..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing Google Chrome..."
apt-get install -y --no-install-recommends google-chrome-stable 2>&1 | tee -a "$LOG_PATH"

verify_google_chrome

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  CHROME_BIN=/usr/bin/google-chrome"
echo_info "  PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind /usr/bin/google-chrome:/usr/bin/google-chrome:ro"
echo_info "  --bind /opt/google/chrome:/opt/google/chrome:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
