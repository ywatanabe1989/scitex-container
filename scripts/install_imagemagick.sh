#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_imagemagick.sh
#
# PURPOSE
# -------
# Install ImageMagick on the host and patch its PDF security policy.
# The binary is bind-mounted into Apptainer/Docker containers at runtime.
#
# USAGE
# -----
#   sudo ./install_imagemagick.sh
#   sudo ./install_imagemagick.sh --check   # verify without installing

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

fix_imagemagick_pdf_policy() {
    # ImageMagick ships with a restrictive policy that blocks PDF conversion.
    # Patch it to allow read|write, matching what the production Dockerfile does.
    local policy_file="/etc/ImageMagick-6/policy.xml"

    if [[ ! -f "${policy_file}" ]]; then
        echo_warning "Policy file not found at ${policy_file} — skipping PDF policy fix."
        return 0
    fi

    if grep -q 'rights="read|write" pattern="PDF"' "${policy_file}"; then
        echo_info "ImageMagick PDF policy already allows read|write — no change needed."
        return 0
    fi

    echo_info "Patching ImageMagick policy.xml to allow PDF read|write..."
    sed -i \
        's|<policy domain="coder" rights="none" pattern="PDF" />|<policy domain="coder" rights="read|write" pattern="PDF" />|g' \
        "${policy_file}"

    if grep -q 'rights="read|write" pattern="PDF"' "${policy_file}"; then
        echo_success "ImageMagick PDF policy patched."
    else
        echo_warning "Patch ran but expected pattern not found. Inspect: ${policy_file}"
    fi
}

verify_imagemagick() {
    echo_info "Verifying ImageMagick tools..."
    local failed=0
    for tool in convert identify mogrify; do
        if command -v "$tool" &>/dev/null; then
            version="$("$tool" --version 2>&1 | head -1)"
            echo_success "  $tool: $version"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done
    if [[ $failed -eq 0 ]]; then
        echo_success "All ImageMagick tools verified."
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
echo_info "ImageMagick Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_imagemagick
    exit $?
fi

check_root

# Check if already installed (idempotent — apt handles it)
if command -v convert &>/dev/null; then
    CURRENT_VERSION="$(convert --version 2>&1 | head -1)"
    echo_warning "ImageMagick already installed: $CURRENT_VERSION"
    echo_info "Re-running apt install is idempotent — continuing."
fi

echo_info "Updating apt cache..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing ImageMagick..."
apt-get install -y --no-install-recommends imagemagick 2>&1 | tee -a "$LOG_PATH"

fix_imagemagick_pdf_policy

verify_imagemagick

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  HOST_IMAGEMAGICK_BIN=/usr/bin/convert"
echo_info "  HOST_IMAGEMAGICK_POLICY=/etc/ImageMagick-6/policy.xml"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind /usr/bin/convert:/usr/bin/convert:ro"
echo_info "  --bind /etc/ImageMagick-6:/etc/ImageMagick-6:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
