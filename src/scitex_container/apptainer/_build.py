#!/usr/bin/env python3
# Timestamp: "2026-07-02"
# File: src/scitex_container/apptainer/_build.py
"""Build Apptainer/Singularity SIF or sandbox from .def file.

Dir-per-image layout — every artifact for one ``<name>.def`` lives in
its own ``<out_dir>/<name>/`` subdir, and the built SIF is published
through TWO stable symlinks (each swapped atomically on a successful
build), so the live paths every consumer boots from never point at a
half-written image:

    containers/
    ├── <name>.def                          (the recipe — caller-managed input)
    ├── <name>.sif -> <name>/<name>-<ts>.sif (top-level convenience symlink)
    └── <name>/
        ├── <name>-<ts>.sif                  (the built image — timestamped)
        ├── <name>.sif -> <name>-<ts>.sif    (stable inner symlink; boot here)
        ├── <name>.def                       (snapshot of the recipe at build time)
        ├── <name>.build-YYYY-MMDD-HHMMSS.log (full build log)
        └── .def-hash                        (sha256 of the recipe, for skip-rebuild)

Atomic build strategy (the SSOT for safe SIF builds — sac consumes this
rather than running ``apptainer build --force`` in place):

- Build into a fresh, timestamped ``<name>-<ts>.sif`` — never overwrite
  a live image in place.
- On success, atomically repoint BOTH stable symlinks (temp symlink +
  ``os.replace``, via ``_store.atomic_symlink``):
    * INNER   ``<name>/<name>.sif -> <name>-<ts>.sif``  — the path agents
      boot from (kept stable so consumer specs never churn).
    * TOP     ``<name>.sif -> <name>/<name>-<ts>.sif``  — so recipes that
      say ``From: ./<name>.sif`` (resolved against the build cwd) keep
      working across layers.
- Retain the last N timestamped SIFs for rollback (``retain``; defaults
  to the image config's ``retain``). The live symlink targets are never
  pruned.
- A failed build raises before any swap, leaving the prior symlinks and
  their targets fully intact.

The build cwd (``cwd``) is the directory apptainer resolves the .def's
relative ``%files`` sources and ``From: ./<other>.sif`` against. It
defaults to ``out_dir`` (back-compat: the top-level ``<name>.sif``
symlinks live there), but a caller staging ``%files`` into a separate
build context can set it independently of where the SIF lands.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from pathlib import Path

from scitex_container._compat import supports_return_as

from . import _store
from ._utils import detect_container_cmd, find_containers_dir

logger = logging.getLogger(__name__)


@supports_return_as
def build(
    def_name: str = "scitex-cloud-shared-v0.1.0",
    output_dir: str | Path | None = None,
    force: bool = False,
    sandbox: bool = False,
    *,
    def_path: str | Path | None = None,
    image_name: str | None = None,
    use_sudo: bool = False,
    fakeroot: bool | None = None,
    cwd: str | Path | None = None,
    retain: int | None = None,
) -> Path:
    """Build Apptainer/Singularity SIF or sandbox from .def file.

    Parameters
    ----------
    def_name : str
        Name of the .def file (without extension) when looking it up in
        the discovered containers dir. Ignored if ``def_path`` is given.
    output_dir : str or Path, optional
        Directory under which the per-image subdir is created (i.e.
        the artifact lands at ``<output_dir>/<image_name>/<image_name>-<ts>.sif``).
        Defaults to the directory containing the resolved ``.def`` file.
    force : bool
        Force rebuild even if .def is unchanged.
    sandbox : bool
        If True, build a sandbox directory instead of a SIF image.
        Uses: apptainer build --sandbox --fakeroot output-sandbox/ input.def
    def_path : str or Path, optional
        Explicit path to the ``.def`` file. Lets out-of-tree callers
        (e.g. scitex-agent-container, whose recipes ship inside its
        own wheel) bypass ``find_containers_dir``. When given,
        ``def_name`` is ignored for lookup and ``image_name`` defaults
        to the .def's stem.
    image_name : str, optional
        Name of the per-image subdir + artifact stem (i.e. the artifact
        lands at ``<output_dir>/<image_name>/<image_name>-<ts>.sif``).
        Defaults to ``def_name`` (or the .def stem when ``def_path``
        is given). Use this when the on-disk recipe is named
        differently from the image you want to produce — e.g. sac's
        ``apptainer-base.def`` → ``sac-base/sac-base.sif``.
    use_sudo : bool
        Prefix the build with ``sudo``.
    fakeroot : bool, optional
        Pass ``--fakeroot``. Defaults to True for sandbox builds (needed
        to chown files inside the sandbox tree as the build user) and
        False for SIF builds. Set explicitly to override.
    cwd : str or Path, optional
        Build context — the directory apptainer resolves the .def's
        relative ``%files`` sources and ``From: ./<other>.sif`` layer
        references against. Defaults to ``output_dir`` (back-compat).
        Set this when the ``%files`` staging dir must be independent of
        where the produced SIF lands.
    retain : int, optional
        Number of *previous* timestamped SIFs to keep per image for
        rollback. The just-published (live) build is always kept, so
        ``retain=N`` leaves up to ``N + 1`` SIFs on disk; older ones are
        pruned after a successful build. Defaults to the image config's
        ``retain`` resolved from ``output_dir`` (via ``_store.prune``,
        the same retention the reproducible store uses). SIF builds only.

    Returns
    -------
    Path
        For a SIF build, the resolved real timestamped image
        (``<output_dir>/<image_name>/<image_name>-<ts>.sif``); the stable
        boot symlink is ``<output_dir>/<image_name>/<image_name>.sif``.
        For a sandbox build, the sandbox directory path.

    Raises
    ------
    FileNotFoundError
        If .def file or container command not found.
    RuntimeError
        If build fails.
    """
    cmd = detect_container_cmd()
    if def_path is not None:
        resolved_def = Path(def_path)
        if not resolved_def.is_absolute():
            resolved_def = Path.cwd() / resolved_def
    else:
        containers_dir = find_containers_dir()
        resolved_def = containers_dir / f"{def_name}.def"

    if not resolved_def.exists():
        raise FileNotFoundError(f"Definition file not found: {resolved_def}")

    name = image_name or (def_name if def_path is None else resolved_def.stem)
    out_dir = Path(output_dir) if output_dir else resolved_def.parent
    image_dir = out_dir / name
    image_dir.mkdir(parents=True, exist_ok=True)

    # Build context: what apptainer resolves relative ``%files`` and
    # ``From: ./<other>.sif`` against. Defaults to out_dir (where the
    # top-level ``<name>.sif`` symlinks live), overridable by callers that
    # stage ``%files`` elsewhere.
    build_cwd = Path(cwd) if cwd is not None else out_dir

    if sandbox:
        return _build_sandbox(
            cmd=cmd,
            resolved_def=resolved_def,
            name=name,
            image_dir=image_dir,
            build_cwd=build_cwd,
            force=force,
            use_sudo=use_sudo,
            fakeroot=fakeroot,
        )

    return _build_sif(
        cmd=cmd,
        resolved_def=resolved_def,
        name=name,
        out_dir=out_dir,
        image_dir=image_dir,
        build_cwd=build_cwd,
        force=force,
        use_sudo=use_sudo,
        fakeroot=fakeroot,
        retain=retain,
    )


def _build_sif(
    *,
    cmd: str,
    resolved_def: Path,
    name: str,
    out_dir: Path,
    image_dir: Path,
    build_cwd: Path,
    force: bool,
    use_sudo: bool,
    fakeroot: bool | None,
    retain: int | None,
) -> Path:
    """Atomic timestamped SIF build with dual stable-symlink publish."""
    hash_file = image_dir / ".def-hash"
    inner_link = image_dir / f"{name}.sif"  # stable boot symlink
    current_hash = _hash_file(resolved_def)

    # Skip-rebuild: the stable inner symlink resolves to an existing SIF
    # and the recipe hash is unchanged. (A pre-atomic-layout real file at
    # the inner path is intentionally not skip-eligible — the next build
    # migrates it into the atomic layout.)
    if not force and inner_link.is_symlink() and hash_file.exists():
        resolved_sif = inner_link.resolve()
        if resolved_sif.exists() and hash_file.read_text().strip() == current_hash:
            logger.info("Output is up-to-date (hash: %s...)", current_hash[:12])
            return resolved_sif

    ts = _store.timestamp()
    log_path = image_dir / f"{name}.build-{ts}.log"
    output_path = image_dir / f"{name}-{ts}.sif"

    # SIF builds are rootless when apptainer is setuid-installed; fakeroot
    # off by default (caller can override).
    fakeroot = False if fakeroot is None else fakeroot

    privilege_args: list[str] = ["sudo"] if use_sudo else []
    flag_args: list[str] = []
    if fakeroot:
        flag_args += ["--fakeroot"]
    # --force only guards the fresh timestamped target against a partial
    # left by a crashed same-ts build; it never overwrites a live image.
    flag_args += ["--force"]

    logger.info("Building image %s from %s", output_path.name, resolved_def.name)
    build_args = [
        *privilege_args,
        cmd,
        "build",
        *flag_args,
        str(output_path),
        str(resolved_def),
    ]

    logger.info("Build log → %s (cwd=%s)", log_path, build_cwd)
    with open(log_path, "wb") as log_fh:
        result = subprocess.run(
            build_args,
            cwd=str(build_cwd),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
    if result.returncode != 0:
        # The live symlinks were never touched — remove only the partial
        # artifact so it can't be mistaken for a good build.
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass
        raise RuntimeError(
            f"Build failed with exit code {result.returncode}; see {log_path}"
        )

    # Snapshot the recipe alongside the artifact ON SUCCESS, in lockstep
    # with the hash that describes it. Both used to be written at different
    # moments — the ``.def`` copy before the build, the ``.def-hash`` after
    # it — so an interrupted or failed build left a recipe snapshot
    # describing a build that never finished, permanently disagreeing with
    # the hash beside it (measured on a live host 2026-08-12: the ``.def``
    # hashed b7564978… while ``.def-hash`` said 47c7bbfc…, and the live SIF
    # was neither). Writing both here makes the pair atomic in practice:
    # a failed build leaves the PREVIOUS build's snapshot + hash intact,
    # which is the only self-consistent thing to leave behind.
    shutil.copy2(resolved_def, image_dir / f"{name}.def")
    hash_file.write_text(current_hash + "\n")

    # Atomically publish the new build through both stable symlinks, before
    # prune so retention sees the new build as active and never prunes it.
    _publish_atomic(out_dir, image_dir, name, ts)

    # Retention: keep the last N timestamped SIFs; the active target (the
    # symlinks just written) is always protected. Reuses the store's prune.
    if retain is None:
        from ._config import load_config

        retain = load_config(out_dir).retain
    _store.prune(out_dir, name, retain)

    logger.info("Build complete: %s (published %s.sif)", output_path, name)

    # Auto-freeze: capture this build's version set into an ARTIFACT-SCOPED
    # lock, ``<image_dir>/<name>-<ts>.lock``.
    #
    # This used to call ``_freeze.freeze(output_path, output_dir=out_dir)``,
    # which wrote three FIXED names (``requirements-lock.txt`` /
    # ``dpkg-lock.txt`` / ``node-lock.txt``) at the containers ROOT. Three
    # problems, all fixed by scoping the lock to the artifact:
    #
    #   1. Cross-layer clobber — a ``sac-scitex`` build overwrote the
    #      ``sac-base`` record, so the next base build destroyed the
    #      current SIF's only fingerprint. Nothing tied a lock to the SIF
    #      it described.
    #   2. Host bleed — ``freeze`` execs without ``--cleanenv --no-home``,
    #      so apptainer auto-mounts ``$HOME`` and ``pip freeze`` captured
    #      the HOST environment. ``capture_lock`` isolates (see
    #      ``_lockgen._exec_capture``), so what lands is the CONTAINER's
    #      version set — the only one that means anything here.
    #   3. Unprunable — root-level fixed names outlived every retention
    #      sweep. ``<name>-<ts>.lock`` is exactly the path
    #      ``_store._remove_build`` already deletes, so locks now age out
    #      with the SIF they describe.
    #
    # The format is the same combined ``.lock`` the reproducible round-trip
    # writes, so a plain build's lock and a round-trip lock are directly
    # comparable. ``_freeze.freeze`` itself is unchanged and still backs the
    # explicit ``container freeze`` verb.
    try:
        from ._lockgen import capture_lock

        lock_path = image_dir / f"{name}-{ts}.lock"
        capture_lock(output_path, lock_path)
        logger.info("Auto-freeze: lock saved at %s", lock_path)
    except Exception as exc:
        logger.warning("Auto-freeze failed (non-fatal): %s", exc)

    return output_path


def _build_sandbox(
    *,
    cmd: str,
    resolved_def: Path,
    name: str,
    image_dir: Path,
    build_cwd: Path,
    force: bool,
    use_sudo: bool,
    fakeroot: bool | None,
) -> Path:
    """Build a sandbox directory (in place; not atomically swappable)."""
    output_path = image_dir / f"{name}.sandbox"
    hash_file = image_dir / ".sandbox-hash"
    current_hash = _hash_file(resolved_def)

    if not force and output_path.exists() and hash_file.exists():
        if hash_file.read_text().strip() == current_hash:
            logger.info("Output is up-to-date (hash: %s...)", current_hash[:12])
            return output_path

    ts = _store.timestamp()
    log_path = image_dir / f"{name}.build-{ts}.log"

    # Sandbox builds need fakeroot to chown files inside the tree as the
    # build user; on by default (caller can override).
    fakeroot = True if fakeroot is None else fakeroot

    privilege_args: list[str] = ["sudo"] if use_sudo else []
    flag_args: list[str] = ["--sandbox"]
    if fakeroot:
        flag_args += ["--fakeroot"]
    flag_args += ["--force"]

    logger.info("Building sandbox %s from %s", output_path.name, resolved_def.name)
    build_args = [
        *privilege_args,
        cmd,
        "build",
        *flag_args,
        str(output_path),
        str(resolved_def),
    ]

    logger.info("Build log → %s (cwd=%s)", log_path, build_cwd)
    with open(log_path, "wb") as log_fh:
        result = subprocess.run(
            build_args,
            cwd=str(build_cwd),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"Build failed with exit code {result.returncode}; see {log_path}"
        )

    # Recipe snapshot + hash together, ON SUCCESS — same reasoning as the
    # SIF path above: a failed sandbox build must not leave a snapshot
    # describing a build that never finished.
    shutil.copy2(resolved_def, image_dir / f"{name}.def")
    hash_file.write_text(current_hash + "\n")
    logger.info("Build complete: %s", output_path)
    return output_path


def _publish_atomic(out_dir: Path, image_dir: Path, name: str, ts: str) -> Path:
    """Publish ``<name>-<ts>.sif`` via both stable symlinks, atomically.

    Swaps the two live paths consumers depend on (temp symlink + os.replace,
    via ``_store.atomic_symlink``) so a rebuild is published all-at-once and
    a reader never sees a missing/partial link:

    - INNER  ``<image_dir>/<name>.sif -> <name>-<ts>.sif``  (boot path)
    - TOP    ``<out_dir>/<name>.sif   -> <name>/<name>-<ts>.sif``  (From: ./x.sif)

    Delegates to ``_store.publish`` — the shared primitive the reproducible
    round-trip publishes through too, so both build paths land the same
    two links. ``image_dir`` is ``out_dir/name`` by construction and stays
    in the signature for the existing callers/tests.

    Returns the resolved real SIF (``<image_dir>/<name>-<ts>.sif``).
    """
    return _store.publish(out_dir, name, ts)


def _hash_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# EOF
