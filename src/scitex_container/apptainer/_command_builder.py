#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/apptainer/_command_builder.py
"""Build apptainer exec arguments for terminal sessions.

All configuration is passed as explicit function parameters so this module
has no dependency on Django settings or any project-specific config files.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._sandbox import is_sandbox

logger = logging.getLogger(__name__)

# TeX Live binary names to bind-mount from the host prefix
_TEXLIVE_BINS = [
    "pdflatex",
    "bibtex",
    "latexmk",
    "latexdiff",
    "kpsewhich",
    "makeindex",
]

# TeX Live share directories to bind-mount from the host prefix
_TEXLIVE_SHARE_DIRS = [
    "texlive",
    "texmf-dist",
]


def build_dev_pythonpath(dev_repos: list[dict]) -> str:
    """Build a PYTHONPATH string that prepends ``/opt/dev/{name}/src`` for each dev repo.

    Packages in dev repos are assumed to follow the src-layout convention
    (i.e. ``repo_root/src/<package>``), so we add ``/opt/dev/{name}/src``.

    Parameters
    ----------
    dev_repos : list[dict]
        List of dev repo dicts, each with a ``name`` key.

    Returns
    -------
    str
        Colon-separated PYTHONPATH string, or empty string if no repos.
    """
    if not dev_repos:
        return ""
    parts = [f"/opt/dev/{repo['name']}/src" for repo in dev_repos]
    return ":".join(parts)


def build_host_mount_binds(
    host_mounts: list[dict] | None = None,
    texlive_prefix: str = "",
) -> list[str]:
    """Build ``--bind`` argument pairs for host package mounts.

    Parameters
    ----------
    host_mounts : list[dict], optional
        Generic list of ``{host_path, container_path, mode}`` dicts.
    texlive_prefix : str
        Host prefix for TeX Live installation (e.g. ``/usr``). When set,
        auto-generates bind entries for TeX Live share directories and binaries.
        Example: ``/usr`` generates:
          ``--bind /usr/share/texlive:/usr/share/texlive:ro``
          ``--bind /usr/share/texmf-dist:/usr/share/texmf-dist:ro``
          ``--bind /usr/bin/pdflatex:/usr/bin/pdflatex:ro``
          ... (all _TEXLIVE_BINS)

    Returns
    -------
    list[str]
        Flat list of alternating ``"--bind"`` / ``"<spec>"`` strings
        ready to be inserted into the apptainer argv list.
    """
    bind_args: list[str] = []

    for mount in host_mounts or []:
        spec = f"{mount['host_path']}:{mount['container_path']}:{mount['mode']}"
        bind_args += ["--bind", spec]
        logger.debug("Host mount: %s", spec)

    if texlive_prefix:
        prefix = texlive_prefix.rstrip("/")

        for share_dir in _TEXLIVE_SHARE_DIRS:
            path = f"{prefix}/share/{share_dir}"
            spec = f"{path}:{path}:ro"
            bind_args += ["--bind", spec]
            logger.debug("TeX Live share mount: %s", spec)

        for binary in _TEXLIVE_BINS:
            path = f"{prefix}/bin/{binary}"
            spec = f"{path}:{path}:ro"
            bind_args += ["--bind", spec]
            logger.debug("TeX Live bin mount: %s", spec)

    return bind_args


def build_exec_args(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
    dev_repos: list[dict] | None = None,
    host_mounts: list[dict] | None = None,
    texlive_prefix: str = "",
) -> list[str]:
    """Build the ``apptainer exec`` argument list.

    Handles:
    - Sandbox vs SIF detection. Both use ``--writable-tmpfs`` for user
      sessions so each user gets a clean per-session tmpfs overlay.
    - For SIF images, ``--containall`` is added to prevent host mounts
      leaking in.
    - Dev repo bind mounts.
    - PYTHONPATH injection for dev repos (src-layout).
    - Host package bind mounts (TeX Live, etc.).
    - Standard ``--env``, ``--home``, ``--bind`` args.

    Parameters
    ----------
    container_path : str
        Path to the SIF file or sandbox directory.
    username : str
        Username for the session (used for home dir and env vars).
    host_user_dir : Path
        Host path to the user's home directory.
    host_project_dir : Path
        Host path to the project directory.
    project_slug : str
        Project identifier (e.g. "my-project").
    dev_repos : list[dict], optional
        Dev repo dicts with ``name`` and ``host_path`` keys.
    host_mounts : list[dict], optional
        Generic host mount dicts with ``host_path``, ``container_path``, ``mode``.
    texlive_prefix : str
        Host prefix for TeX Live (e.g. ``/usr``).

    Returns
    -------
    list[str]
        Flat list starting with ``["apptainer", "exec", ...]``.
    """
    sandbox = is_sandbox(container_path)
    dev_repos = dev_repos or []

    # Dev repo bind mounts
    dev_bind_args: list[str] = []
    for repo in dev_repos:
        spec = f"{repo['host_path']}:/opt/dev/{repo['name']}:ro"
        dev_bind_args += ["--bind", spec]
        logger.debug("Dev mode: mounting %s from %s", repo["name"], repo["host_path"])

    dev_pythonpath = build_dev_pythonpath(dev_repos)
    host_mount_binds = build_host_mount_binds(
        host_mounts=host_mounts,
        texlive_prefix=texlive_prefix,
    )

    args: list[str] = ["apptainer", "exec"]

    # Always isolate — both SIF and sandbox need --containall
    # to prevent host filesystem leakage and ensure user isolation
    args.append("--containall")

    args += [
        "--cleanenv",
        "--writable-tmpfs",
        "--hostname",
        "scitex-cloud",
        "--env",
        "TERM=xterm-256color",
        "--env",
        "SCITEX_CLOUD=true",
        "--env",
        f"SCITEX_PROJECT={project_slug}",
        "--env",
        f"SCITEX_USER={username}",
        "--env",
        f"USER={username}",
        "--env",
        f"LOGNAME={username}",
        "--env",
        "SHELL=/bin/bash",
        "--env",
        "PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin",
    ]

    if dev_pythonpath:
        args += ["--env", f"PYTHONPATH={dev_pythonpath}"]

    args += [
        "--home",
        f"{host_user_dir}:/home/{username}",
        "--bind",
        f"{host_project_dir}:/home/{username}/proj/{project_slug}:rw",
        *dev_bind_args,
        *host_mount_binds,
        "--pwd",
        f"/home/{username}/proj/{project_slug}",
        container_path,
    ]

    return args


def build_srun_command(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
    dev_repos: list[dict] | None = None,
    host_mounts: list[dict] | None = None,
    texlive_prefix: str = "",
    slurm_partition: str = "compute",
    slurm_time_limit: str = "8:00:00",
    slurm_cpus: int = 4,
    slurm_memory_gb: int = 16,
    screen_session: str = "scitex-0",
) -> list[str]:
    """Build the complete ``srun`` + ``apptainer`` command list.

    Combines the SLURM resource flags with the apptainer exec arguments
    produced by ``build_exec_args()``, then appends the screen session
    reattach / create command.

    Parameters
    ----------
    container_path : str
        Path to the SIF file or sandbox directory.
    username : str
        Username for the session.
    host_user_dir : Path
        Host path to the user's home directory.
    host_project_dir : Path
        Host path to the project directory.
    project_slug : str
        Project identifier.
    dev_repos : list[dict], optional
        Dev repo dicts with ``name`` and ``host_path`` keys.
    host_mounts : list[dict], optional
        Generic host mount dicts.
    texlive_prefix : str
        Host prefix for TeX Live.
    slurm_partition : str
        SLURM partition name.
    slurm_time_limit : str
        SLURM time limit (e.g. "8:00:00").
    slurm_cpus : int
        Number of CPUs per task.
    slurm_memory_gb : int
        Memory in GB.
    screen_session : str
        Screen session name for reattach/create.

    Returns
    -------
    list[str]
        Flat list ready to be passed to ``os.execvpe`` or ``subprocess.Popen``.
    """
    apptainer_args = build_exec_args(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        dev_repos=dev_repos,
        host_mounts=host_mounts,
        texlive_prefix=texlive_prefix,
    )

    cmd = [
        "srun",
        "--pty",
        "--chdir=/tmp",
        f"--partition={slurm_partition}",
        f"--time={slurm_time_limit}",
        f"--cpus-per-task={slurm_cpus}",
        f"--mem={slurm_memory_gb}G",
        f"--job-name=terminal_{username}",
        *apptainer_args,
        "/bin/bash",
        "-lc",
        f"exec screen -xRR {screen_session}",
    ]

    return cmd


# EOF
