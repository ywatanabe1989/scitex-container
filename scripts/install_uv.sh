#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_uv.sh
#
# PURPOSE
# -------
# Install uv (Rust-based Python package manager) via the official installer
# script. uv is installed per-user into ~/.local/bin and can be bind-mounted
# into Apptainer/Docker containers.
#
# USAGE
# -----
#   ./install_uv.sh
#   ./install_uv.sh --check   # verify without installing
#   (Does NOT require root — installs to ~/.local/bin)

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

install_uv() {
    echo_info "Downloading and running the official uv installer..."
    curl -LsSf https://astral.sh/uv/install.sh 2>&1 | sh 2>&1 | tee -a "$LOG_PATH"

    # Ensure ~/.local/bin is on PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
}

verify_uv() {
    echo_info "Verifying uv installation..."
    local failed=0

    # uv may land in ~/.local/bin or ~/.cargo/bin depending on version
    if command -v uv &>/dev/null || [[ -x "$HOME/.local/bin/uv" ]]; then
        local uv_bin
        uv_bin="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
        echo_success "  uv: $("${uv_bin}" --version 2>&1)"
    else
        echo_warning "  uv: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "uv verified."
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
        echo "Usage: $0 [--check]"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "uv Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_uv
    exit $?
fi

# Idempotency check
if command -v uv &>/dev/null; then
    CURRENT_VERSION="$(uv --version 2>&1)"
    echo_warning "uv already installed: $CURRENT_VERSION"
    echo_info "Re-running installer updates uv to the latest release — continuing."
fi

install_uv
verify_uv

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  UV_CACHE_DIR=\$HOME/.cache/uv"
echo_info "  UV_PYTHON=python3.11"
echo_info ""
echo_info "Add to ~/.bashrc:"
echo_info "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind \$HOME/.local/bin/uv:\$HOME/.local/bin/uv:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
