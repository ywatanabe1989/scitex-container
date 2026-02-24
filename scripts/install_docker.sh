#!/bin/bash
# Timestamp: "2026-02-25"
# File: scripts/install_docker.sh
#
# PURPOSE
# -------
# Install Docker Engine (CE) with Compose V2 and Buildx plugins from the
# official Docker apt repository. The Docker socket/daemon runs on the host;
# containers are not baked into Apptainer/Docker images.
#
# USAGE
# -----
#   sudo ./install_docker.sh
#   sudo ./install_docker.sh --check   # verify without installing

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

is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null
}

remove_old_packages() {
    echo_info "Removing old/conflicting Docker packages if present..."
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    # Remove old standalone docker-compose
    apt-get remove -y docker-compose 2>/dev/null || true
    pip uninstall -y docker-compose 2>/dev/null || true
    rm -f /usr/local/bin/docker-compose
    echo_info "Old packages removed (or were not present)."
}

remove_old_user_plugins() {
    echo_info "Removing stale user-installed CLI plugins..."
    rm -f ~/.docker/cli-plugins/docker-buildx 2>/dev/null || true
    rm -f ~/.docker/cli-plugins/docker-compose 2>/dev/null || true
}

install_docker_official() {
    echo_info "Installing Docker CE from official Docker apt repository..."

    echo_info "Installing prerequisites..."
    apt-get install -y ca-certificates curl gnupg lsb-release 2>&1 | tee -a "$LOG_PATH"

    echo_info "Adding Docker GPG key..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg |
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo_info "Setting up Docker apt repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" |
        tee /etc/apt/sources.list.d/docker.list >/dev/null

    echo_info "Updating apt cache..."
    apt-get update -qq 2>&1 | tee -a "$LOG_PATH"

    echo_info "Installing Docker Engine, CLI, and plugins..."
    apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin 2>&1 | tee -a "$LOG_PATH"
}

setup_docker_group() {
    echo_info "Ensuring docker group exists and current user is a member..."
    if ! getent group docker &>/dev/null; then
        groupadd docker
    fi
    # SUDO_USER is set when running via sudo; fall back to USER
    local target_user="${SUDO_USER:-${USER:-}}"
    if [[ -n "${target_user}" ]]; then
        usermod -aG docker "${target_user}"
        echo_success "User '${target_user}' added to docker group."
        echo_warning "Log out and back in (or run: newgrp docker) for group to take effect."
    else
        echo_warning "Could not determine target user — skipping group membership."
    fi
}

restart_docker_daemon() {
    echo_info "Starting/restarting Docker daemon..."
    if is_wsl; then
        echo_info "WSL detected — using service command."
        service docker restart 2>&1 | tee -a "$LOG_PATH" || service docker start 2>&1 | tee -a "$LOG_PATH"
    else
        systemctl enable docker 2>&1 | tee -a "$LOG_PATH"
        systemctl restart docker 2>&1 | tee -a "$LOG_PATH"
    fi
    sleep 2
    echo_success "Docker daemon started."
}

verify_docker() {
    echo_info "Verifying Docker installation..."
    local failed=0

    if command -v docker &>/dev/null; then
        echo_success "  docker: $(docker --version 2>&1)"
    else
        echo_warning "  docker: NOT FOUND"
        ((failed++)) || true
    fi

    if docker compose version &>/dev/null 2>&1; then
        echo_success "  docker compose: $(docker compose version 2>&1)"
    else
        echo_warning "  docker compose: NOT FOUND"
        ((failed++)) || true
    fi

    if docker buildx version &>/dev/null 2>&1; then
        echo_success "  docker buildx: $(docker buildx version 2>&1)"
    else
        echo_warning "  docker buildx: NOT FOUND"
        ((failed++)) || true
    fi

    if [[ $failed -eq 0 ]]; then
        echo_success "All Docker tools verified."
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
echo_info "Docker Installation Script"
echo_info "=========================================="

if [[ "$CHECK_ONLY" == true ]]; then
    echo_info "Running in --check mode (no packages will be installed)."
    verify_docker
    exit $?
fi

check_root

# Idempotency check
if command -v docker &>/dev/null; then
    CURRENT_VERSION="$(docker --version 2>&1)"
    echo_warning "Docker already installed: $CURRENT_VERSION"
    echo_info "Re-running install from official repo is idempotent — continuing."
fi

remove_old_packages
remove_old_user_plugins
install_docker_official
setup_docker_group
restart_docker_daemon
verify_docker

echo_info ""
echo_info "ENV VAR GUIDANCE:"
echo_info "  DOCKER_HOST=unix:///var/run/docker.sock"
echo_info ""
echo_info "Next steps:"
echo_info "  1. Log out and back in (or: newgrp docker)"
echo_info "  2. Test: docker run --rm hello-world"
echo_info "  3. Test: docker compose version"
echo_info "  4. Test: docker buildx version"
echo_success "Log saved to: $LOG_PATH"

# EOF
