#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_python.sh
#
# PURPOSE
# -------
# Build and install Python from source with --enable-optimizations and a
# bundled OpenSSL. Installs to /usr/local so it is available system-wide and
# can be bind-mounted into Apptainer/Docker containers.
#
# USAGE
# -----
#   sudo ./install_python.sh
#   sudo ./install_python.sh --check               # verify without installing
#   sudo ./install_python.sh --python-version 3.12.9

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

DEFAULT_PYTHON_VERSION="3.11.11"
DEFAULT_OPENSSL_VERSION="1.1.1w"
INSTALL_PREFIX="/usr/local"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

install_build_deps() {
    echo_info "Installing build dependencies..."
    apt-get install -y \
        build-essential \
        libbz2-dev \
        libffi-dev \
        libgdbm-dev \
        liblzma-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        tk-dev \
        uuid-dev \
        wget \
        zlib1g-dev \
        2>&1 | tee -a "$LOG_PATH"
}

install_openssl() {
    local openssl_version="$1"
    local prefix="$2"

    echo_info "Building OpenSSL ${openssl_version}..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN

    wget -q "https://www.openssl.org/source/openssl-${openssl_version}.tar.gz" \
        -O "${tmp_dir}/openssl-${openssl_version}.tar.gz" 2>&1 | tee -a "$LOG_PATH"
    tar -xzf "${tmp_dir}/openssl-${openssl_version}.tar.gz" -C "${tmp_dir}"

    cd "${tmp_dir}/openssl-${openssl_version}"
    ./config --prefix="${prefix}" --openssldir="${prefix}/openssl" 2>&1 | tee -a "$LOG_PATH"
    make -j"$(nproc)" 2>&1 | tee -a "$LOG_PATH"
    make install 2>&1 | tee -a "$LOG_PATH"
    cd /
    echo_success "OpenSSL ${openssl_version} installed."
}

build_python() {
    local python_version="$1"
    local prefix="$2"
    local major_minor="${python_version%.*}"

    echo_info "Building Python ${python_version} with --enable-optimizations..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN

    wget -q "https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tgz" \
        -O "${tmp_dir}/Python-${python_version}.tgz" 2>&1 | tee -a "$LOG_PATH"
    tar -xzf "${tmp_dir}/Python-${python_version}.tgz" -C "${tmp_dir}"

    cd "${tmp_dir}/Python-${python_version}"
    ./configure \
        --enable-optimizations \
        --prefix="${prefix}" \
        --with-openssl="${prefix}" \
        --with-openssl-rpath=auto \
        2>&1 | tee -a "$LOG_PATH"

    make -j"$(nproc)" 2>&1 | tee -a "$LOG_PATH"
    make altinstall 2>&1 | tee -a "$LOG_PATH"

    # Create stable symlinks
    ln -sf "${prefix}/bin/python${major_minor}" "${prefix}/bin/python3" || true
    ln -sf "${prefix}/bin/python${major_minor}" "${prefix}/bin/python" || true
    ln -sf "${prefix}/bin/pip${major_minor}" "${prefix}/bin/pip3" || true
    ln -sf "${prefix}/bin/pip${major_minor}" "${prefix}/bin/pip" || true

    cd /
    echo_success "Python ${python_version} installed."
}

verify_python() {
    echo_info "Verifying Python installation..."
    local failed=0

    for tool in python3 python; do
        if command -v "$tool" &>/dev/null; then
            echo_success "  $tool: $("$tool" --version 2>&1)"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done

    if python3 -c "import ssl; print('  ssl:', ssl.OPENSSL_VERSION)" 2>/dev/null; then
        echo_success "  ssl module: OK"
    else
        echo_warning "  ssl module: NOT AVAILABLE"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "Python verified."
    else
        echo_warning "$failed check(s) failed."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECK_ONLY=false
PYTHON_VERSION="${DEFAULT_PYTHON_VERSION}"
OPENSSL_VERSION="${DEFAULT_OPENSSL_VERSION}"

while [[ $# -gt 0 ]]; do
    case "$1" in
    --check)
        CHECK_ONLY=true
        shift
        ;;
    --python-version)
        PYTHON_VERSION="$2"
        shift 2
        ;;
    --openssl-version)
        OPENSSL_VERSION="$2"
        shift 2
        ;;
    -h | --help)
        echo "Usage: sudo $0 [--check] [--python-version X.Y.Z] [--openssl-version X.Y.Z]"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "Python from Source Installation Script"
echo_info "=========================================="
echo_info "  Python version:  ${PYTHON_VERSION}"
echo_info "  OpenSSL version: ${OPENSSL_VERSION}"
echo_info "  Prefix:          ${INSTALL_PREFIX}"

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_python
    exit $?
fi

check_root

# Idempotency check
if command -v python3 &>/dev/null; then
    CURRENT_VERSION="$(python3 --version 2>&1)"
    echo_warning "python3 already installed: $CURRENT_VERSION"
    echo_info "Rebuilding from source — this is idempotent."
fi

apt-get update -qq 2>&1 | tee -a "$LOG_PATH"
install_build_deps
install_openssl "${OPENSSL_VERSION}" "${INSTALL_PREFIX}"
build_python "${PYTHON_VERSION}" "${INSTALL_PREFIX}"
verify_python

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  PYTHON=${INSTALL_PREFIX}/bin/python3"
echo_info "  PATH=${INSTALL_PREFIX}/bin:\$PATH"
echo_info "  LD_LIBRARY_PATH=${INSTALL_PREFIX}/lib:\$LD_LIBRARY_PATH"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind ${INSTALL_PREFIX}/bin/python3:${INSTALL_PREFIX}/bin/python3:ro"
echo_info "  --bind ${INSTALL_PREFIX}/lib/python${PYTHON_VERSION%.*}:${INSTALL_PREFIX}/lib/python${PYTHON_VERSION%.*}:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
