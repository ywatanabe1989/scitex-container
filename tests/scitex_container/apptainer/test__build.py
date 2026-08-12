#!/usr/bin/env python3
# Timestamp: "2026-07-02"
# File: tests/scitex_container/apptainer/test__build.py
"""Tests for scitex_container.apptainer._build atomic-publish logic.

No mocks. The safety-critical part of the atomic build strategy — the
dual stable-symlink publish and its interaction with retention — is pure
filesystem logic, so it is exercised directly against tmp_path with
fake-byte ``.sif`` files (the store never execs them), exactly like the
_store tests. The subprocess-invoking ``build()`` end-to-end path needs a
real apptainer image and is covered by the gated round-trip integration
test (``test__reproducible_roundtrip.py``, which drives ``build()`` via
the rough build).
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _build():
    from scitex_container.apptainer import _build as b

    return b


def _mk_ts_sif(image_dir: Path, name: str, ts: str) -> Path:
    """Materialize a fake timestamped artifact <image_dir>/<name>-<ts>.sif."""
    image_dir.mkdir(parents=True, exist_ok=True)
    sif = image_dir / f"{name}-{ts}.sif"
    sif.write_bytes(b"fake-sif-" + ts.encode())
    return sif


class TestPublishAtomicInner:
    """The inner <name>/<name>.sif symlink — the path consumers boot from."""

    def test_creates_inner_symlink(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert (image_dir / "sac-base.sif").is_symlink()

    def test_inner_resolves_to_timestamped_sif(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        sif = _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert (image_dir / "sac-base.sif").resolve() == sif.resolve()

    def test_inner_target_is_relative(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert not (image_dir / "sac-base.sif").readlink().is_absolute()


class TestPublishAtomicTopLevel:
    """The top-level <name>.sif symlink — cross-layer From: ./<name>.sif."""

    def test_creates_top_level_symlink(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert (tmp_path / "sac-base.sif").is_symlink()

    def test_top_resolves_to_timestamped_sif(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        sif = _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert (tmp_path / "sac-base.sif").resolve() == sif.resolve()

    def test_top_target_is_relative(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert not (tmp_path / "sac-base.sif").readlink().is_absolute()


class TestPublishAtomicReturn:
    """_publish_atomic returns the resolved real timestamped SIF."""

    def test_returns_real_timestamped_sif(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        sif = _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        result = b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert result == sif

    def test_returned_path_is_not_a_symlink(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        # Act
        result = b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Assert
        assert not result.is_symlink()


class TestRepublishSwap:
    """A rebuild atomically repoints both symlinks; prior build retained."""

    def test_inner_repoints_to_new_build(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-110000")
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-110000")
        # Assert
        assert (image_dir / "sac-base.sif").resolve().name == "sac-base-2026-0702-110000.sif"

    def test_top_repoints_to_new_build(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-110000")
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-110000")
        # Assert
        assert (tmp_path / "sac-base.sif").resolve().name == "sac-base-2026-0702-110000.sif"

    def test_prior_build_retained_on_disk(self, tmp_path):
        # Arrange
        b = _build()
        image_dir = tmp_path / "sac-base"
        prior = _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-110000")
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-100000")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-110000")
        # Assert — the prior SIF stays available for rollback
        assert prior.exists()


class TestPublishThenRetain:
    """publish + _store.prune — build()'s retention behaviour, no apptainer."""

    def _store(self):
        from scitex_container.apptainer import _store as s

        return s

    def test_prune_keeps_live_plus_retain(self, tmp_path):
        # Arrange
        b = _build()
        s = self._store()
        image_dir = tmp_path / "sac-base"
        for ts in ("2026-0702-100000", "2026-0702-110000", "2026-0702-120000"):
            _mk_ts_sif(image_dir, "sac-base", ts)
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-120000")
        # Act
        s.prune(tmp_path, "sac-base", retain=1)
        # Assert — live build + 1 previous kept (store semantic: N+1 total)
        assert len(list(image_dir.glob("sac-base-*.sif"))) == 2

    def test_prune_removes_oldest(self, tmp_path):
        # Arrange
        b = _build()
        s = self._store()
        image_dir = tmp_path / "sac-base"
        oldest = _mk_ts_sif(image_dir, "sac-base", "2026-0702-100000")
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-110000")
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-120000")
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-120000")
        # Act
        s.prune(tmp_path, "sac-base", retain=1)
        # Assert
        assert not oldest.exists()

    def test_live_symlink_valid_after_prune(self, tmp_path):
        # Arrange
        b = _build()
        s = self._store()
        image_dir = tmp_path / "sac-base"
        for ts in ("2026-0702-100000", "2026-0702-110000", "2026-0702-120000"):
            _mk_ts_sif(image_dir, "sac-base", ts)
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-120000")
        # Act
        s.prune(tmp_path, "sac-base", retain=1)
        # Assert — the boot symlink still resolves to an existing file
        assert (image_dir / "sac-base.sif").resolve().exists()

    def test_active_build_never_pruned(self, tmp_path):
        # Arrange
        b = _build()
        s = self._store()
        image_dir = tmp_path / "sac-base"
        for ts in ("2026-0702-100000", "2026-0702-110000", "2026-0702-120000"):
            _mk_ts_sif(image_dir, "sac-base", ts)
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-120000")
        # Act
        pruned = s.prune(tmp_path, "sac-base", retain=1)
        # Assert
        assert "2026-0702-120000" not in pruned


