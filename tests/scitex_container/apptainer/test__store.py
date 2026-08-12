#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: tests/scitex_container/apptainer/test__store.py
"""Tests for scitex_container.apptainer._store.

No mocks. The store owns on-disk shape only (paths, symlink, markers,
retention), so every test writes real files into tmp_path — fake `.sif`
files are plain bytes (the store never execs them) and the symlink /
prune / marker logic is exercised against the real filesystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _store():
    from scitex_container.apptainer import _store as s

    return s


def _make_build(root: Path, layer: str, ts: str, *, lock=True, locked_def=True) -> None:
    """Materialize a fake build: <root>/<layer>/<layer>-<ts>.{sif,lock,def}."""
    s = _store()
    ap = s.artifact_paths(root, layer, ts)
    ap.layer_dir.mkdir(parents=True, exist_ok=True)
    ap.sif.write_bytes(b"fake-sif-" + ts.encode())
    if lock:
        ap.lock.write_text(f"# lock {ts}\n")
    if locked_def:
        ap.locked_def.write_text(f"# def {ts}\n")


class TestArtifactPaths:
    """ArtifactPaths layout — timestamp correspondence is the invariant."""

    def test_sif_path_includes_layer_and_timestamp(self, tmp_path):
        # Arrange
        s = _store()
        # Act
        ap = s.artifact_paths(tmp_path, "sac-base", "2026-0524-101500")
        # Assert
        assert ap.sif == tmp_path / "sac-base" / "sac-base-2026-0524-101500.sif"

    def test_lock_shares_timestamp_with_sif(self, tmp_path):
        # Arrange
        s = _store()
        ap = s.artifact_paths(tmp_path, "sac-base", "2026-0524-101500")
        # Act
        sif_stem = ap.sif.stem
        lock_stem = ap.lock.stem
        # Assert
        assert sif_stem == lock_stem

    def test_latest_symlink_is_layer_dot_sif_at_root(self, tmp_path):
        # Arrange
        s = _store()
        # Act
        ap = s.artifact_paths(tmp_path, "sac-base", "2026-0524-101500")
        # Assert
        assert ap.latest_symlink == tmp_path / "sac-base.sif"


class TestAtomicSymlink:
    """atomic_symlink — the SSOT safe-swap primitive."""

    def test_creates_symlink_at_link_path(self, tmp_path):
        # Arrange
        s = _store()
        (tmp_path / "target.sif").write_bytes(b"x")
        link = tmp_path / "latest.sif"
        # Act
        s.atomic_symlink(link, "target.sif")
        # Assert
        assert link.is_symlink()

    def test_target_written_verbatim(self, tmp_path):
        # Arrange
        s = _store()
        link = tmp_path / "latest.sif"
        # Act
        s.atomic_symlink(link, Path("sub") / "target.sif")
        # Assert
        assert str(link.readlink()) == str(Path("sub") / "target.sif")

    def test_replaces_existing_symlink(self, tmp_path):
        # Arrange
        s = _store()
        link = tmp_path / "latest.sif"
        s.atomic_symlink(link, "old.sif")
        # Act
        s.atomic_symlink(link, "new.sif")
        # Assert
        assert str(link.readlink()) == "new.sif"

    def test_replaces_existing_real_file(self, tmp_path):
        # Arrange — a pre-atomic-layout real file at the link path
        s = _store()
        link = tmp_path / "latest.sif"
        link.write_bytes(b"real-file")
        # Act
        s.atomic_symlink(link, "new.sif")
        # Assert
        assert link.is_symlink() and str(link.readlink()) == "new.sif"

    def test_no_leftover_temp_files(self, tmp_path):
        # Arrange
        s = _store()
        link = tmp_path / "latest.sif"
        # Act
        s.atomic_symlink(link, "target.sif")
        # Assert — the temp symlink was consumed by os.replace
        assert list(tmp_path.glob(".*.tmp.*")) == []


class TestPointLatest:
    """point_latest writes a relative symlink to the timestamped build."""

    def test_creates_symlink_at_layer_dot_sif(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-101500")
        # Act
        s.point_latest(tmp_path, "base", "2026-0524-101500")
        # Assert
        assert (tmp_path / "base.sif").is_symlink()

    def test_symlink_resolves_to_timestamped_sif(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-101500")
        # Act
        s.point_latest(tmp_path, "base", "2026-0524-101500")
        # Assert
        assert (tmp_path / "base.sif").resolve() == (
            tmp_path / "base" / "base-2026-0524-101500.sif"
        ).resolve()

    def test_symlink_target_is_relative(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-101500")
        # Act
        s.point_latest(tmp_path, "base", "2026-0524-101500")
        # Assert
        assert not (tmp_path / "base.sif").readlink().is_absolute()

    def test_repoint_replaces_previous_target(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-101500")
        _make_build(tmp_path, "base", "2026-0524-120000")
        s.point_latest(tmp_path, "base", "2026-0524-101500")
        # Act
        s.point_latest(tmp_path, "base", "2026-0524-120000")
        # Assert
        assert (tmp_path / "base.sif").resolve().name == "base-2026-0524-120000.sif"

    def test_missing_build_raises_file_not_found(self, tmp_path):
        # Arrange
        s = _store()
        import pytest

        ctx = pytest.raises(FileNotFoundError)
        # Act
        # Assert
        with ctx:
            s.point_latest(tmp_path, "base", "2026-0524-999999")


class TestMarkers:
    """verified / unverified / keep markers."""

    def test_mark_verified_writes_verified_marker(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts")
        # Act
        marker = s.mark_verified(tmp_path, "base", "ts")
        # Assert
        assert marker.exists()

    def test_mark_verified_clears_prior_unverified(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts")
        s.mark_unverified(tmp_path, "base", "ts", reason="drift")
        # Act
        s.mark_verified(tmp_path, "base", "ts")
        # Assert
        assert not s.artifact_paths(tmp_path, "base", "ts").unverified_marker.exists()

    def test_mark_unverified_records_reason(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts")
        # Act
        marker = s.mark_unverified(tmp_path, "base", "ts", reason="numpy drifted")
        # Assert
        assert "numpy drifted" in marker.read_text()

    def test_mark_unverified_clears_prior_verified(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts")
        s.mark_verified(tmp_path, "base", "ts")
        # Act
        s.mark_unverified(tmp_path, "base", "ts", reason="drift")
        # Assert
        assert not s.artifact_paths(tmp_path, "base", "ts").verified_marker.exists()

    def test_protect_writes_keep_marker(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts")
        # Act
        marker = s.protect(tmp_path, "base", "ts")
        # Assert
        assert marker.exists()


class TestListBuilds:
    """list_builds enumeration + status."""

    def test_lists_all_builds_for_layer(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-100000")
        _make_build(tmp_path, "base", "2026-0524-110000")
        # Act
        builds = s.list_builds(tmp_path, "base")
        # Assert
        assert len(builds) == 2

    def test_builds_sorted_newest_first(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-100000")
        _make_build(tmp_path, "base", "2026-0524-110000")
        # Act
        builds = s.list_builds(tmp_path, "base")
        # Assert
        assert builds[0]["ts"] == "2026-0524-110000"

    def test_verified_marker_reported_true(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-100000")
        s.mark_verified(tmp_path, "base", "2026-0524-100000")
        # Act
        builds = s.list_builds(tmp_path, "base")
        # Assert
        assert builds[0]["verified"] is True

    def test_unmarked_build_reports_verified_none(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-100000")
        # Act
        builds = s.list_builds(tmp_path, "base")
        # Assert
        assert builds[0]["verified"] is None

    def test_active_build_flagged_after_point_latest(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "2026-0524-100000")
        s.point_latest(tmp_path, "base", "2026-0524-100000")
        # Act
        builds = s.list_builds(tmp_path, "base")
        # Assert
        assert builds[0]["active"] is True

    def test_missing_layer_dir_returns_empty_list(self, tmp_path):
        # Arrange
        s = _store()
        # Act
        builds = s.list_builds(tmp_path, "absent")
        # Assert
        assert builds == []


class TestPrune:
    """retain:N retention + .keep prune-protection."""

    def test_keeps_n_most_recent(self, tmp_path):
        # Arrange
        s = _store()
        for i in range(5):
            _make_build(tmp_path, "base", f"2026-0524-10000{i}")
        # Act
        s.prune(tmp_path, "base", retain=2)
        # Assert
        assert len(s.list_builds(tmp_path, "base")) == 2

    def test_prune_removes_oldest_first(self, tmp_path):
        # Arrange
        s = _store()
        for i in range(4):
            _make_build(tmp_path, "base", f"2026-0524-10000{i}")
        # Act
        pruned = s.prune(tmp_path, "base", retain=2)
        # Assert
        assert "2026-0524-100000" in pruned

    def test_keep_marker_protects_old_build(self, tmp_path):
        # Arrange
        s = _store()
        for i in range(4):
            _make_build(tmp_path, "base", f"2026-0524-10000{i}")
        s.protect(tmp_path, "base", "2026-0524-100000")  # oldest, protected
        # Act
        pruned = s.prune(tmp_path, "base", retain=1)
        # Assert
        assert "2026-0524-100000" not in pruned

    def test_active_build_never_pruned(self, tmp_path):
        # Arrange
        s = _store()
        for i in range(4):
            _make_build(tmp_path, "base", f"2026-0524-10000{i}")
        s.point_latest(tmp_path, "base", "2026-0524-100000")  # oldest, active
        # Act
        pruned = s.prune(tmp_path, "base", retain=1)
        # Assert
        assert "2026-0524-100000" not in pruned

    def test_prune_deletes_paired_lock_and_def(self, tmp_path):
        # Arrange
        s = _store()
        for i in range(3):
            _make_build(tmp_path, "base", f"2026-0524-10000{i}")
        # Act
        s.prune(tmp_path, "base", retain=1)
        # Assert
        assert not (tmp_path / "base" / "base-2026-0524-100000.lock").exists()

    def test_no_prune_when_under_retain(self, tmp_path):
        # Arrange
        s = _store()
        _make_build(tmp_path, "base", "ts0")
        # Act
        pruned = s.prune(tmp_path, "base", retain=10)
        # Assert
        assert pruned == []


class TestPublishBothSymlinks:
    """``publish`` swaps BOTH stable links — the boot path and the top link.

    ``point_latest`` writes only the top-level link. Any caller that means
    "make this build live" must write the inner boot link too, or runtimes
    keep resolving the previous build while the store advertises the new
    one.
    """

    def _mk_build(self, root, layer, ts):
        layer_dir = root / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        sif = layer_dir / f"{layer}-{ts}.sif"
        sif.write_bytes(b"fake-" + ts.encode())
        return sif

    def test_creates_inner_boot_symlink(self, tmp_path):
        # Arrange
        s = _store()
        self._mk_build(tmp_path, "base", "2026-0812-100000")
        # Act
        s.publish(tmp_path, "base", "2026-0812-100000")
        # Assert
        assert (tmp_path / "base" / "base.sif").is_symlink()

    def test_inner_boot_symlink_resolves_to_the_build(self, tmp_path):
        # Arrange
        s = _store()
        sif = self._mk_build(tmp_path, "base", "2026-0812-100000")
        # Act
        s.publish(tmp_path, "base", "2026-0812-100000")
        # Assert
        assert (tmp_path / "base" / "base.sif").resolve() == sif.resolve()

    def test_creates_top_level_symlink(self, tmp_path):
        # Arrange
        s = _store()
        sif = self._mk_build(tmp_path, "base", "2026-0812-100000")
        # Act
        s.publish(tmp_path, "base", "2026-0812-100000")
        # Assert
        assert (tmp_path / "base.sif").resolve() == sif.resolve()

    def test_both_targets_are_relative(self, tmp_path):
        # Arrange
        s = _store()
        self._mk_build(tmp_path, "base", "2026-0812-100000")
        # Act
        s.publish(tmp_path, "base", "2026-0812-100000")
        # Assert
        assert not (tmp_path / "base" / "base.sif").readlink().is_absolute()

    def test_republish_repoints_inner_link_to_newer_build(self, tmp_path):
        # Arrange
        s = _store()
        self._mk_build(tmp_path, "base", "2026-0812-100000")
        newer = self._mk_build(tmp_path, "base", "2026-0812-110000")
        s.publish(tmp_path, "base", "2026-0812-100000")
        # Act
        s.publish(tmp_path, "base", "2026-0812-110000")
        # Assert
        assert (tmp_path / "base" / "base.sif").resolve() == newer.resolve()

    def test_returns_the_real_sif(self, tmp_path):
        # Arrange
        s = _store()
        sif = self._mk_build(tmp_path, "base", "2026-0812-100000")
        # Act
        published = s.publish(tmp_path, "base", "2026-0812-100000")
        # Assert
        assert published == sif

    def test_missing_artifact_raises(self, tmp_path):
        # Arrange
        s = _store()
        (tmp_path / "base").mkdir()
        ctx = pytest.raises(FileNotFoundError)
        # Act
        # Assert
        with ctx:
            s.publish(tmp_path, "base", "2026-0812-100000")


# EOF
