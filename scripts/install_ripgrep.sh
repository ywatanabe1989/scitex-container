#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_ripgrep.sh
#
# PURPOSE
# -------
# Install ripgrep (rg) from the pre-built GitHub release binary. The binary
# is placed at /usr/local/bin/rg and can be bind-mounted into containers.
#
# USAGE
# -----
#   sudo ./install_ripgrep.sh
#   sudo ./install_ripgrep.sh --check   # verify without installing

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

RG_VERSION="14.1.1"
INSTALL_DIR="/usr/local/bin"
RG_TARBALL="ripgrep-${RG_VERSION}-x86_64-unknown-linux-musl.tar.gz"
RG_URL="https://github.com/BurntSushi/ripgrep/releases/download/${RG_VERSION}/${RG_TARBALL}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

install_ripgrep() {
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT

    echo_info "Downloading ripgrep v${RG_VERSION}..."
    wget -q "${RG_URL}" -O "${tmp_dir}/${RG_TARBALL}" 2>&1 | tee -a "$LOG_PATH"

    echo_info "Extracting..."
    tar -xzf "${tmp_dir}/${RG_TARBALL}" -C "${tmp_dir}"

    echo_info "Installing rg to ${INSTALL_DIR}..."
    cp "${tmp_dir}/ripgrep-${RG_VERSION}-x86_64-unknown-linux-musl/rg" "${INSTALL_DIR}/rg"
    chmod +x "${INSTALL_DIR}/rg"
}

verify_ripgrep() {
    echo_info "Verifying ripgrep installation..."
    local failed=0

    if command -v rg &>/dev/null; then
        echo_success "  rg: $(rg --version 2>&1 | head -1)"
    else
        echo_warning "  rg: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "ripgrep verified."
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
echo_info "ripgrep Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_ripgrep
    exit $?
fi

check_root

# Idempotency check
if command -v rg &>/dev/null; then
    CURRENT_VERSION="$(rg --version 2>&1 | head -1)"
    echo_warning "rg already installed: $CURRENT_VERSION"
    echo_info "Overwriting with v${RG_VERSION} — this is idempotent."
fi

echo_info "Installing wget if not present..."
apt-get install -y wget 2>&1 | tee -a "$LOG_PATH"

install_ripgrep
verify_ripgrep

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  RIPGREP_CONFIG_PATH=\$HOME/.ripgreprc"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind ${INSTALL_DIR}/rg:${INSTALL_DIR}/rg:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
