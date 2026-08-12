# Changelog

All notable changes to `scitex-container` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.2]

### Changed

- **The test suite no longer writes anything into site-packages.** 0.4.1
  guarded the subprocess-coverage `.pth` so it stopped tracebacking; this
  removes the `.pth` mechanism altogether, because guarding it fixed the
  symptom and left the real defect standing.

  That defect: the shim was **machine-wide state produced as a side effect of
  collecting tests**, and the writer rewrote it whenever its content differed
  — idempotent with respect to its own text, but **not monotonic with respect
  to time**. Every checkout older than the fix is also a writer, so the rule
  was last-writer-wins. Measured 2026-08-12: a freshly fixed shim was reverted
  minutes later by a baseline checkout one commit behind, with no commit to
  blame and no error to read. A fix whose precondition is "nobody runs an old
  worktree" is not a fix — that condition is neither achievable nor checkable.

  Subprocess coverage is now **session-scoped**: a temp directory holding a
  `sitecustomize.py` is prepended to `PYTHONPATH` for the run and removed at
  interpreter exit. Children inherit it; nothing else on the machine is
  touched; there is no shared file for two checkouts to fight over.

  It is also a **no-op when `coverage` is not importable** — there is nothing
  to start, and putting a `sitecustomize` in front of every child process to
  accomplish nothing is the cost being removed. (Note `pytest-cov` 7.x ships
  no `.pth` of its own, so this shim *is* the subprocess-coverage mechanism;
  deleting it outright would have silently dropped child-process coverage
  rather than fixing anything.)

  The generated `sitecustomize` **chains to any `sitecustomize` it shadows**.
  Being first on `PYTHONPATH` puts it ahead of the stdlib directory, and
  Debian/Ubuntu ship `/etc/python3.12/sitecustomize.py` (it installs apport's
  crash handler). Shadowing that silently would have been a fresh instance of
  the same family of bug: something that stops working with no error.

### Note for operators

Machines that ran an older suite still carry a stale
`site-packages/_scitex_container_subprocess_coverage.pth`. Nothing in this
release deletes it — deliberately, since removing it from `conftest` would
mean this code still mutates site-packages, which is the practice being
retired. Delete it once per environment, or let the next image rebuild clear
it:

```
rm -f "$(python -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')/_scitex_container_subprocess_coverage.pth"
```

## [0.4.1]

### Fixed

- **The subprocess-coverage `.pth` shim printed a traceback from every Python
  process on the machine.** It opened with an unconditional `import coverage`,
  and a `.pth` runs at interpreter startup inside `site` — before any
  application code exists to catch anything. On an interpreter without
  coverage installed, `site` printed a `ModuleNotFoundError` traceback to
  stderr and carried on. Every command in every container carried it; one
  `curl | python3` emitted four tracebacks before two lines of real output.

  The cost was never the noise. It is that people learn to skim past stderr,
  which is precisely where the next real error appears.

  The shim now checks `COVERAGE_PROCESS_START` **first** and only then imports
  coverage, guarded:

  ```python
  import os
  if os.environ.get('COVERAGE_PROCESS_START'):
      try:
          import coverage
      except ImportError:
          pass
      else:
          coverage.process_startup()
  ```

  Ordering the env check before the import is not just a tidier spelling of
  the guard: a non-test process now imports *nothing*, rather than paying for
  a coverage import it was never going to use. A `.pth` should be the cheapest
  and quietest thing in the process.

  Fixed in the GENERATOR (`tests/conftest.py::_ensure_subprocess_coverage_shim`),
  which rewrites the artifact whenever its content differs — so the file is
  corrected on the next test run rather than needing a manual edit. Existing
  installs keep the old shim until then.

## [0.4.0]

### Added

