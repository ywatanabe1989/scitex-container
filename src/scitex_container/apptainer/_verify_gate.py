#!/usr/bin/env python3
# Timestamp: "2026-08-12"
# File: src/scitex_container/apptainer/_verify_gate.py
"""Use-time reproducibility gate — read the marker a round-trip left.

The WRITE side of reproducibility (rough build → freeze lock → locked def
→ rebuild → compare → mark) lives in ``_reproducible``. This module is the
READ side, and the split is a real boundary rather than a size cut: the
write side runs ONCE, on the build host, and costs two full container
builds; the read side runs on EVERY image use, on every host, and must
never do more than stat two paths.

``check_verified`` is what a consumer calls before booting an image:

- ``.verified`` beside the SIF → silent OK.
- ``.unverified`` → WARN with the recorded drift, or raise under
  ``require_verified``.
- no marker → the image predates the round-trip (or skipped it) → same
  treatment as unverified, with "no marker" as the detail.

Re-exported from ``_reproducible`` so existing imports keep resolving.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from scitex_container._compat import supports_return_as

from ._config import ImageConfig, load_config

logger = logging.getLogger(__name__)


class VerifyError(RuntimeError):
    """Raised by the use-time gate when an image is unverified under strict mode."""


@dataclass(frozen=True)
class VerifyStatus:
    """Result of a use-time verify check."""

    state: str  # "verified" | "unverified" | "unknown"
    sif: Path
    detail: str = ""

    @property
    def is_verified(self) -> bool:
        return self.state == "verified"


@supports_return_as
def check_verified(
    sif_path: str | Path,
    *,
    require_verified: bool | None = None,
    root: str | Path | None = None,
    config: ImageConfig | None = None,
) -> VerifyStatus:
    """Check a built image's reproducibility marker — NOISY on every use.

    The use-time gate consumers call on every image use. Looks beside the
    SIF for the ``.verified`` / ``.unverified`` marker (resolving a
    ``latest`` symlink first):

    - ``.verified`` present → ``state="verified"`` (silent OK).
    - ``.unverified`` present → WARN by default ("reproducibility
      unverified: <drift>"); under ``require_verified`` → raise
      ``VerifyError``.
    - no marker → ``state="unknown"`` → WARN it's unverified; under
      ``require_verified`` → raise.

    Parameters
    ----------
    sif_path : str or Path
        Path to the image being used (may be the ``latest`` symlink).
    require_verified : bool, optional
        Strict mode. When None, resolved from ``config`` /
        ``load_config(root)`` (``images.require_verified``).
    root : str or Path, optional
        Output root for config resolution (when ``require_verified`` and
        ``config`` are both None).
    config : ImageConfig, optional
        Pre-resolved config.

    Returns
    -------
    VerifyStatus
        The marker state + detail.

    Raises
    ------
    VerifyError
        When the image is not verified and strict mode is on.
    """
    sif_path = Path(sif_path)
    resolved = sif_path.resolve() if sif_path.is_symlink() else sif_path

    if require_verified is None:
        cfg = config or load_config(root)
        require_verified = cfg.require_verified

    verified_marker = resolved.with_suffix(".verified")
    unverified_marker = resolved.with_suffix(".unverified")

    if verified_marker.exists():
        return VerifyStatus(
            state="verified", sif=resolved, detail="round-trip verified"
        )

    if unverified_marker.exists():
        detail = unverified_marker.read_text().strip().replace("\n", "; ")
        msg = f"reproducibility unverified: {detail}"
        if require_verified:
            raise VerifyError(f"{resolved.name}: {msg}")
        logger.warning("%s: %s", resolved.name, msg)
        return VerifyStatus(state="unverified", sif=resolved, detail=detail)

    msg = "reproducibility unverified: no round-trip marker found"
    if require_verified:
        raise VerifyError(f"{resolved.name}: {msg}")
    logger.warning("%s: %s", resolved.name, msg)
    return VerifyStatus(state="unknown", sif=resolved, detail="no marker")


__all__ = ["VerifyError", "VerifyStatus", "check_verified"]

# EOF
