#!/usr/bin/env python3
# Timestamp: "2026-05-12"
# File: tests/conftest.py
"""Pytest configuration and shared fixtures.

Two responsibilities:

1. Source-tree sys.path bootstrap — adds the scitex-container src/ and
   scitex-dev src/ directories so tests can run without prior
   ``pip install -e .`` of either package.

2. Subprocess coverage wiring — pins ``COVERAGE_PROCESS_START`` +
   ``COVERAGE_FILE`` at module-import time (force-set, not
   ``setdefault``; pytest-cov has already set ``COVERAGE_FILE`` to a
   per-test tmp dir by the time this loads) and puts a SESSION-SCOPED
   ``sitecustomize`` on ``PYTHONPATH`` that calls
   ``coverage.process_startup()`` in every child interpreter. Without
   this, ``subprocess.run([sys.executable, ...])`` coverage data is
   silently dropped — see
   ``~/proj/scitex-dev/src/scitex_dev/_skills/general/05_development_06_subprocess-coverage.md``.

   This used to install a ``.pth`` into site-packages. It no longer writes
   anything outside the session; see
   :func:`_install_session_subprocess_coverage` for why that mattered.
"""

from __future__ import annotations

import atexit
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure packages are importable from source trees
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCITEX_CONTAINER_SRC = _REPO_ROOT / "src"

# scitex-dev lives as a sibling repo in ~/proj/scitex-dev
_SCITEX_DEV_SRC = _REPO_ROOT.parent / "scitex-dev" / "src"

for _p in (_SCITEX_CONTAINER_SRC, _SCITEX_DEV_SRC):
    _s = str(_p)
    if _p.is_dir() and _s not in sys.path:
        sys.path.insert(0, _s)

# ---------------------------------------------------------------------------
# Subprocess coverage wiring (parallel + COVERAGE_PROCESS_START)
# ---------------------------------------------------------------------------

# Pin coverage's data file at the repo root and point process_startup at our
# pyproject so child interpreters configure themselves correctly. FORCE-SET
# (not setdefault) — pytest-cov has already set COVERAGE_FILE to a tmp dir
# by the time conftest loads, so setdefault would be a silent no-op.
os.environ["COVERAGE_PROCESS_START"] = str(_REPO_ROOT / "pyproject.toml")
os.environ["COVERAGE_FILE"] = str(_REPO_ROOT / ".coverage")


# The text of the session-scoped ``sitecustomize`` handed to child
# interpreters. Two responsibilities, in this order:
#
# 1. CHAIN to whatever ``sitecustomize`` we are shadowing. We are first on
#    PYTHONPATH, which precedes the stdlib directory, so a system
#    ``sitecustomize`` would otherwise silently never run. Debian/Ubuntu ship
#    one (``/etc/python3.12/sitecustomize.py``) that installs apport's crash
#    handler — measured present on this fleet's image. Shadowing it would be
#    a fresh instance of exactly the bug this change exists to remove: a thing
#    that stops working with no error and no diagnosis.
# 2. Start coverage, guarded, only when asked.
_SITECUSTOMIZE = '''\
"""Session-scoped subprocess-coverage shim (scitex-container tests).

Injected via PYTHONPATH for the duration of one test session, then removed.
Never installed into site-packages.
"""

import os
import sys


def _chain_shadowed_sitecustomize():
    """Run the sitecustomize this file shadows, if any."""
    here = os.path.dirname(os.path.abspath(__file__))
    for entry in sys.path:
        try:
            directory = os.path.abspath(entry or ".")
        except (TypeError, ValueError):
            continue
        if directory == here:
            continue
        candidate = os.path.join(directory, "sitecustomize.py")
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate) as handle:
                source = handle.read()
            exec(  # noqa: S102 - re-running the shadowed hook is the point
                compile(source, candidate, "exec"),
                {"__file__": candidate, "__name__": "sitecustomize"},
            )
        except Exception:
            # A broken system hook must not take the child process with it.
            pass
        return


_chain_shadowed_sitecustomize()

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage
    except ImportError:
        pass
    else:
        coverage.process_startup()
'''


def _install_session_subprocess_coverage() -> None:
    """Enable coverage in CHILD interpreters for THIS SESSION ONLY.

    Replaces a ``.pth`` written into site-packages. That older approach
    worked, and was wrong in a way that took a while to see:

    **It was machine-wide state produced as a side effect of collecting
    tests.** A ``.pth`` in site-packages affects every Python process on the
    box, forever, including processes that have nothing to do with this repo.

    **And it did not stay fixed.** The writer rewrote the file whenever its
    content differed, which is idempotent with respect to its own text but
    NOT monotonic with respect to time. Any checkout older than the fix is
    also a writer, so the rule was last-writer-wins: running the suite from a
    stale worktree silently reverted the file. Measured on 2026-08-12 — a
    fixed shim was reverted minutes later by a baseline checkout one commit
    behind, with no commit to blame and no error to read. A fix whose
    precondition is "nobody runs an old worktree" is not a fix, because that
    condition is neither achievable nor checkable.

    So the mechanism is now scoped to the session that wants it:

    - a temp dir holding ``sitecustomize.py`` is prepended to ``PYTHONPATH``,
      so children inherit it and nothing else on the machine is touched;
    - it is removed at interpreter exit, so it cannot outlive the run;
    - nothing is written to site-packages, so there is no shared file for two
      checkouts to fight over and no requirement that any checkout be current.

    It is also a no-op when ``coverage`` is not importable. There is nothing
    to start in that case, and putting a ``sitecustomize`` on the path of
    every child process to accomplish nothing is precisely the cost this
    change is removing. (On this fleet's image coverage is in fact absent —
    the old ``.pth`` was inert *and* noisy.)
    """
    if importlib.util.find_spec("coverage") is None:
        return

    shim_dir = Path(tempfile.mkdtemp(prefix="scitex-container-subproc-cov-"))
    (shim_dir / "sitecustomize.py").write_text(_SITECUSTOMIZE)

    previous = os.environ.get("PYTHONPATH", "")
    parts = [str(shim_dir)] + ([previous] if previous else [])
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)

    atexit.register(shutil.rmtree, shim_dir, ignore_errors=True)


_install_session_subprocess_coverage()

# EOF
