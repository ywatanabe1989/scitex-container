#!/usr/bin/env python3
# Timestamp: "2026-08-12"
# File: tests/scitex_container/apptainer/test__verify_gate.py
"""Tests for scitex_container.apptainer._verify_gate (use-time gate).

No mocks. The gate is exercised against real marker files in tmp_path.
These cases moved here verbatim from ``test__reproducible.py`` when the
gate was extracted into its own module — they test the same behaviour
through its own module now, and one added class pins the re-export so the
long-standing ``_reproducible.check_verified`` entry point cannot silently
disappear.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _gate():
    from scitex_container.apptainer import _verify_gate as g

    return g


@pytest.fixture
def scitex_dir(tmp_path):
    """Point SCITEX_DIR at a tmp dir so config resolution is isolated."""
    user_root = tmp_path / "scitex-home"
    user_root.mkdir()
    saved = os.environ.get("SCITEX_DIR")
    os.environ["SCITEX_DIR"] = str(user_root)
    try:
        yield user_root
    finally:
        if saved is None:
            os.environ.pop("SCITEX_DIR", None)
        else:
            os.environ["SCITEX_DIR"] = saved


@pytest.fixture
def no_project_scope(tmp_path):
    workdir = tmp_path / "no-scope"
    workdir.mkdir()
    saved = Path.cwd()
    os.chdir(workdir)
    try:
        yield workdir
    finally:
        os.chdir(saved)


def _sif_with_marker(tmp_path: Path, marker_ext: str | None, body: str = "") -> Path:
    """Create a fake <name>.sif and an optional sibling marker."""
    sif = tmp_path / "img.sif"
    sif.write_bytes(b"fake")
    if marker_ext is not None:
        (tmp_path / f"img{marker_ext}").write_text(body or "marker\n")
    return sif


class TestCheckVerifiedVerified:
    """A .verified image passes silently."""

    def test_verified_marker_yields_verified_state(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".verified")
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert status.state == "verified"

    def test_verified_status_is_verified_true(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".verified")
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert status.is_verified is True

    def test_verified_passes_even_under_require_verified(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".verified")
        # Act
        status = g.check_verified(sif, require_verified=True)
        # Assert
        assert status.state == "verified"


class TestCheckVerifiedUnverified:
    """An .unverified image warns by default, errors in strict mode."""

    def test_unverified_marker_yields_unverified_state(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".unverified", body="numpy drifted\n")
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert status.state == "unverified"

    def test_unverified_detail_carries_drift_reason(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".unverified", body="numpy drifted\n")
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert "numpy" in status.detail

    def test_unverified_warns_but_returns_in_default_mode(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".unverified", body="drift\n")
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert status.is_verified is False

    def test_unverified_raises_under_require_verified(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, ".unverified", body="drift\n")
        ctx = pytest.raises(g.VerifyError)
        # Act
        # Assert
        with ctx:
            g.check_verified(sif, require_verified=True)


class TestCheckVerifiedUnknown:
    """An image with no marker is treated as unverified."""

    def test_no_marker_yields_unknown_state(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, None)
        # Act
        status = g.check_verified(sif, require_verified=False)
        # Assert
        assert status.state == "unknown"

    def test_no_marker_raises_under_require_verified(self, tmp_path):
        # Arrange
        g = _gate()
        sif = _sif_with_marker(tmp_path, None)
        ctx = pytest.raises(g.VerifyError)
        # Act
        # Assert
        with ctx:
            g.check_verified(sif, require_verified=True)


class TestCheckVerifiedSymlink:
    """A latest-symlink is resolved before the marker lookup."""

    def test_symlink_resolves_to_verified_target(self, tmp_path):
        # Arrange
        g = _gate()
        layer_dir = tmp_path / "base"
        layer_dir.mkdir()
        target = layer_dir / "base-2026-0524-100000.sif"
        target.write_bytes(b"fake")
        (layer_dir / "base-2026-0524-100000.verified").write_text("ok\n")
        link = tmp_path / "base.sif"
        link.symlink_to(Path("base") / "base-2026-0524-100000.sif")
        # Act
        status = g.check_verified(link, require_verified=False)
        # Assert
        assert status.state == "verified"


class TestCheckVerifiedConfigResolution:
    """require_verified is read from config when not passed explicitly."""

    def test_require_verified_from_root_config_raises(
        self, tmp_path, scitex_dir, no_project_scope
    ):
        # Arrange
        g = _gate()
        root = tmp_path / "root"
        root.mkdir()
        (root / "config.yaml").write_text("images:\n  require_verified: true\n")
        sif = _sif_with_marker(tmp_path, ".unverified", body="drift\n")
        ctx = pytest.raises(g.VerifyError)
        # Act
        # Assert
        with ctx:
            g.check_verified(sif, root=root)


class TestReproducibleReExport:
    """The gate stays reachable through its historical import path.

    ``_reproducible.check_verified`` predates the split and is what the
    package __init__ (and therefore every consumer) imports. Extracting the
    gate must not move the entry point out from under them.
    """

    def test_reproducible_reexports_the_same_function(self):
        # Arrange
        from scitex_container.apptainer import _reproducible as r

        g = _gate()
        # Act
        # Assert
        assert r.check_verified is g.check_verified

    def test_reproducible_reexports_the_error_type(self):
        # Arrange
        from scitex_container.apptainer import _reproducible as r

        g = _gate()
        # Act
        # Assert
        assert r.VerifyError is g.VerifyError

    def test_package_export_resolves(self):
        # Arrange
        import scitex_container.apptainer as a

        g = _gate()
        # Act
        # Assert
        assert a.check_verified is g.check_verified


# EOF
