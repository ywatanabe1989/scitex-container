#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_texlive.sh
#
# PURPOSE
# -------
# Install TeXLive packages on the host. These are bind-mounted into Apptainer/
# Docker containers at runtime instead of baking them into images.
#
# USAGE
# -----
#   sudo ./install_texlive.sh
#   sudo ./install_texlive.sh --check   # verify without installing

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
# Packages
# ---------------------------------------------------------------------------

TEXLIVE_PACKAGES=(
    texlive-latex-base
    texlive-latex-extra
    texlive-latex-recommended
    texlive-fonts-recommended
    texlive-fonts-extra
    texlive-bibtex-extra
    texlive-science
    texlive-pictures
    texlive-plain-generic
    latexdiff
    latexmk
    ghostscript
    poppler-utils
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo_error "ERROR: This script must be run with sudo or as root."
    fi
}

verify_texlive() {
    echo_info "Verifying TeXLive tools..."
    local failed=0
    for tool in pdflatex bibtex latexmk latexdiff gs pdfinfo; do
        if command -v "$tool" &>/dev/null; then
            version="$("$tool" --version 2>&1 | head -1)"
            echo_success "  $tool: $version"
        else
            echo_warning "  $tool: NOT FOUND"
            ((failed++)) || true
        fi
    done
    if [[ $failed -eq 0 ]]; then
        echo_success "All TeXLive tools verified."
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
echo_info "TeXLive Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_texlive
    exit $?
fi

check_root

# Check if already installed (idempotent — apt handles it)
if command -v pdflatex &>/dev/null; then
    CURRENT_VERSION="$(pdflatex --version 2>&1 | head -1)"
    echo_warning "pdflatex already installed: $CURRENT_VERSION"
    echo_info "Re-running apt install is idempotent — continuing."
fi

echo_info "Updating apt cache..."
apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

echo_info "Installing TeXLive packages..."
apt-get install -y --no-install-recommends "${TEXLIVE_PACKAGES[@]}" 2>&1 | tee -a "$LOG_PATH"

verify_texlive

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  HOST_TEXLIVE_BIN=/usr/bin"
echo_info "  HOST_TEXMF_DIR=/usr/share/texmf"
echo_info "  HOST_TEXLIVE_DIR=/usr/share/texlive"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind /usr/share/texmf:/usr/share/texmf:ro"
echo_info "  --bind /usr/bin/pdflatex:/usr/bin/pdflatex:ro"
echo_success "Log saved to: $LOG_PATH"

# EOF
