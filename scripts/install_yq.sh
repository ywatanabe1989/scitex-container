#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_yq.sh
#
# PURPOSE
# -------
# Install yq (YAML processor) on the host. Used for parsing and editing
# container definition files and configuration YAMLs.
#
# USAGE
# -----
#   ./install_yq.sh
#   ./install_yq.sh --check   # verify without installing

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

YQ_VERSION="v4.40.5"
INSTALL_DIR="${HOME}/.local/bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

verify_yq() {
    echo_info "Verifying yq installation..."
    if command -v yq &>/dev/null; then
        version="$(yq --version 2>&1 | head -1)"
        echo_success "  yq: $version"
    else
        echo_warning "  yq: NOT FOUND"
        return 1
    fi
    echo_success "yq verified."
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
echo_info "yq Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_yq
    exit $?
fi

# Check if already installed (idempotent)
if command -v yq &>/dev/null; then
    CURRENT_VERSION="$(yq --version 2>&1 | head -1)"
    echo_warning "yq already installed: $CURRENT_VERSION"
    echo_info "Re-downloading will overwrite with version ${YQ_VERSION} — continuing."
fi

echo_info "Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo_info "Downloading yq ${YQ_VERSION}..."
curl -fsSL \
    "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    -o "$INSTALL_DIR/yq" 2>&1 | tee -a "$LOG_PATH"

chmod +x "$INSTALL_DIR/yq"
echo_success "yq ${YQ_VERSION} installed to ${INSTALL_DIR}/yq"

verify_yq

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  YQ_BIN=${INSTALL_DIR}/yq"
echo_info ""
echo_info "Ensure ${INSTALL_DIR} is on your PATH:"
echo_info "  export PATH=\"${INSTALL_DIR}:\$PATH\""
echo_success "Log saved to: $LOG_PATH"

# EOF
