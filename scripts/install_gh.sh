#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_gh.sh
#
# PURPOSE
# -------
# Install GitHub CLI (gh) from the official apt repository. The gh binary
# runs on the host and can be bind-mounted into Apptainer/Docker containers.
#
# USAGE
# -----
#   sudo ./install_gh.sh
#   sudo ./install_gh.sh --check   # verify without installing

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

install_gh_official() {
    echo_info "Installing prerequisites..."
    apt-get install -y curl gpg 2>&1 | tee -a "$LOG_PATH"

    echo_info "Adding GitHub CLI GPG key..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg |
        tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg

    echo_info "Setting up GitHub CLI apt repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] \
https://cli.github.com/packages stable main" |
        tee /etc/apt/sources.list.d/github-cli.list >/dev/null

    echo_info "Updating apt cache..."
    apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

    echo_info "Installing gh..."
    apt-get install -y gh 2>&1 | tee -a "$LOG_PATH"
}

verify_gh() {
    echo_info "Verifying GitHub CLI installation..."
    local failed=0

    if command -v gh &>/dev/null; then
        echo_success "  gh: $(gh --version 2>&1 | head -1)"
    else
        echo_warning "  gh: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "GitHub CLI verified."
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
echo_info "GitHub CLI (gh) Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_gh
    exit $?
fi

check_root

# Idempotency check
if command -v gh &>/dev/null; then
    CURRENT_VERSION="$(gh --version 2>&1 | head -1)"
    echo_warning "gh already installed: $CURRENT_VERSION"
    echo_info "Re-running install from official repo is idempotent — continuing."
fi

install_gh_official
verify_gh

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  GH_TOKEN=<your-personal-access-token>"
echo_info ""
echo_info "Apptainer bind flags:"
echo_info "  --bind /usr/bin/gh:/usr/bin/gh:ro"
echo_info ""
echo_info "Next steps:"
echo_info "  1. Authenticate: gh auth login"
echo_info "  2. Test: gh repo list"
echo_success "Log saved to: $LOG_PATH"

# EOF
