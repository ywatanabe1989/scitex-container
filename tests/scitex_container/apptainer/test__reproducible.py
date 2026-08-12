#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: tests/scitex_container/apptainer/test__reproducible.py
"""Tests for scitex_container.apptainer._reproducible (round-trip side).

No mocks. The build-context (``cwd``) forwarding is exercised against a
real recording callable substituted for ``_build``; the log-relocation
helper against real files in tmp_path. The full round-trip
(``build_reproducible`` / ``verify_roundtrip`` end to end) requires
apptainer + a real build and lives in the gated integration test
``test__reproducible_roundtrip.py``.

The use-time gate (``check_verified``) moved to ``_verify_gate`` and its
tests to ``test__verify_gate.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _repro():
    from scitex_container.apptainer import _reproducible as r

    return r


@pytest.fixture
def recording_build():
    """Swap ``_reproducible._build`` for a real recording callable.

    Save/restore of a module-level attribute — the same pattern the
    package already uses for its own build seam — not a mocking library:
    the substitute is an ordinary function that records the kwargs it was
    called with and materializes the SIF on disk, so everything around it
    (relocate, log preservation, publish, prune) runs for real against
    real files. Yields the list of recorded call kwargs.

    Substituting the build itself is the point: what these tests assert is
    precisely WHICH ARGUMENTS reach apptainer, and a real multi-minute
    container build cannot answer that question.
    """
    from scitex_container.apptainer import _reproducible as r

    calls: list[dict] = []

    def recording(**kwargs):
        calls.append(dict(kwargs))
        out_dir = Path(kwargs["output_dir"])
        name = kwargs["image_name"]
        image_dir = out_dir / name
        image_dir.mkdir(parents=True, exist_ok=True)
        sif = image_dir / f"{name}.sif"
        sif.write_bytes(b"fake-sif")
        return sif

    saved = r._build
    r._build = recording
    try:
        yield calls
    finally:
        r._build = saved


class TestRoughBuildForwardsCwd:
    """The rough build must resolve the recipe against the caller's context.

    A consumer whose ``.def`` reads ``%files`` from a STAGED directory can
    only use the round-trip if that directory reaches apptainer as the
    build cwd. Dropping it silently builds against the wrong tree (or
    FATALs), which is why the round-trip had no callers.
    """

    def test_forwards_cwd_to_build(self, tmp_path, recording_build):
        # Arrange
        r = _repro()
        staging = tmp_path / "build-context"
        staging.mkdir()
        # Act
        r._rough_build(
            layer="base",
            ts="2026-0812-100000",
            root=tmp_path,
            canonical_sif=tmp_path / "base" / "base-2026-0812-100000.sif",
            build_log=tmp_path / "base" / "base-2026-0812-100000.build.log",
            def_path=None,
            def_name="base",
            force=False,
            cwd=staging,
        )
        # Assert
        assert recording_build[0]["cwd"] == staging

    def test_defaults_cwd_to_none_when_unset(self, tmp_path, recording_build):
        # Arrange
        r = _repro()
        # Act
        r._rough_build(
            layer="base",
            ts="2026-0812-100000",
            root=tmp_path,
            canonical_sif=tmp_path / "base" / "base-2026-0812-100000.sif",
            build_log=tmp_path / "base" / "base-2026-0812-100000.build.log",
            def_path=None,
            def_name="base",
            force=False,
        )
        # Assert
        assert recording_build[0]["cwd"] is None


class TestVerifyRoundtripForwardsCwd:
    """The replay must use the SAME build context as the rough build.

    The locked def is the rough def plus a pin stanza, so it carries the
    identical relative ``%files`` / ``From:`` references. Replaying it from
    a different cwd does not compare like with like — it fails to build.
    """

    def test_forwards_cwd_to_verify_rebuild(self, tmp_path, recording_build):
        # Arrange
        r = _repro()
        from scitex_container.apptainer import _store as s

        staging = tmp_path / "build-context"
        staging.mkdir()
        ap = s.artifact_paths(tmp_path, "base", "2026-0812-100000")
        ap.layer_dir.mkdir(parents=True)
        ap.sif.write_bytes(b"fake-sif")
        ap.locked_def.write_text("Bootstrap: docker\nFrom: alpine:3.19\n")
        ap.lock.write_text("# scitex-container lock\n[pip]\n[dpkg]\n[node]\n")
        # Act
        r.verify_roundtrip("base", tmp_path, "2026-0812-100000", cwd=staging)
        # Assert
        assert recording_build[0]["cwd"] == staging


class TestBuildReproduciblePublishesBothSymlinks:
    """A published round-trip build must be the one that actually boots.

    ``point_latest`` writes only the TOP link; runtimes boot off the INNER
    ``<layer>/<layer>.sif``. Publishing one without the other leaves the
    store advertising a build nobody runs.
    """

    def test_inner_boot_symlink_points_at_the_new_build(
        self, tmp_path, recording_build
    ):
        # Arrange
        r = _repro()
        def_path = tmp_path / "base.def"
        def_path.write_text("Bootstrap: docker\nFrom: alpine:3.19\n")
        # Act
        res = r.build_reproducible(
            layer="base", root=tmp_path, def_path=def_path, verify=False
        )
        # Assert
        inner = tmp_path / "base" / "base.sif"
        assert inner.resolve() == res.sif.resolve()

    def test_top_level_symlink_points_at_the_new_build(
        self, tmp_path, recording_build
    ):
        # Arrange
        r = _repro()
        def_path = tmp_path / "base.def"
        def_path.write_text("Bootstrap: docker\nFrom: alpine:3.19\n")
        # Act
        res = r.build_reproducible(
            layer="base", root=tmp_path, def_path=def_path, verify=False
        )
        # Assert
        assert (tmp_path / "base.sif").resolve() == res.sif.resolve()


class TestPreserveBuildLog:
    """_preserve_build_log relocates _build's scratch log into the canonical slot.

    Pure filesystem logic (no real build): _build writes its log as
    ``<scratch>/<scratch>.build-<inner-ts>.log``; the helper must move it
    to the canonical ``build_log`` path so the rough build's log survives
    the scratch-dir ``rmtree``.
    """

    def _scratch_with_log(self, tmp_path: Path, scratch_name: str, body: str) -> Path:
        scratch_dir = tmp_path / scratch_name
        scratch_dir.mkdir()
        # _build's log name shape: <scratch>.build-<YYYY-MMDD-HHMMSS>.log
        log = scratch_dir / f"{scratch_name}.build-2026-0524-090000.log"
        log.write_text(body)
        return scratch_dir

    def test_relocates_scratch_log_to_canonical_slot(self, tmp_path):
        # Arrange
        r = _repro()
        scratch = self._scratch_with_log(tmp_path, "base-ts", "rough build output\n")
        canonical = tmp_path / "base" / "base-ts.build.log"
        # Act
        r._preserve_build_log(scratch, "base-ts", canonical)
        # Assert
        assert canonical.read_text() == "rough build output\n"

    def test_removes_log_from_scratch_after_move(self, tmp_path):
        # Arrange
        r = _repro()
        scratch = self._scratch_with_log(tmp_path, "base-ts", "x\n")
        canonical = tmp_path / "base" / "base-ts.build.log"
        # Act
        r._preserve_build_log(scratch, "base-ts", canonical)
        # Assert
        assert list(scratch.glob("*.build-*.log")) == []

    def test_picks_newest_log_when_multiple(self, tmp_path):
        # Arrange
        r = _repro()
        scratch = tmp_path / "base-ts"
        scratch.mkdir()
        (scratch / "base-ts.build-2026-0524-080000.log").write_text("old\n")
        (scratch / "base-ts.build-2026-0524-090000.log").write_text("new\n")
        canonical = tmp_path / "base" / "base-ts.build.log"
        # Act
        r._preserve_build_log(scratch, "base-ts", canonical)
        # Assert
        assert canonical.read_text() == "new\n"

    def test_no_log_is_a_silent_noop(self, tmp_path):
        # Arrange
        r = _repro()
        scratch = tmp_path / "base-ts"
        scratch.mkdir()
        canonical = tmp_path / "base" / "base-ts.build.log"
        # Act
        r._preserve_build_log(scratch, "base-ts", canonical)
        # Assert
        assert not canonical.exists()

    def test_missing_scratch_dir_is_a_silent_noop(self, tmp_path):
        # Arrange
        r = _repro()
        canonical = tmp_path / "base" / "base-ts.build.log"
        # Act
        r._preserve_build_log(tmp_path / "absent", "base-ts", canonical)
        # Assert
        assert not canonical.exists()


# EOF