- **`build_reproducible()` / `verify_roundtrip()` accept `cwd`** — the build
  context apptainer resolves a recipe's relative `%files` sources and
  `From: ./<other>.sif` layer references against. Forwarded to *both* the
  rough build and the verify rebuild, so the replay resolves the same staged
  inputs the rough build did.

  Without it the round-trip was **unreachable** for any consumer whose recipe
  reads from a staged build context rather than from the containers dir: the
  relative `%files` do not exist relative to `root`, and apptainer FATALs
  before running a line of `%post`. That was the entire reason this
  round-trip shipped with no callers — `scitex-agent-container` stages its
  own source tree beside the `.def` so the SIF pins the source that shipped
  the recipe, and could not call in.

- **`_store.publish()`** — publishes a build through *both* stable symlinks
  (the inner `<layer>/<layer>.sif` boot path and the top-level
  `<layer>.sif`). `_build._publish_atomic` now delegates to it, so the plain
  build and the reproducible round-trip publish identically.

### Fixed

- **`build_reproducible` left the boot symlink stale.** It published via
  `point_latest`, which writes only the TOP-level link, so a consumer that
  boots off the inner `<layer>/<layer>.sif` kept resolving the PREVIOUS
  build while the store advertised the new one — a reproducible build nobody
  ran. It now publishes through `_store.publish`.

- **The recipe snapshot could describe a build that never finished.**
  `_build` copied the `.def` beside the artifact at build START while writing
  `.def-hash` only on SUCCESS, so an interrupted or failing build left a
  snapshot permanently disagreeing with the hash next to it. (Measured on a
  live host 2026-08-12: the `.def` hashed `b7564978…`, `.def-hash` said
  `47c7bbfc…`, and the live SIF was neither.) Both are now written together,
  on success; a failed build leaves the previous build's pair intact.

- **Auto-freeze is artifact-scoped.** After a successful build the version
  set is captured to `<image_dir>/<name>-<ts>.lock` via `capture_lock`,
  replacing the three fixed-name files (`requirements-lock.txt` /
  `dpkg-lock.txt` / `node-lock.txt`) written at the containers ROOT. That
  layout had three faults: a second layer's build overwrote the first
  layer's record (nothing tied a lock to the SIF it described); `freeze`
  execs without `--cleanenv --no-home`, so apptainer auto-mounted `$HOME`
  and `pip freeze` captured the HOST environment; and root-level fixed names
  outlived every retention sweep. `<name>-<ts>.lock` is host-isolated and is
  exactly the path `_store._remove_build` already prunes. The explicit
  `container freeze` verb and `_freeze.freeze` itself are unchanged.

### Changed

- The use-time gate (`check_verified`, `VerifyStatus`, `VerifyError`) moved
  from `_reproducible` into a new `_verify_gate` module — the read side, run
  on every image use, split from the write side that runs once per build.
  Re-exported from `_reproducible`, so every existing import still resolves.

## [0.3.0]

### Added

- `apptainer.build()` is now the SSOT for **safe SIF builds**: it builds
  into a fresh timestamped `<name>/<name>-<ts>.sif` and, on success,
  atomically repoints two stable symlinks (temp symlink + `os.replace`,
  via the new `_store.atomic_symlink` primitive) — the inner
  `<name>/<name>.sif` (the path consumers boot from) and the top-level
  `<name>.sif` (for cross-layer `From: ./<name>.sif`). A live image is
  never overwritten in place; a failed build leaves the prior symlinks
  and their targets intact.
- `build(..., cwd=...)`: explicit build context — the directory apptainer
  resolves the recipe's relative `%files` and `From: ./<other>.sif`
  against — settable independently of `output_dir` (defaults to
  `output_dir`, fully back-compatible).
- `build(..., retain=N)`: keep the last N *previous* timestamped SIFs for
  rollback (the live build is always kept). Defaults to the image
  config's `retain`; reuses `_store.prune`.
- `_store.atomic_symlink(link, rel_target)`: reusable atomic symlink-swap
  primitive; `point_latest` now builds on it.

### Changed

- A successful SIF `build()` returns the resolved real timestamped SIF
  (`<name>-<ts>.sif`); `<name>/<name>.sif` and `<name>.sif` are stable
  symlinks pointing at it. Consumers booting from the inner
  `<name>/<name>.sif` path are unaffected.

## [0.1.10]

- Initial CHANGELOG entry — see git log for prior history.
