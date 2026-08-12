#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: src/scitex_container/apptainer/_reproducible.py
"""Self-verifying reproducible-build round-trip + use-time verify gate.

The round-trip (operator-approved core):

1. **rough build** → ``<layer>-<ts>.sif`` (from the loose ``.def``).
2. **freeze lock** → ``<layer>-<ts>.lock`` (the *actually installed*
   versions — only knowable post-build).
3. **generate locked def** → ``<layer>-<ts>.def`` (every pip version
   pinned from the lock).
4. **rebuild from the locked def** → a throwaway verify SIF.
5. **round-trip verify** — capture the rebuild's lock, compare the two
   version sets:
   - identical → mark ``.verified``.
   - mismatch → **fail loud**: mark ``.unverified`` with the drift diff;
     NOT a build failure (the rough SIF stays usable). Never a silent
     pass.
   The verify SIF is auto-deleted after the compare; the canonical kept
   artifact is the rough SIF + its lock + its locked def + the marker.

Byte-identical (``SOURCE_DATE_EPOCH``) is an OPTIONAL stretch, deliberately
NOT the default gate — version-set identity is the meaningful guarantee
for the paper's reproducibility claim.

The use-time gate (``check_verified``) is what consumers call on *every*
image use: ``.unverified`` → WARN by default, ERROR under
``require_verified``.

scitex-container takes the output ``root`` as an argument (path
injection); it never reads a consumer's config location.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from scitex_container._compat import supports_return_as

from . import _store
from ._build import build as _build
from ._config import ImageConfig, load_config
from ._lockgen import (
    LockDiff,
    capture_lock,
    compare_locks,
    generate_locked_def,
    read_lock,
)

logger = logging.getLogger(__name__)


# The use-time gate (``check_verified`` + its types) lives in
# ``_verify_gate`` — the READ side, run on every image use, versus this
# module's WRITE side, run once per build. Re-exported here so the
# long-standing ``from ._reproducible import check_verified`` keeps
# resolving.
from ._verify_gate import (  # noqa: E402,F401  (deliberate re-export)
    VerifyError,
    VerifyStatus,
    check_verified,
)


@dataclass
class RoundTripResult:
    """Outcome of a reproducible round-trip build."""

    layer: str
    ts: str
    sif: Path  # the kept (rough) artifact
    lock: Path
    locked_def: Path
    verified: bool | None  # None when verify was skipped (e.g. background pending)
    diff: LockDiff | None = None

    @property
    def marker(self) -> Path:
        ap = _store.artifact_paths(self.sif.parent.parent, self.layer, self.ts)
        return ap.verified_marker if self.verified else ap.unverified_marker


@supports_return_as
def build_reproducible(
    layer: str,
    root: str | Path,
    *,
    def_path: str | Path | None = None,
    def_name: str | None = None,
    verify: bool = True,
    keep: bool = False,
    config: ImageConfig | None = None,
    force: bool = False,
    cwd: str | Path | None = None,
) -> RoundTripResult:
    """Run the reproducible round-trip and manage the artifact store.

    Steps 1-3 (rough build, freeze lock, generate locked def) always run
    synchronously — the rough SIF + lock + locked def are the kept,
    immediately-usable artifacts. Steps 4-5 (verify rebuild + compare)
    run inline when ``verify=True``.

    The operator design specifies steps 4-5 run BACKGROUND-by-default in
    the CLI; this function exposes the synchronous primitive that a
    caller (CLI/MCP) backgrounds. ``verify=False`` skips them entirely
    (leaving the build unmarked) so a caller can schedule the verify
    rebuild as a detached job and call ``verify_roundtrip`` later.

    Parameters
    ----------
    layer : str
        Layer name (artifact stem, e.g. ``sac-base``).
    root : str or Path
        The ``containers/`` directory (path injection).
    def_path : str or Path, optional
        Explicit path to the rough ``.def``. Either this or ``def_name``.
    def_name : str, optional
        Name of the ``.def`` to look up via ``find_containers_dir``.
    verify : bool
        Run steps 4-5 inline. False = skip (build stays unmarked).
    keep : bool
        Write the ``.keep`` prune-protect marker on the build.
    config : ImageConfig, optional
        Resolved config (retain). Loaded from ``root`` when None.
    force : bool
        Force the rough rebuild even when the recipe hash is unchanged.
    cwd : str or Path, optional
        Build context — the directory apptainer resolves the ``.def``'s
        relative ``%files`` sources and ``From: ./<other>.sif`` layer
        references against. Forwarded verbatim to ``build`` for BOTH the
        rough build and the verify rebuild, so the replay resolves the
        same staged inputs the rough build did. Defaults to ``root``
        (``build``'s own back-compat default).

        Without it the round-trip is UNREACHABLE for any consumer whose
        recipe reads from a STAGED build context rather than from the
        containers dir: the recipe's relative ``%files`` does not exist
        relative to ``root``, so apptainer FATALs before running a line of
        ``%post``. scitex-agent-container is exactly that consumer — it
        stages its own source tree beside the ``.def`` so the SIF pins the
        source that shipped the recipe — which is why this whole
        round-trip sat here with no caller.

    Returns
    -------
    RoundTripResult
        The kept artifact paths + verify outcome.
    """
    root = Path(root)
    cfg = config or load_config(root)
    ts = _store.timestamp()
    ap = _store.artifact_paths(root, layer, ts)
    ap.layer_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: rough build ------------------------------------------
    # Build straight into the timestamped artifact path. We bypass the
    # _build dir-per-image auto-layout by giving _build a temp image_name
    # then relocating — simpler: build with image_name=<layer>-<ts> so the
    # artifact lands at <root>/<layer>-<ts>/<layer>-<ts>.sif, then move it
    # up into <root>/<layer>/. To keep the store flat we instead build to
    # a scratch dir and move the SIF into the timestamped slot.
    _rough_build(
        layer=layer,
        ts=ts,
        root=root,
        canonical_sif=ap.sif,
        build_log=ap.build_log,
        def_path=def_path,
        def_name=def_name,
        force=force,
        cwd=cwd,
    )

    # Snapshot the rough def alongside (the recipe that produced this build).
    resolved_rough_def = _resolve_def(def_path, def_name)
    rough_def_snapshot = ap.layer_dir / f"{layer}-{ts}.rough.def"
    rough_def_snapshot.write_text(resolved_rough_def.read_text())

    # --- Step 2: freeze lock ------------------------------------------
    rough_lock = capture_lock(ap.sif, ap.lock)

    # --- Step 3: generate locked def ----------------------------------
    generate_locked_def(resolved_rough_def, rough_lock, ap.locked_def)

    # Publish the freshly-built rough artifact through BOTH stable
    # symlinks. This used to call ``point_latest``, which writes only the
    # TOP-level ``<root>/<layer>.sif`` — leaving the INNER
    # ``<root>/<layer>/<layer>.sif`` boot path still resolving to the
    # PREVIOUS build. A consumer that boots off the inner path (as
    # scitex-agent-container's runtime does) would then run the OLD image
    # while the store claimed the new one was live: a reproducible build
    # nobody ever ran.
    _store.publish(root, layer, ts)

    if keep:
        _store.protect(root, layer, ts)

    # Prune older builds per retain.
    _store.prune(root, layer, cfg.retain)

    result = RoundTripResult(
        layer=layer,
        ts=ts,
        sif=ap.sif,
        lock=ap.lock,
        locked_def=ap.locked_def,
        verified=None,
    )

    if not verify:
        logger.info("Skipping round-trip verify (verify=False); build is unmarked")
        return result

    # --- Steps 4-5: verify rebuild + compare --------------------------
    diff = verify_roundtrip(layer, root, ts, cwd=cwd)
    result.verified = diff.identical
    result.diff = diff
    return result


def _resolve_def(
    def_path: str | Path | None,
    def_name: str | None,
) -> Path:
    """Resolve the rough ``.def`` path from ``def_path`` or ``def_name``."""
    if def_path is not None:
        p = Path(def_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.exists():
            raise FileNotFoundError(f"Definition file not found: {p}")
        return p
    if def_name is not None:
        from ._utils import find_containers_dir

        return find_containers_dir() / f"{def_name}.def"
    raise ValueError("Provide either def_path or def_name")


def _rough_build(
    *,
    layer: str,
    ts: str,
    root: Path,
    canonical_sif: Path,
    build_log: Path,
    def_path: str | Path | None,
    def_name: str | None,
    force: bool,
    cwd: str | Path | None = None,
) -> Path:
    """Run the loose (rough) build, relocate into the timestamped slot.

    Builds via ``_build.build`` with ``image_name=<layer>-<ts>`` so the
    artifact lands in a scratch dir-per-image at
    ``<root>/<layer>-<ts>/<layer>-<ts>.sif``, then moves the SIF into the
    canonical ``<root>/<layer>/<layer>-<ts>.sif`` slot and removes the
    scratch dir + the stray top-level ``<root>/<layer>-<ts>.sif`` symlink
    that ``_build`` writes for cross-layer lookups. The scratch
    auto-freeze locks are discarded — the reproducible store captures its
    own combined ``.lock`` (step 2).

    The rough build's log (which ``_build`` writes into the scratch dir
    as ``<scratch>/<scratch>.build-<inner-ts>.log``, where ``<inner-ts>``
    is _build's own timestamp) is relocated into the canonical
    ``build_log`` slot before the scratch dir is removed — otherwise the
    log is lost on ``rmtree``.

    Returns
    -------
    Path
        The canonical SIF path (``canonical_sif``).
    """
    import shutil

    scratch_name = f"{layer}-{ts}"
    scratch_sif = _build(
        def_name=def_name or scratch_name,
        output_dir=root,
        force=force,
        sandbox=False,
        def_path=def_path,
        image_name=scratch_name,
        cwd=cwd,
    )
    scratch_sif = Path(scratch_sif)

    canonical_sif.parent.mkdir(parents=True, exist_ok=True)
    if canonical_sif.exists():
        canonical_sif.unlink()
    os.replace(scratch_sif, canonical_sif)

    scratch_dir = root / scratch_name

    # Preserve the rough build log into the canonical slot before the
    # scratch dir is removed (otherwise rmtree loses it). _build names
    # its log ``<scratch>.build-<inner-ts>.log`` with its own timestamp,
    # so glob for it rather than guessing the inner ts.
    _preserve_build_log(scratch_dir, scratch_name, build_log)

    # Clean the scratch dir-per-image and the stray top-level symlink.
    if scratch_dir.is_dir():
        shutil.rmtree(scratch_dir, ignore_errors=True)
    stray_link = root / f"{scratch_name}.sif"
    if stray_link.is_symlink() or stray_link.exists():
        try:
            stray_link.unlink()
        except OSError:
            pass
    # _build auto-freezes into ``output_dir`` (= root) WITHOUT host
    # isolation, leaving host-bleed lock files we never use (step 2
    # captures our own isolated combined lock). Discard them.
    _discard_stray_locks(root)

    return canonical_sif


def _preserve_build_log(scratch_dir: Path, scratch_name: str, build_log: Path) -> None:
    """Relocate _build's rough log out of the scratch dir into ``build_log``.

    _build writes ``<scratch_dir>/<scratch_name>.build-<inner-ts>.log``
    with its own timestamp; pick the newest match and move it to the
    canonical ``build_log`` path so it survives the scratch ``rmtree``.
    Silently no-ops if no log is found (e.g. an up-to-date skip-rebuild).
    """
    if not scratch_dir.is_dir():
        return
    logs = sorted(scratch_dir.glob(f"{scratch_name}.build-*.log"))
    if not logs:
        return
    newest = logs[-1]
    build_log.parent.mkdir(parents=True, exist_ok=True)
    if build_log.exists():
        build_log.unlink()
    os.replace(newest, build_log)


def _discard_stray_locks(root: Path) -> None:
    """Remove the root-level lock files _build's auto-freeze leaves behind."""
    for name in ("requirements-lock.txt", "dpkg-lock.txt", "node-lock.txt"):
        stray = root / name
        if stray.is_file():
            stray.unlink()


@supports_return_as
def verify_roundtrip(
    layer: str,
    root: str | Path,
    ts: str,
    *,
    cwd: str | Path | None = None,
) -> LockDiff:
    """Rebuild from the locked def, compare version sets, mark the build.

    This is steps 4-5 split out so a caller can run it in the background
    (the operator default) after the rough build returns. It:

    1. rebuilds from ``<layer>-<ts>.def`` into a throwaway verify SIF,
    2. captures the rebuild's lock (a throwaway ``.verify.lock``),
    3. compares against the rough lock,
    4. marks ``.verified`` (identical) or ``.unverified`` (drift, loud),
    5. deletes the throwaway verify SIF + its scratch dir + the
       ``.verify.lock``.

    Parameters
    ----------
    layer : str
        Layer name.
    root : str or Path
        The ``containers/`` directory.
    ts : str
        Timestamp of the rough build to verify.
    cwd : str or Path, optional
        Build context for the verify rebuild. MUST be the same context
        the rough build used — the locked def is the rough def plus a pin
        stanza, so it carries the identical relative ``%files`` /
        ``From:`` references and resolves them the same way or not at all.

    Returns
    -------
    LockDiff
        The round-trip comparison. ``identical`` is the gate.
    """
    root = Path(root)
    ap = _store.artifact_paths(root, layer, ts)
    if not ap.locked_def.exists():
        raise FileNotFoundError(f"Locked def not found: {ap.locked_def}")
    if not ap.lock.exists():
        raise FileNotFoundError(f"Rough lock not found: {ap.lock}")

    rough_lock = read_lock(ap.lock)

    verify_name = f"{layer}-{ts}-verify"
    verify_scratch = root / verify_name
    # The rebuild's lock is a throwaway — captured only to compare against
    # the rough lock, then deleted in the finally below (it would otherwise
    # leave a stray <layer>-<ts>.verify.lock beside the kept artifacts).
    verify_lock_path = ap.layer_dir / f"{layer}-{ts}.verify.lock"
    try:
        verify_sif = _build(
            def_name=verify_name,
            output_dir=root,
            force=True,
            sandbox=False,
            def_path=ap.locked_def,
            image_name=verify_name,
            cwd=cwd,
        )
        rebuild_lock = capture_lock(verify_sif, verify_lock_path)
        diff = compare_locks(rough_lock, rebuild_lock)
    finally:
        # Auto-delete the throwaway verify SIF + its scratch dir + symlink.
        _cleanup_verify(root, verify_name, verify_scratch)
        # Delete the throwaway rebuild lock — it was only needed for the
        # version-set compare above; the kept lock is the rough one.
        if verify_lock_path.is_file():
            verify_lock_path.unlink()

    if diff.identical:
        _store.mark_verified(root, layer, ts)
        logger.info("Round-trip VERIFIED for %s-%s", layer, ts)
    else:
        reason = diff.summary()
        _store.mark_unverified(root, layer, ts, reason=reason)
        # Fail loud — but NOT a build failure: the rough SIF stays usable.
        logger.error(
            "Round-trip MISMATCH for %s-%s: %s. Marked .unverified "
            "(rough SIF stays usable; reproducibility unproven).",
            layer,
            ts,
            reason,
        )

    return diff


def _cleanup_verify(root: Path, verify_name: str, verify_scratch: Path) -> None:
    """Delete the throwaway verify SIF, its scratch dir, and its symlink."""
    import shutil

    link = root / f"{verify_name}.sif"
    if link.is_symlink() or link.exists():
        try:
            link.unlink()
        except OSError:
            pass
    if verify_scratch.is_dir():
        shutil.rmtree(verify_scratch, ignore_errors=True)
    # Discard _build's host-bleed auto-freeze locks (see _rough_build).
    _discard_stray_locks(root)


# EOF
