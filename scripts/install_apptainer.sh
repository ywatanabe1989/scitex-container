#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_apptainer.sh
#
# PURPOSE
# -------
# Install Apptainer (formerly Singularity) on the host by downloading the
# official .deb package from GitHub releases. Apptainer is used to run
# SciTeX container images without requiring Docker.
#
# USAGE
# -----
#   sudo ./install_apptainer.sh
#   sudo ./install_apptainer.sh --check   # verify without installing

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
# Version pin
# ---------------------------------------------------------------------------

VERSION="1.3.6"
DEB_FILE="apptainer_${VERSION}_amd64.deb"
DEB_URL="https://github.com/apptainer/apptainer/releases/download/v${VERSION}/${DEB_FILE}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

verify_apptainer() {
    echo_info "Verifying Apptainer installation..."
    local failed=0
    if command -v apptainer &>/dev/null; then
        local version
        version="$(apptainer --version 2>&1)"
        echo_success "  apptainer: $version"
    else
        echo_warning "  apptainer: NOT FOUND"
        ((failed++)) || true
    fi
    if [[ $failed -eq 0 ]]; then
        echo_success "Apptainer verified."
    else
        echo_warning "Apptainer not found."
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
echo_info "Apptainer Installation Script (v${VERSION})"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_apptainer
    exit $?
fi

check_root

# Idempotency check
if command -v apptainer &>/dev/null; then
    CURRENT_VERSION="$(apptainer --version 2>&1)"
    echo_warning "Apptainer already installed: $CURRENT_VERSION"
    echo_info "Proceeding with reinstall to ensure version ${VERSION} — continuing."
fi

TMP_DIR="$(mktemp -d)"

echo_info "Downloading Apptainer ${VERSION} from GitHub releases..."
curl -fsSL "${DEB_URL}" -o "${TMP_DIR}/${DEB_FILE}" 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing .deb package..."
dpkg -i "${TMP_DIR}/${DEB_FILE}" 2>&1 | tee -a "$LOG_PATH"

echo_info "Fixing any unmet dependencies..."
apt-get install -f -y 2>&1 | tee -a "$LOG_PATH"

# Cleanup temp directory
rm -f "${TMP_DIR}/${DEB_FILE}"
rmdir "${TMP_DIR}" 2>/dev/null || true

verify_apptainer

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  APPTAINER_BIN=/usr/bin/apptainer"
echo_info "  APPTAINER_CACHEDIR=\$HOME/.apptainer/cache"
echo_info ""
echo_info "Basic usage:"
echo_info "  apptainer run <image.sif> <command>"
echo_info "  apptainer exec --bind /data:/data <image.sif> <command>"
echo_success "Log saved to: $LOG_PATH"

# EOF
