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
   per-test tmp dir by the time this loads) and drops an idempotent
   ``.pth`` shim into site-packages that calls
   ``coverage.process_startup()`` in every child interpreter. Without
   this, ``subprocess.run([sys.executable, ...])`` coverage data is
   silently dropped — see
   ``~/proj/scitex-dev/src/scitex_dev/_skills/general/05_development_06_subprocess-coverage.md``.
"""

from __future__ import annotations

import os
import sys
import sysconfig
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


def _ensure_subprocess_coverage_shim() -> None:
    """Drop an idempotent ``.pth`` file in site-packages that auto-starts
    coverage in every child Python interpreter via
    ``coverage.process_startup()``.

    The shim is written in a very specific shape, and both halves matter.

    **Guard the import.** A ``.pth`` executes at interpreter startup, inside
    ``site``, for EVERY Python process on the machine — long before any
    application code exists to catch anything. The previous shim ran a bare
    ``import coverage`` at line 1, so on any interpreter without coverage
    installed, ``site`` printed a traceback to stderr and carried on. That is
    every command in every container on this fleet: one ``curl | python3``
    emitted four tracebacks before two lines of real output.

    The cost is not the noise. It is that people learn to skim past stderr,
    which is exactly where the next real error will appear.

    **Check the env var FIRST.** A non-test process now imports *nothing* —
    it evaluates one ``os.environ.get`` and stops. Ordering the check before
    the import is not merely a tidier way to spell the guard: it means the
    overwhelming majority of processes stop paying for a coverage import they
    were never going to use. A ``.pth`` should be the cheapest and quietest
    thing in the process.
    """
    purelib = Path(sysconfig.get_paths()["purelib"])
    pth = purelib / "_scitex_container_subprocess_coverage.pth"
    shim = (
        "import os\n"
        "if os.environ.get('COVERAGE_PROCESS_START'):\n"
        "    try:\n"
        "        import coverage\n"
        "    except ImportError:\n"
        "        pass\n"
        "    else:\n"
        "        coverage.process_startup()\n"
    )
    try:
        if not pth.exists() or pth.read_text() != shim:
            pth.write_text(shim)
    except OSError:
        # site-packages may be read-only (e.g. system Python); silently skip —
        # local dev venvs are writable and that's where this matters.
        pass


_ensure_subprocess_coverage_shim()

# EOF
