#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_shell_formatter_linter.sh
#
# PURPOSE
# -------
# Install shell script formatters and linters: shellcheck and shfmt.
# Uses apt where available; falls back to pre-built binaries from GitHub
# releases. Binaries are placed in /usr/local/bin.
#
# USAGE
# -----
#   sudo ./install_shell_formatter_linter.sh
#   sudo ./install_shell_formatter_linter.sh --check   # verify without installing

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

SHELLCHECK_VERSION="v0.10.0"
SHFMT_VERSION="v3.8.0"
INSTALL_DIR="/usr/local/bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

install_shellcheck() {
    echo_info "Installing shellcheck ${SHELLCHECK_VERSION}..."

    if command -v apt-get &>/dev/null; then
        apt-get install -y shellcheck 2>&1 | tee -a "$LOG_PATH"
    else
        echo_warning "apt-get not found — installing shellcheck from GitHub releases..."
        local arch
        arch="$(uname -m)"
        local tmp_dir
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "$tmp_dir"' RETURN

        wget -q \
            "https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION}/shellcheck-${SHELLCHECK_VERSION}.linux.${arch}.tar.xz" \
            -O "${tmp_dir}/shellcheck.tar.xz" 2>&1 | tee -a "$LOG_PATH"
        tar -xf "${tmp_dir}/shellcheck.tar.xz" -C "${tmp_dir}"
        cp "${tmp_dir}/shellcheck-${SHELLCHECK_VERSION}/shellcheck" "${INSTALL_DIR}/shellcheck"
        chmod +x "${INSTALL_DIR}/shellcheck"
    fi

    if command -v shellcheck &>/dev/null; then
        echo_success "shellcheck installed: $(shellcheck --version 2>&1 | head -2 | tail -1)"
    else
        echo_warning "shellcheck installation may have failed — check PATH."
        return 1
    fi
}

install_shfmt() {
    echo_info "Installing shfmt ${SHFMT_VERSION}..."

    local arch
    arch="$(uname -m)"
    local os
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"

    # Normalise arch for shfmt release naming
    case "$arch" in
    x86_64) arch="amd64" ;;
    aarch64 | arm64) arch="arm64" ;;
    esac

    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN

    wget -q \
        "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_${os}_${arch}" \
        -O "${tmp_dir}/shfmt" 2>&1 | tee -a "$LOG_PATH"
    cp "${tmp_dir}/shfmt" "${INSTALL_DIR}/shfmt"
    chmod +x "${INSTALL_DIR}/shfmt"

    if command -v shfmt &>/dev/null; then
        echo_success "shfmt installed: $(shfmt --version 2>&1)"
    else
        echo_warning "shfmt installation may have failed — check PATH."
        return 1
    fi
}

verify_shell_tools() {
    echo_info "Verifying shell formatter/linter tools..."
    local failed=0

    declare -A TOOL_CMDS=(
        [shellcheck]="shellcheck --version"
        [shfmt]="shfmt --version"
    )

    for tool in "${!TOOL_CMDS[@]}"; do
        if command -v "$tool" &>/dev/null; then
            version_line="$(${TOOL_CMDS[$tool]} 2>&1 | head -1)"
            echo_success "  $tool: $version_line"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done

    if [[ $failed -eq 0 ]]; then
        echo_success "All shell formatter/linter tools verified."
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
echo_info "Shell Formatter/Linter Installation Script"
echo_info "=========================================="
echo_info "  shellcheck: ${SHELLCHECK_VERSION}"
echo_info "  shfmt:      ${SHFMT_VERSION}"

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_shell_tools
    exit $?
fi

check_root

# Idempotency check
if command -v shellcheck &>/dev/null; then
    echo_warning "shellcheck already installed: $(shellcheck --version 2>&1 | head -2 | tail -1)"
fi
if command -v shfmt &>/dev/null; then
    echo_warning "shfmt already installed: $(shfmt --version 2>&1)"
fi
echo_info "Re-installing is idempotent — binaries will be overwritten."

apt-get update -qq 2>&1 | tee -a "$LOG_PATH"
apt-get install -y wget 2>&1 | tee -a "$LOG_PATH"

install_shellcheck
install_shfmt
verify_shell_tools

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  (No special env vars required — binaries are in ${INSTALL_DIR})"
echo_info ""
echo_info "Usage examples:"
echo_info "  Lint script:    shellcheck script.sh"
echo_info "  Lint all:       shellcheck \$(find . -name '*.sh')"
echo_info "  Format script:  shfmt -w -i 4 script.sh"
echo_info "  Format all:     shfmt -w -i 4 -l ."
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind ${INSTALL_DIR}/shellcheck:${INSTALL_DIR}/shellcheck:ro"
echo_info "  --bind ${INSTALL_DIR}/shfmt:${INSTALL_DIR}/shfmt:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