class TestMigratesPreAtomicRealFile:
    """A pre-atomic-layout real file at the inner path is replaced by a symlink."""

    def test_real_inner_file_replaced_by_symlink(self, tmp_path):
        # Arrange — legacy layout: <name>/<name>.sif is a real file
        b = _build()
        image_dir = tmp_path / "sac-base"
        _mk_ts_sif(image_dir, "sac-base", "2026-0702-120000")
        (image_dir / "sac-base.sif").write_bytes(b"legacy-real-file")
        # Act
        b._publish_atomic(tmp_path, image_dir, "sac-base", "2026-0702-120000")
        # Assert
        assert (image_dir / "sac-base.sif").is_symlink()


# ---------------------------------------------------------------------------
# Recipe snapshot + auto-freeze — driven through the REAL build() path
# ---------------------------------------------------------------------------

_FAKE_APPTAINER_OK = """#!/bin/sh
# Stand-in apptainer: succeeds, and materializes the artifact `build`
# was asked to produce so the post-build bookkeeping runs for real.
case "$1" in
  build)
    for a in "$@"; do case "$a" in *.sif) out="$a";; esac; done
    printf 'fake sif\\n' > "$out"
    ;;
  exec)
    # capture_lock introspects the SIF; answer with an empty version set.
    printf ''
    ;;
esac
exit 0
"""

_FAKE_APPTAINER_FAIL = """#!/bin/sh
# Stand-in apptainer: the build dies partway, exactly like an interrupted
# or failing %post — no artifact is produced.
echo "FATAL: simulated build failure" >&2
exit 255
"""


@pytest.fixture
def fake_apptainer(tmp_path):
    """Put a REAL executable named ``apptainer`` first on PATH.

    ``detect_container_cmd`` resolves through ``shutil.which``, so a real
    shell script in tmp_path is a genuine substitute — the production code
    execs it through the same ``subprocess.run`` it uses in anger. Yields a
    callable that installs a given script body.
    """
    import os
    import stat

    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    saved = os.environ.get("PATH", "")

    def install(body: str) -> Path:
        exe = bindir / "apptainer"
        exe.write_text(body)
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = f"{bindir}{os.pathsep}{saved}"
        return exe

    try:
        yield install
    finally:
        os.environ["PATH"] = saved


def _prepare(tmp_path, body: str, install):
    """Install the given fake apptainer and lay out a real .def to build."""
    b = _build()
    install(body)
    out_dir = tmp_path / "containers"
    out_dir.mkdir(exist_ok=True)
    def_path = tmp_path / "sac-base.def"
    def_path.write_text("Bootstrap: docker\nFrom: ubuntu:24.04\n")
    return b, out_dir, def_path


@pytest.fixture
def aborted_build(tmp_path, fake_apptainer):
    """Drive ``build()`` through a REAL failing apptainer.

    The failure is the fixture's job, so each test below carries exactly
    one assertion about the wreckage it left.
    """
    b, out_dir, def_path = _prepare(tmp_path, _FAKE_APPTAINER_FAIL, fake_apptainer)
    try:
        b.build(def_path=def_path, output_dir=out_dir, image_name="sac-base")
    except RuntimeError:
        return out_dir / "sac-base"
    raise AssertionError("the fake apptainer was expected to fail the build")


@pytest.fixture
def finished_build(tmp_path, fake_apptainer):
    """Drive ``build()`` through a REAL succeeding apptainer.

    Yields ``(sif, image_dir, def_path)`` for the completed build.
    """
    b, out_dir, def_path = _prepare(tmp_path, _FAKE_APPTAINER_OK, fake_apptainer)
    sif = b.build(def_path=def_path, output_dir=out_dir, image_name="sac-base")
    return sif, out_dir / "sac-base", def_path


