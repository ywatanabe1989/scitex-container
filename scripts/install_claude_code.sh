#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_claude_code.sh
#
# PURPOSE
# -------
# Install Claude Code CLI (@anthropic-ai/claude-code) as a global npm package
# in ~/.npm-global. Does NOT require root — all files are installed in the
# user home directory.
#
# USAGE
# -----
#   ./install_claude_code.sh
#   ./install_claude_code.sh --check   # verify without installing
#   ./install_claude_code.sh --version 2.0.70
#
# PREREQUISITE
# ------------
#   Node.js and npm must be installed first:
#     sudo ./install_nodejs.sh

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
# Config
# ---------------------------------------------------------------------------

NPM_GLOBAL_PATH="${HOME}/.npm-global"
NPM_GLOBAL_BIN="${NPM_GLOBAL_PATH}/bin"
CLAUDE_CODE_VERSION="latest"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_node_available() {
    if ! command -v node &>/dev/null; then
        echo_error "ERROR: node not found. Install Node.js first: sudo ./install_nodejs.sh"
    fi
    if ! command -v npm &>/dev/null; then
        echo_error "ERROR: npm not found. Install Node.js first: sudo ./install_nodejs.sh"
    fi
    echo_info "  node: $(node --version 2>&1)"
    echo_info "  npm:  $(npm --version 2>&1)"
}

verify_claude_code() {
    echo_info "Verifying Claude Code installation..."
    local failed=0
    local claude_bin="${NPM_GLOBAL_BIN}/claude"

    if command -v claude &>/dev/null || [[ -x "${claude_bin}" ]]; then
        local claude_cmd
        claude_cmd="$(command -v claude 2>/dev/null || echo "${claude_bin}")"
        local version
        version="$("${claude_cmd}" --version 2>&1 | head -1)"
        echo_success "  claude: $version (${claude_cmd})"
    else
        echo_warning "  claude: NOT FOUND (looked in PATH and ${claude_bin})"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "Claude Code verified."
        echo_info "  Ensure PATH includes: ${NPM_GLOBAL_BIN}"
    else
        echo_warning "claude not found."
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
    --version)
        shift
        if [[ $# -gt 0 && "$1" != -* ]]; then
            CLAUDE_CODE_VERSION="$1"
            shift
        else
            echo_error "ERROR: --version requires a version argument."
        fi
        ;;
    -h | --help)
        echo "Usage: $0 [--check] [--version VERSION]"
        echo ""
        echo "Options:"
        echo "  --check              Verify installation without installing"
        echo "  --version VERSION    Install specific version (default: latest)"
        echo "  -h, --help           Show this help message"
        exit 0
        ;;
    *)
        echo_error "Unknown argument: $1. Use --help for usage."
        ;;
    esac
done

echo_info "=========================================="
echo_info "Claude Code CLI Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_claude_code
    exit $?
fi

# Require Node.js
check_node_available

# Idempotency check
if [[ -x "${NPM_GLOBAL_BIN}/claude" ]] || command -v claude &>/dev/null; then
    echo_warning "claude already installed."
    echo_info "Reinstalling to ensure up-to-date version — continuing."
fi

echo_info "Configuring npm global prefix to ${NPM_GLOBAL_PATH}..."
mkdir -p "${NPM_GLOBAL_PATH}"
npm config set prefix "${NPM_GLOBAL_PATH}"

# Ensure global bin is in PATH for this session
export PATH="${NPM_GLOBAL_BIN}:${PATH}"

echo_info "Clearing stale npm cache..."
npm cache clean --force 2>&1 | tee -a "$LOG_PATH"

echo_info "Removing any existing Claude Code installation..."
npm uninstall -g @anthropic-ai/claude-code 2>&1 | tee -a "$LOG_PATH" || true
rm -rf "${NPM_GLOBAL_PATH}/lib/node_modules/@anthropic-ai/claude-code"

if [[ "${CLAUDE_CODE_VERSION}" == "latest" ]]; then
    echo_info "Installing @anthropic-ai/claude-code@latest globally..."
    npm install -g @anthropic-ai/claude-code 2>&1 | tee -a "$LOG_PATH"
else
    echo_info "Installing @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} globally..."
    npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" 2>&1 | tee -a "$LOG_PATH"
fi

# Disable auto-updates to keep version pinned
if command -v claude &>/dev/null || [[ -x "${NPM_GLOBAL_BIN}/claude" ]]; then
    local_claude="$(command -v claude 2>/dev/null || echo "${NPM_GLOBAL_BIN}/claude")"
    "${local_claude}" config set -g autoUpdates disabled 2>/dev/null || true
fi

verify_claude_code

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  CLAUDE_BIN=${NPM_GLOBAL_BIN}/claude"
echo_info "  ANTHROPIC_API_KEY=<your-api-key>"
echo_info ""
echo_info "Add to ~/.bashrc or ~/.profile:"
echo_info "  export PATH=\"${NPM_GLOBAL_BIN}:\$PATH\""
echo_info "  export ANTHROPIC_API_KEY=\"your-api-key-here\""
echo_info ""
echo_info "Basic usage:"
echo_info "  claude                 # interactive mode"
echo_info "  claude --version       # show version"
echo_success "Log saved to: $LOG_PATH"

# EOF
