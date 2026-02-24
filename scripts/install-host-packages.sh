#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install-host-packages.sh
#
# PURPOSE
# -------
# Thin dispatcher: delegates to individual installer scripts for each package
# group. Kept for backward compatibility and as a convenience entry point.
#
# USAGE
# -----
#   sudo ./install-host-packages.sh             # install everything (default)
#   sudo ./install-host-packages.sh --all       # same as above
#   sudo ./install-host-packages.sh --texlive   # texlive only
#   sudo ./install-host-packages.sh --imagemagick  # imagemagick only
#   sudo ./install-host-packages.sh --check     # verify without installing
#
# INDIVIDUAL SCRIPTS
# ------------------
#   scripts/install_texlive.sh
#   scripts/install_imagemagick.sh
#
# IDEMPOTENT: safe to re-run; already-installed packages are skipped by apt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${LIGHT_GRAY}[install-packages] INFO:  $1${NC}"; }
echo_success() { echo -e "${GREEN}[install-packages] OK:    $1${NC}"; }
echo_warning() { echo -e "${YELLOW}[install-packages] WARN:  $1${NC}" >&2; }
echo_error() {
    echo -e "${RED}[install-packages] ERROR: $1${NC}" >&2
    exit 1
}

usage() {
    cat <<EOF
Usage: sudo $(basename "${BASH_SOURCE[0]}") [OPTIONS]

Options:
  --texlive       Install TeXLive packages only
  --imagemagick   Install ImageMagick only
  --all           Install all packages (default if no flags given)
  --check         Verify tools without installing anything
  -h, --help      Show this help message

If no option is provided, --all is assumed.
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DO_TEXLIVE=false
DO_IMAGEMAGICK=false
DO_CHECK=false
EXPLICIT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --texlive)
        DO_TEXLIVE=true
        EXPLICIT=true
        shift
        ;;
    --imagemagick)
        DO_IMAGEMAGICK=true
        EXPLICIT=true
        shift
        ;;
    --all)
        DO_TEXLIVE=true
        DO_IMAGEMAGICK=true
        EXPLICIT=true
        shift
        ;;
    --check)
        DO_CHECK=true
        EXPLICIT=true
        shift
        ;;
    -h | --help)
        usage
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

# Default: install everything
if [[ "${EXPLICIT}" == false ]]; then
    DO_TEXLIVE=true
    DO_IMAGEMAGICK=true
fi

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

TEXLIVE_SCRIPT="${SCRIPT_DIR}/install_texlive.sh"
IMAGEMAGICK_SCRIPT="${SCRIPT_DIR}/install_imagemagick.sh"

for script in "${TEXLIVE_SCRIPT}" "${IMAGEMAGICK_SCRIPT}"; do
    if [[ ! -f "${script}" ]]; then
        echo_error "Required script not found: ${script}"
    fi
done

if [[ "${DO_CHECK}" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    FAILED=0
    [[ "${DO_TEXLIVE}" == true || "${EXPLICIT}" == false ]] && bash "${TEXLIVE_SCRIPT}" --check || ((FAILED++)) || true
    [[ "${DO_IMAGEMAGICK}" == true || "${EXPLICIT}" == false ]] && bash "${IMAGEMAGICK_SCRIPT}" --check || ((FAILED++)) || true
    exit "${FAILED}"
fi

if [[ "${DO_TEXLIVE}" == true ]]; then
    echo_info "--- Installing TeXLive ---"
    bash "${TEXLIVE_SCRIPT}"
    echo_success "TeXLive done."
fi

if [[ "${DO_IMAGEMAGICK}" == true ]]; then
    echo_info "--- Installing ImageMagick ---"
    bash "${IMAGEMAGICK_SCRIPT}"
    echo_success "ImageMagick done."
fi

echo_success "All requested packages installed."

# EOF
