#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_nvidia_driver.sh
#
# PURPOSE
# -------
# Install NVIDIA drivers on the host (Ubuntu/Debian).
# Containers access the host GPU via bind-mounted driver libraries at runtime.
#
# USAGE
# -----
#   sudo ./install_nvidia_driver.sh
#   sudo ./install_nvidia_driver.sh --check   # verify without installing

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

verify_nvidia_driver() {
    echo_info "Verifying NVIDIA driver installation..."
    local failed=0
    for tool in nvidia-smi nvidia-modprobe; do
        if command -v "$tool" &>/dev/null; then
            version="$("$tool" --version 2>&1 | head -1)"
            echo_success "  $tool: $version"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done
    if [[ $failed -eq 0 ]]; then
        echo_success "All NVIDIA tools verified."
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
echo_info "NVIDIA Driver Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_nvidia_driver
    exit $?
fi

check_root

# Detect GPU
if ! lspci 2>/dev/null | grep -qi nvidia; then
    echo_warning "No NVIDIA GPU detected via lspci. Proceeding anyway."
fi

# Check if already installed (idempotent)
if command -v nvidia-smi &>/dev/null; then
    CURRENT_VERSION="$(nvidia-smi --version 2>&1 | head -1)"
    echo_warning "nvidia-smi already installed: $CURRENT_VERSION"
    echo_info "Re-running installation is idempotent — continuing."
fi

echo_info "Updating apt cache..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing dependencies..."
apt-get install -y --no-install-recommends \
    software-properties-common \
    pciutils \
    2>&1 | tee -a "$LOG_PATH"

echo_info "Adding graphics-drivers PPA..."
add-apt-repository -y ppa:graphics-drivers/ppa 2>&1 | tee -a "$LOG_PATH"

echo_info "Updating apt cache with PPA..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing recommended NVIDIA driver..."
# ubuntu-drivers detects the best driver automatically
if command -v ubuntu-drivers &>/dev/null; then
    ubuntu-drivers autoinstall 2>&1 | tee -a "$LOG_PATH"
else
    apt-get install -y --no-install-recommends ubuntu-drivers-common 2>&1 | tee -a "$LOG_PATH"
    ubuntu-drivers autoinstall 2>&1 | tee -a "$LOG_PATH"
fi

verify_nvidia_driver

echo_info ""
echo_info "NOTE: A reboot is required to load the new kernel module."
echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  NVIDIA_DRIVER_PATH=/usr/lib/x86_64-linux-gnu"
echo_info ""
echo_info "Apptainer bind flags (set automatically with --nv):"
echo_info "  apptainer exec --nv <image.sif> ..."
echo_info "  # or manually: --bind /usr/lib/x86_64-linux-gnu/libcuda.so.1:..."
echo_success "Log saved to: $LOG_PATH"

# EOF
