#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/apptainer/_build.py
"""Build Apptainer/Singularity SIF or sandbox from .def file."""

from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

from ._utils import detect_container_cmd, find_containers_dir

logger = logging.getLogger(__name__)


def build(
    def_name: str = "scitex-cloud-shared-v0.1.0",
    output_dir: str | Path | None = None,
    force: bool = False,
    sandbox: bool = False,
) -> Path:
    """Build Apptainer/Singularity SIF or sandbox from .def file.

    Parameters
    ----------
    def_name : str
        Name of the .def file (without extension).
    output_dir : str or Path, optional
        Directory for the output .sif file or sandbox directory.
        Defaults to same dir as .def.
    force : bool
        Force rebuild even if .def is unchanged.
    sandbox : bool
        If True, build a sandbox directory instead of a SIF image.
        Uses: apptainer build --sandbox --fakeroot output-sandbox/ input.def

    Returns
    -------
    Path
        Path to the built .sif file or sandbox directory.

    Raises
    ------
    FileNotFoundError
        If .def file or container command not found.
    RuntimeError
        If build fails.
    """
    cmd = detect_container_cmd()
    containers_dir = find_containers_dir()
    def_path = containers_dir / f"{def_name}.def"

    if not def_path.exists():
        raise FileNotFoundError(f"Definition file not found: {def_path}")

    out_dir = Path(output_dir) if output_dir else def_path.parent

    if sandbox:
        output_path = out_dir / f"{def_name}-sandbox"
        hash_file = out_dir / f".{def_name}-sandbox-hash"
    else:
        output_path = out_dir / f"{def_name}.sif"
        hash_file = out_dir / ".def-hash"

    current_hash = _hash_file(def_path)

    if not force and output_path.exists() and hash_file.exists():
        stored_hash = hash_file.read_text().strip()
        if current_hash == stored_hash:
            logger.info("Output is up-to-date (hash: %s...)", current_hash[:12])
            return output_path

    if sandbox:
        logger.info("Building sandbox %s from %s", output_path.name, def_path.name)
        build_args = [
            cmd,
            "build",
            "--sandbox",
            "--fakeroot",
            str(output_path),
            str(def_path),
        ]
    else:
        logger.info("Building %s from %s", output_path.name, def_path.name)
        build_args = ["sudo", cmd, "build", "--force", str(output_path), str(def_path)]

    result = subprocess.run(build_args, capture_output=False)
    if result.returncode != 0:
        raise RuntimeError(f"Build failed with exit code {result.returncode}")

    hash_file.write_text(current_hash + "\n")
    logger.info("Build complete: %s", output_path)

    # Auto-freeze lock files after a successful non-sandbox build
    if not sandbox:
        try:
            from ._freeze import freeze

            freeze(output_path, output_dir=out_dir)
            logger.info("Auto-freeze: lock files saved alongside SIF")
        except Exception as exc:
            logger.warning("Auto-freeze failed (non-fatal): %s", exc)

    return output_path


def _hash_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# EOF
