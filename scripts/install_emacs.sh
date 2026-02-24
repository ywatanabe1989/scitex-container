#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_emacs.sh
#
# PURPOSE
# -------
# Install Emacs from source on the host with a full feature set including
# tree-sitter, JSON, and ImageMagick support.
#
# USAGE
# -----
#   sudo ./install_emacs.sh
#   sudo ./install_emacs.sh --version 29.4 --threads 8
#   ./install_emacs.sh --check   # verify without installing

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

EMACS_VERSION="29.4"
THREADS="$(nproc 2>/dev/null || echo 4)"
INSTALL_PREFIX="/opt/emacs-${EMACS_VERSION}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

verify_emacs() {
    echo_info "Verifying Emacs installation..."
    if command -v emacs &>/dev/null; then
        version="$(emacs --version 2>&1 | head -1)"
        echo_success "  emacs: $version"
    else
        echo_warning "  emacs: NOT FOUND"
        return 1
    fi
    echo_success "Emacs verified."
}

install_dependencies() {
    echo_info "Installing build dependencies..."
    apt-get install -y --no-install-recommends \
        autoconf \
        make \
        gcc \
        gcc-12 \
        texinfo \
        libgtk-3-dev \
        libxpm-dev \
        libjpeg-dev \
        libgif-dev \
        libtiff5-dev \
        libgnutls28-dev \
        libncurses5-dev \
        libjansson-dev \
        libjansson4 \
        libharfbuzz-dev \
        libharfbuzz-bin \
        imagemagick \
        libmagickwand-dev \
        libgccjit0 \
        libgccjit-12-dev \
        xaw3dg-dev \
        libx11-dev \
        libtree-sitter0 \
        libtree-sitter-dev \
        libwebkit2gtk-4.0-dev \
        libacl1 \
        libacl1-dev \
        w3m \
        wget \
        2>&1 | tee -a "$LOG_PATH"
    export LIBRARY_PATH="/usr/lib/gcc/x86_64-linux-gnu/12:${LIBRARY_PATH:-}"
}

setup_locale() {
    echo_info "Setting up locale..."
    locale-gen en_US.UTF-8 2>&1 | tee -a "$LOG_PATH"
    echo "LANG=en_US.UTF-8" >/etc/default/locale
    echo "LC_ALL=en_US.UTF-8" >>/etc/default/locale
}

download_source() {
    echo_info "Downloading Emacs ${EMACS_VERSION} source..."
    ARCHIVE="/tmp/emacs-${EMACS_VERSION}.tar.xz"
    if [[ ! -f "$ARCHIVE" ]]; then
        wget -q "https://ftp.gnu.org/gnu/emacs/emacs-${EMACS_VERSION}.tar.xz" \
            -O "$ARCHIVE" 2>&1 | tee -a "$LOG_PATH"
    else
        echo_info "Archive already cached at $ARCHIVE — skipping download."
    fi
    tar -xf "$ARCHIVE" -C /tmp 2>&1 | tee -a "$LOG_PATH"
    rm -rf "${INSTALL_PREFIX}"
}

compile_emacs() {
    echo_info "Configuring Emacs ${EMACS_VERSION}..."
    cd "/tmp/emacs-${EMACS_VERSION}"
    ./configure \
        --prefix="${INSTALL_PREFIX}" \
        --without-native-compilation \
        --with-json \
        --with-modules \
        --with-harfbuzz \
        --with-compress-install \
        --with-threads \
        --with-included-regex \
        --with-zlib \
        --with-jpeg \
        --with-png \
        --with-imagemagick \
        --with-tiff \
        --with-xpm \
        --with-gnutls \
        --with-xft \
        --with-xml2 \
        --with-mailutils \
        --with-tree-sitter \
        2>&1 | tee -a "$LOG_PATH"

    echo_info "Compiling Emacs with ${THREADS} threads..."
    make -j "${THREADS}" 2>&1 | tee -a "$LOG_PATH"
    make install -j "${THREADS}" 2>&1 | tee -a "$LOG_PATH"
    cd "$THIS_DIR"
}

setup_links() {
    echo_info "Setting up symbolic link: /usr/bin/emacs -> ${INSTALL_PREFIX}/bin/emacs"
    ln -sf "${INSTALL_PREFIX}/bin/emacs" /usr/bin/emacs
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
    -v | --version)
        EMACS_VERSION="$2"
        INSTALL_PREFIX="/opt/emacs-${EMACS_VERSION}"
        shift 2
        ;;
    -t | --threads)
        THREADS="$2"
        shift 2
        ;;
    -h | --help)
        echo "Usage: sudo $0 [--check] [--version VERSION] [--threads N]"
        echo ""
        echo "Options:"
        echo "  --version VERSION    Emacs version to install (default: ${EMACS_VERSION})"
        echo "  --threads N          Compile threads (default: nproc)"
        echo "  --check              Verify installation without installing"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "Emacs Installation Script (from source)"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_emacs
    exit $?
fi

check_root

# Check if already installed (idempotent)
if command -v emacs &>/dev/null; then
    CURRENT_VERSION="$(emacs --version 2>&1 | head -1)"
    echo_warning "emacs already installed: $CURRENT_VERSION"
    echo_info "Re-building will overwrite ${INSTALL_PREFIX} — continuing."
fi

echo_info "Updating apt cache..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

setup_locale
install_dependencies
download_source
compile_emacs
setup_links

verify_emacs

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  EMACS_VERSION=${EMACS_VERSION}"
echo_info "  EMACS_PREFIX=${INSTALL_PREFIX}"
echo_info "  EMACS_BIN=${INSTALL_PREFIX}/bin/emacs"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind ${INSTALL_PREFIX}:${INSTALL_PREFIX}:ro"
echo_info "  --bind /usr/bin/emacs:/usr/bin/emacs:ro"
echo_success "Emacs ${EMACS_VERSION} installed to ${INSTALL_PREFIX}"
echo_success "Log saved to: $LOG_PATH"

# EOF
