#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_tree.sh
#
# PURPOSE
# -------
# Install the tree command on the host. Tries apt first; falls back to
# building from source if apt is unavailable or produces an old version.
#
# USAGE
# -----
#   sudo ./install_tree.sh
#   ./install_tree.sh --source          # force build from source
#   ./install_tree.sh --check           # verify without installing

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

TREE_VERSION="2.1.3"
BUILD_DIR="${HOME}/.cache/build/tree"
INSTALL_PREFIX="${HOME}/.local"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root (for apt install)."
    fi
}

verify_tree() {
    echo_info "Verifying tree installation..."
    if command -v tree &>/dev/null; then
        version="$(tree --version 2>&1 | head -1)"
        echo_success "  tree: $version"
    else
        echo_warning "  tree: NOT FOUND"
        return 1
    fi
    echo_success "tree verified."
}

install_from_apt() {
    check_root
    echo_info "Updating apt cache..."
    apt-get update -qq 2>&1 | tee -a "$LOG_PATH"
    echo_info "Installing tree via apt..."
    apt-get install -y --no-install-recommends tree 2>&1 | tee -a "$LOG_PATH"
}

install_from_source() {
    echo_info "Building tree ${TREE_VERSION} from source..."
    mkdir -p "$BUILD_DIR"
    mkdir -p "$INSTALL_PREFIX/bin"
    mkdir -p "$INSTALL_PREFIX/share/man/man1"

    ARCHIVE="$BUILD_DIR/tree-${TREE_VERSION}.tgz"
    if [[ ! -f "$ARCHIVE" ]]; then
        echo_info "Downloading tree ${TREE_VERSION}..."
        wget -q \
            "https://gitlab.com/OldManProgrammer/unix-tree/-/archive/${TREE_VERSION}/unix-tree-${TREE_VERSION}.tar.gz" \
            -O "$ARCHIVE" 2>&1 | tee -a "$LOG_PATH"
    else
        echo_info "Archive already cached at $ARCHIVE — skipping download."
    fi

    tar -xzf "$ARCHIVE" -C "$BUILD_DIR" 2>&1 | tee -a "$LOG_PATH"
    cd "$BUILD_DIR/unix-tree-${TREE_VERSION}"

    make PREFIX="$INSTALL_PREFIX" 2>&1 | tee -a "$LOG_PATH"
    make PREFIX="$INSTALL_PREFIX" install 2>&1 | tee -a "$LOG_PATH"

    cd "$THIS_DIR"
    echo_success "tree ${TREE_VERSION} built and installed to ${INSTALL_PREFIX}/bin/tree"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECK_ONLY=false
FROM_SOURCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --check)
        CHECK_ONLY=true
        shift
        ;;
    --source)
        FROM_SOURCE=true
        shift
        ;;
    -h | --help)
        echo "Usage: [sudo] $0 [--check] [--source]"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "tree Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_tree
    exit $?
fi

# Check if already installed (idempotent)
if command -v tree &>/dev/null; then
    CURRENT_VERSION="$(tree --version 2>&1 | head -1)"
    echo_warning "tree already installed: $CURRENT_VERSION"
    echo_info "Re-running installation is idempotent — continuing."
fi

if [[ "$FROM_SOURCE" == true ]]; then
    install_from_source
elif command -v apt-get &>/dev/null && [[ "${EUID}" -eq 0 ]]; then
    install_from_apt
else
    echo_info "apt not available or not running as root — building from source."
    install_from_source
fi

verify_tree

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  TREE_BIN=$(command -v tree 2>/dev/null || echo "${INSTALL_PREFIX}/bin/tree")"
echo_info ""
echo_info "If installed from source, ensure ${INSTALL_PREFIX}/bin is on your PATH:"
echo_info "  export PATH=\"${INSTALL_PREFIX}/bin:\$PATH\""
echo_success "Log saved to: $LOG_PATH"

# EOF
