#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/apptainer/_sandbox.py
"""Sandbox management for Apptainer containers."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ._utils import detect_container_cmd

logger = logging.getLogger(__name__)


def is_sandbox(path: str | Path) -> bool:
    """Check if path is a sandbox directory (not a SIF image).

    A path ending in ``.sif`` is treated as a SIF image; anything else
    (including bare directory names or paths ending in ``-sandbox``) is
    treated as a sandbox directory.

    Parameters
    ----------
    path : str or Path
        Path to check.

    Returns
    -------
    bool
        True if path is a sandbox directory, False if it is a SIF image.
    """
    return not str(path).rstrip("/").endswith(".sif")


def create(source_sif: str | Path, output_dir: str | Path) -> Path:
    """Convert a SIF image to a sandbox directory.

    Parameters
    ----------
    source_sif : str or Path
        Path to the source .sif file.
    output_dir : str or Path
        Path for the output sandbox directory.

    Returns
    -------
    Path
        Path to the created sandbox directory.

    Raises
    ------
    FileNotFoundError
        If the source SIF does not exist or apptainer is not found.
    RuntimeError
        If the conversion fails.
    """
    source_sif = Path(source_sif)
    output_dir = Path(output_dir)

    if not source_sif.exists():
        raise FileNotFoundError(f"SIF not found: {source_sif}")

    cmd = detect_container_cmd()
    logger.info("Creating sandbox %s from %s", output_dir, source_sif.name)

    result = subprocess.run(
        [cmd, "build", "--sandbox", "--fakeroot", str(output_dir), str(source_sif)],
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Sandbox creation failed with exit code {result.returncode}"
        )

    logger.info("Sandbox created: %s", output_dir)
    return output_dir


def maintain(sandbox_dir: str | Path, command: list[str]) -> int:
    """Run a command inside a sandbox with --writable --fakeroot flags.

    Intended for admin maintenance tasks (installing packages, etc.).
    For user sessions, use --writable-tmpfs instead.

    Parameters
    ----------
    sandbox_dir : str or Path
        Path to the sandbox directory.
    command : list[str]
        Command to execute inside the sandbox.

    Returns
    -------
    int
        Return code of the executed command.

    Raises
    ------
    FileNotFoundError
        If the sandbox directory does not exist or apptainer is not found.
    """
    sandbox_dir = Path(sandbox_dir)

    if not sandbox_dir.exists():
        raise FileNotFoundError(f"Sandbox directory not found: {sandbox_dir}")

    cmd = detect_container_cmd()
    logger.info("Running maintenance command in sandbox %s", sandbox_dir.name)

    result = subprocess.run(
        [cmd, "exec", "--writable", "--fakeroot", str(sandbox_dir), *command],
        capture_output=False,
    )

    if result.returncode != 0:
        logger.warning("Maintenance command exited with code %d", result.returncode)

    return result.returncode


def to_sif(sandbox_dir: str | Path, output_sif: str | Path) -> Path:
    """Convert a sandbox directory back to a SIF image.

    Parameters
    ----------
    sandbox_dir : str or Path
        Path to the source sandbox directory.
    output_sif : str or Path
        Path for the output .sif file.

    Returns
    -------
    Path
        Path to the created .sif file.

    Raises
    ------
    FileNotFoundError
        If the sandbox directory does not exist or apptainer is not found.
    RuntimeError
        If the conversion fails.
    """
    sandbox_dir = Path(sandbox_dir)
    output_sif = Path(output_sif)

    if not sandbox_dir.exists():
        raise FileNotFoundError(f"Sandbox directory not found: {sandbox_dir}")

    cmd = detect_container_cmd()
    logger.info("Converting sandbox %s to SIF %s", sandbox_dir.name, output_sif.name)

    result = subprocess.run(
        ["sudo", cmd, "build", "--force", str(output_sif), str(sandbox_dir)],
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Sandbox to SIF conversion failed with exit code {result.returncode}"
        )

    logger.info("SIF created: %s", output_sif)
    return output_sif


# EOF
