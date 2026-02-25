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
#   sudo ./install-host-packages.sh --docker    # docker only
#   sudo ./install-host-packages.sh --apptainer # apptainer only
#   sudo ./install-host-packages.sh --nodejs    # nodejs only
#        ./install-host-packages.sh --mermaid   # mermaid only (no root needed)
#   sudo ./install-host-packages.sh --check     # verify without installing
#
# INDIVIDUAL SCRIPTS
# ------------------
#   scripts/install_texlive.sh
#   scripts/install_imagemagick.sh
#   scripts/install_docker.sh
#   scripts/install_apptainer.sh
#   scripts/install_nodejs.sh
#   scripts/install_mermaid.sh
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
  --docker        Install Docker CE + Compose + Buildx only
  --apptainer     Install Apptainer only
  --nodejs        Install Node.js 20.x LTS only
  --mermaid       Install Mermaid CLI (mmdc) only (no root required)
  --all           Install all packages (default if no flags given)
  --check         Verify tools without installing anything
  -h, --help      Show this help message

If no option is provided, --all is assumed.
Note: --mermaid does not require root. All other install options require sudo.
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DO_TEXLIVE=false
DO_IMAGEMAGICK=false
DO_DOCKER=false
DO_APPTAINER=false
DO_NODEJS=false
DO_MERMAID=false
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
    --docker)
        DO_DOCKER=true
        EXPLICIT=true
        shift
        ;;
    --apptainer)
        DO_APPTAINER=true
        EXPLICIT=true
        shift
        ;;
    --nodejs)
        DO_NODEJS=true
        EXPLICIT=true
        shift
        ;;
    --mermaid)
        DO_MERMAID=true
        EXPLICIT=true
        shift
        ;;
    --all)
        DO_TEXLIVE=true
        DO_IMAGEMAGICK=true
        DO_DOCKER=true
        DO_APPTAINER=true
        DO_NODEJS=true
        DO_MERMAID=true
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
    DO_DOCKER=true
    DO_APPTAINER=true
    DO_NODEJS=true
    DO_MERMAID=true
fi

# ---------------------------------------------------------------------------
# Locate individual scripts
# ---------------------------------------------------------------------------

TEXLIVE_SCRIPT="${SCRIPT_DIR}/install_texlive.sh"
IMAGEMAGICK_SCRIPT="${SCRIPT_DIR}/install_imagemagick.sh"
DOCKER_SCRIPT="${SCRIPT_DIR}/install_docker.sh"
APPTAINER_SCRIPT="${SCRIPT_DIR}/install_apptainer.sh"
NODEJS_SCRIPT="${SCRIPT_DIR}/install_nodejs.sh"
MERMAID_SCRIPT="${SCRIPT_DIR}/install_mermaid.sh"

for script in \
    "${TEXLIVE_SCRIPT}" \
    "${IMAGEMAGICK_SCRIPT}" \
    "${DOCKER_SCRIPT}" \
    "${APPTAINER_SCRIPT}" \
    "${NODEJS_SCRIPT}" \
    "${MERMAID_SCRIPT}"; do
    if [[ ! -f "${script}" ]]; then
        echo_error "Required script not found: ${script}"
    fi
done

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if [[ "${DO_CHECK}" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    FAILED=0
    [[ "${DO_TEXLIVE}" == true ]] && { bash "${TEXLIVE_SCRIPT}" --check || ((FAILED++)) || true; }
    [[ "${DO_IMAGEMAGICK}" == true ]] && { bash "${IMAGEMAGICK_SCRIPT}" --check || ((FAILED++)) || true; }
    [[ "${DO_DOCKER}" == true ]] && { bash "${DOCKER_SCRIPT}" --check || ((FAILED++)) || true; }
    [[ "${DO_APPTAINER}" == true ]] && { bash "${APPTAINER_SCRIPT}" --check || ((FAILED++)) || true; }
    [[ "${DO_NODEJS}" == true ]] && { bash "${NODEJS_SCRIPT}" --check || ((FAILED++)) || true; }
    [[ "${DO_MERMAID}" == true ]] && { bash "${MERMAID_SCRIPT}" --check || ((FAILED++)) || true; }
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

if [[ "${DO_DOCKER}" == true ]]; then
    echo_info "--- Installing Docker ---"
    bash "${DOCKER_SCRIPT}"
    echo_success "Docker done."
fi

if [[ "${DO_APPTAINER}" == true ]]; then
    echo_info "--- Installing Apptainer ---"
    bash "${APPTAINER_SCRIPT}"
    echo_success "Apptainer done."
fi

if [[ "${DO_NODEJS}" == true ]]; then
    echo_info "--- Installing Node.js ---"
    bash "${NODEJS_SCRIPT}"
    echo_success "Node.js done."
fi

if [[ "${DO_MERMAID}" == true ]]; then
    echo_info "--- Installing Mermaid CLI ---"
    bash "${MERMAID_SCRIPT}"
    echo_success "Mermaid CLI done."
fi

echo_success "All requested packages installed."

# EOF
