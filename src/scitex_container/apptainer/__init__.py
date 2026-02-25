#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/apptainer/__init__.py
"""Apptainer container management: build, sandbox, versioning, command building."""

from ._build import build
from ._command_builder import (
    build_dev_pythonpath,
    build_exec_args,
    build_host_mount_binds,
    build_srun_command,
)
from ._freeze import freeze
from ._sandbox import configure_ps1 as sandbox_configure_ps1
from ._sandbox import create as sandbox_create
from ._sandbox import is_sandbox
from ._sandbox import maintain as sandbox_maintain
from ._sandbox import to_sif as sandbox_to_sif
from ._status import status
from ._utils import detect_container_cmd, find_containers_dir
from ._verify import verify
from ._versioning import (
    cleanup,
    deploy,
    get_active_version,
    list_versions,
    rollback,
    switch_version,
)
from ._sandbox_versioning import (
    cleanup_sandboxes,
    cleanup_sifs,
    get_active_sandbox,
    list_sandboxes,
    rollback_sandbox,
    switch_sandbox,
)

__all__ = [
    # build
    "build",
    # sandbox
    "sandbox_create",
    "sandbox_maintain",
    "sandbox_to_sif",
    "sandbox_configure_ps1",
    "is_sandbox",
    # sandbox versioning
    "list_sandboxes",
    "get_active_sandbox",
    "switch_sandbox",
    "rollback_sandbox",
    "cleanup_sandboxes",
    "cleanup_sifs",
    # SIF versioning
    "list_versions",
    "get_active_version",
    "switch_version",
    "rollback",
    "deploy",
    "cleanup",
    # command builder
    "build_exec_args",
    "build_srun_command",
    "build_dev_pythonpath",
    "build_host_mount_binds",
    # freeze / status / verify
    "freeze",
    "status",
    "verify",
    # utils
    "detect_container_cmd",
    "find_containers_dir",
]