@pytest.fixture
def aborted_after_finished(tmp_path, fake_apptainer):
    """A good build, then an edited recipe whose rebuild fails.

    The realistic shape of the bug: the operator edits the recipe, the
    rebuild dies, and the artifact dir must still describe the build that
    is actually on disk. Yields ``(image_dir, good_recipe_text)``.
    """
    b, out_dir, def_path = _prepare(tmp_path, _FAKE_APPTAINER_OK, fake_apptainer)
    b.build(def_path=def_path, output_dir=out_dir, image_name="sac-base")
    image_dir = out_dir / "sac-base"
    good = (image_dir / "sac-base.def").read_text()
    def_path.write_text("Bootstrap: docker\nFrom: ubuntu:24.04\n%post\n    false\n")
    fake_apptainer(_FAKE_APPTAINER_FAIL)
    try:
        b.build(
            def_path=def_path, output_dir=out_dir, image_name="sac-base", force=True
        )
    except RuntimeError:
        return image_dir, good
    raise AssertionError("the fake apptainer was expected to fail the rebuild")


class TestRecipeSnapshotOnlyOnSuccess:
    """The ``.def`` snapshot must describe a build that actually finished.

    The snapshot used to be copied in at build START while ``.def-hash``
    was written only on SUCCESS, so an aborted build left a recipe
    describing a build that never happened — permanently disagreeing with
    the hash beside it. Measured on a live host (2026-08-12): the ``.def``
    hashed b7564978… while ``.def-hash`` said 47c7bbfc…, and the live SIF
    was neither.
    """

    def test_aborted_build_writes_no_recipe_snapshot(self, aborted_build):
        # Arrange
        # Act
        # Assert
        assert not (aborted_build / "sac-base.def").exists()

    def test_aborted_build_writes_no_recipe_hash(self, aborted_build):
        # Arrange
        # Act
        # Assert
        assert not (aborted_build / ".def-hash").exists()

    def test_finished_build_snapshots_the_recipe(self, finished_build):
        # Arrange
        _sif, image_dir, def_path = finished_build
        # Act
        # Assert
        assert (image_dir / "sac-base.def").read_text() == def_path.read_text()

    def test_snapshot_and_hash_agree_after_success(self, finished_build):
        # Arrange
        import hashlib

        _sif, image_dir, _def_path = finished_build
        expected = hashlib.sha256((image_dir / "sac-base.def").read_bytes()).hexdigest()
        # Act
        # Assert
        assert (image_dir / ".def-hash").read_text().strip() == expected

    def test_aborted_rebuild_leaves_previous_snapshot_intact(
        self, aborted_after_finished
    ):
        # Arrange
        image_dir, good = aborted_after_finished
        # Act
        # Assert
        assert (image_dir / "sac-base.def").read_text() == good


class TestAutoFreezeIsArtifactScoped:
    """Each build's version set belongs to THAT build's artifact.

    The auto-freeze used to write three fixed names at the containers
    ROOT, so a ``sac-scitex`` build overwrote the ``sac-base`` record and
    the next base build destroyed the current SIF's only fingerprint.
    """

    def test_writes_lock_beside_the_timestamped_sif(self, finished_build):
        # Arrange
        sif, _image_dir, _def_path = finished_build
        # Act
        # Assert
        assert sif.with_suffix(".lock").exists()

    def test_lock_name_carries_the_build_timestamp(self, finished_build):
        # Arrange
        sif, _image_dir, _def_path = finished_build
        # Act
        # Assert
        assert sif.with_suffix(".lock").name == f"{sif.stem}.lock"

    def test_writes_no_fixed_name_lock_at_the_root(self, finished_build):
        # Arrange
        _sif, image_dir, _def_path = finished_build
        # Act
        # Assert
        assert not (image_dir.parent / "requirements-lock.txt").exists()

    def test_second_layer_does_not_clobber_the_first_lock(
        self, tmp_path, fake_apptainer
    ):
        # Arrange
        b, out_dir, def_path = _prepare(tmp_path, _FAKE_APPTAINER_OK, fake_apptainer)
        base_sif = b.build(
            def_path=def_path, output_dir=out_dir, image_name="sac-base"
        )
        # Act — a different layer builds from the same output root
        b.build(def_path=def_path, output_dir=out_dir, image_name="sac-scitex")
        # Assert
        assert base_sif.with_suffix(".lock").exists()


# EOF
