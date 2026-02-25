#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_rust.sh
#
# PURPOSE
# -------
# Install the Rust toolchain (rustc, cargo, rustup) via the official rustup
# installer. Installs per-user into ~/.cargo and can be bind-mounted into
# Apptainer/Docker containers.
#
# USAGE
# -----
#   ./install_rust.sh
#   ./install_rust.sh --check   # verify without installing
#   (Does NOT require root — installs to ~/.cargo)

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

install_rust() {
    echo_info "Running rustup installer (non-interactive)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs 2>&1 |
        sh -s -- -y --no-modify-path 2>&1 | tee -a "$LOG_PATH"

    # Source Rust environment for this session
    # shellcheck source=/dev/null
    source "$HOME/.cargo/env" || export PATH="$HOME/.cargo/bin:$PATH"
}

verify_rust() {
    echo_info "Verifying Rust toolchain..."
    local failed=0

    # Ensure .cargo/bin is on PATH
    export PATH="$HOME/.cargo/bin:$PATH"

    for tool in rustc cargo rustup; do
        if command -v "$tool" &>/dev/null; then
            echo_success "  $tool: $("$tool" --version 2>&1)"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done

    if [[ $failed -eq 0 ]]; then
        echo_success "Rust toolchain verified."
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
echo_info "Rust Toolchain Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_rust
    exit $?
fi

# Idempotency check — rustup self update if already present
if command -v rustup &>/dev/null || [[ -x "$HOME/.cargo/bin/rustup" ]]; then
    export PATH="$HOME/.cargo/bin:$PATH"
    CURRENT_VERSION="$(rustc --version 2>&1)"
    echo_warning "Rust already installed: $CURRENT_VERSION"
    echo_info "Running rustup self update — this is idempotent."
    rustup self update 2>&1 | tee -a "$LOG_PATH" || true
    rustup update stable 2>&1 | tee -a "$LOG_PATH"
else
    install_rust
fi

verify_rust

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  CARGO_HOME=\$HOME/.cargo"
echo_info "  RUSTUP_HOME=\$HOME/.rustup"
echo_info "  PATH=\$HOME/.cargo/bin:\$PATH"
echo_info ""
echo_info "Add to ~/.bashrc:"
echo_info "  source \"\$HOME/.cargo/env\""
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind \$HOME/.cargo:\$HOME/.cargo:ro"
echo_info "  --bind \$HOME/.rustup:\$HOME/.rustup:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
