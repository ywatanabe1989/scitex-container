#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/mcp_server.py
"""FastMCP server for scitex-container.

Usage:
    scitex-container-mcp               # stdio (Claude Desktop)
    python -m scitex_container mcp     # alternative entry point
"""

from __future__ import annotations

try:
    from fastmcp import FastMCP

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None  # type: ignore

__all__ = ["mcp", "main", "FASTMCP_AVAILABLE"]

if FASTMCP_AVAILABLE:
    mcp = FastMCP(
        name="scitex-container",
        instructions="""\
scitex-container: Container management for Apptainer/Singularity and Docker.

## Available Tools

### Apptainer container operations
- container_build     — Build a SIF or sandbox from a .def file
- container_list      — List versioned SIFs with active marker
- container_switch    — Switch active container version
- container_rollback  — Roll back to the previous version
- container_deploy    — Copy active SIF to production target
- container_cleanup   — Remove old versions (keep N most recent)

### Sandbox operations
- sandbox_create      — Convert a SIF to a writable sandbox directory

### Docker Compose operations
- docker_rebuild      — Rebuild images without cache
- docker_restart      — Restart containers (down + up -d)

### Host package management
- host_install        — Install TeXLive / ImageMagick on the host
- host_check          — Check which host packages are installed

### Unified status
- container_status    — Dashboard: Apptainer + host packages + Docker

### Integrity verification
- container_verify    — Verify SIF SHA256, .def origin, and lock file consistency

### Clew reproducibility
- container_env_snapshot — Capture environment snapshot (container + host + git)
""",
    )
else:
    mcp = None


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------

if FASTMCP_AVAILABLE and mcp is not None:

    @mcp.tool()
    async def container_build(
        name: str = "scitex-final",
        sandbox: bool = False,
        force: bool = False,
        base: bool = False,
    ) -> dict:
        """Build an Apptainer SIF or sandbox from a .def file.

        Args:
            name: Name of the .def file (without extension).
            sandbox: Build a sandbox directory instead of a SIF.
            force: Force rebuild even if the .def is unchanged.
            base: Build the base image instead of the final image.
        """
        from ._mcp.handlers import build_handler

        return await build_handler(name=name, sandbox=sandbox, force=force, base=base)

    @mcp.tool()
    async def container_list(containers_dir: str = "") -> dict:
        """List all versioned SIFs and mark the active one.

        Args:
            containers_dir: Path to containers directory (auto-detected if empty).
        """
        from ._mcp.handlers import list_handler

        return await list_handler(containers_dir=containers_dir or None)

    @mcp.tool()
    async def container_switch(
        version: str,
        containers_dir: str = "",
        use_sudo: bool = False,
    ) -> dict:
        """Switch the active container to VERSION.

        Args:
            version: Target version string (e.g. "2.19.5").
            containers_dir: Path to containers directory (auto-detected if empty).
            use_sudo: Use sudo for symlink operations (needed for /opt paths).
        """
        from ._mcp.handlers import switch_handler

        return await switch_handler(
            version=version,
            containers_dir=containers_dir or None,
            use_sudo=use_sudo,
        )

    @mcp.tool()
    async def container_rollback(
        containers_dir: str = "",
        use_sudo: bool = False,
    ) -> dict:
        """Roll back to the previous container version.

        Args:
            containers_dir: Path to containers directory (auto-detected if empty).
            use_sudo: Use sudo for symlink operations.
        """
        from ._mcp.handlers import rollback_handler

        return await rollback_handler(
            containers_dir=containers_dir or None,
            use_sudo=use_sudo,
        )

    @mcp.tool()
    async def container_deploy(
        target_dir: str = "/opt/scitex/singularity",
        containers_dir: str = "",
    ) -> dict:
        """Copy the active SIF to a production target directory.

        Args:
            target_dir: Deployment target path.
            containers_dir: Source containers directory (auto-detected if empty).
        """
        from ._mcp.handlers import deploy_handler

        return await deploy_handler(
            target_dir=target_dir,
            containers_dir=containers_dir or None,
        )

    @mcp.tool()
    async def container_cleanup(
        keep: int = 3,
        containers_dir: str = "",
    ) -> dict:
        """Remove old container versions, keeping the N most recent.

        Args:
            keep: Number of recent versions to keep.
            containers_dir: Containers directory (auto-detected if empty).
        """
        from ._mcp.handlers import cleanup_handler

        return await cleanup_handler(keep=keep, containers_dir=containers_dir or None)

    @mcp.tool()
    async def container_status() -> dict:
        """Show unified status: Apptainer versions, host packages, Docker services."""
        from ._mcp.handlers import status_handler

        return await status_handler()

    @mcp.tool()
    async def sandbox_create(
        source_sif: str,
        output_dir: str = "",
        force: bool = False,
    ) -> dict:
        """Convert a SIF image into a writable Apptainer sandbox directory.

        Args:
            source_sif: Path to the source .sif file.
            output_dir: Output sandbox path (defaults to <sif_stem>-sandbox/).
            force: Overwrite if the sandbox already exists.
        """
        from ._mcp.handlers import sandbox_create_handler

        return await sandbox_create_handler(
            source_sif=source_sif,
            output_dir=output_dir or None,
            force=force,
        )

    @mcp.tool()
    async def docker_rebuild(env: str = "dev") -> dict:
        """Rebuild Docker containers without cache.

        Args:
            env: Environment name used to locate the compose file (dev/prod).
        """
        from ._mcp.handlers import docker_rebuild_handler

        return await docker_rebuild_handler(env=env)

    @mcp.tool()
    async def docker_restart(env: str = "dev") -> dict:
        """Restart Docker containers (compose down + up -d).

        Args:
            env: Environment name (dev/prod).
        """
        from ._mcp.handlers import docker_restart_handler

        return await docker_restart_handler(env=env)

    @mcp.tool()
    async def host_install(
        texlive: bool = False,
        imagemagick: bool = False,
        all: bool = True,  # noqa: A002
    ) -> dict:
        """Install host packages (TeXLive, ImageMagick) required by SciTeX containers.

        Args:
            texlive: Install TeXLive packages.
            imagemagick: Install ImageMagick.
            all: Install all packages (default when no specific flag is set).
        """
        from ._mcp.handlers import host_install_handler

        return await host_install_handler(
            texlive=texlive, imagemagick=imagemagick, all=all
        )

    @mcp.tool()
    async def host_check() -> dict:
        """Check which host packages (TeXLive, ImageMagick) are installed."""
        from ._mcp.handlers import host_check_handler

        return await host_check_handler()

    @mcp.tool()
    async def container_verify(
        sif_path: str = "",
        def_path: str = "",
        lock_dir: str = "",
    ) -> dict:
        """Verify SIF integrity: SHA256 hash, .def origin check, lock file comparison.

        Args:
            sif_path: Path to .sif to verify (defaults to active SIF).
            def_path: Path to .def file to verify origin against.
            lock_dir: Directory with lock files (defaults to SIF directory).
        """
        from ._mcp.handlers import verify_handler

        return await verify_handler(
            sif_path=sif_path, def_path=def_path, lock_dir=lock_dir
        )

    @mcp.tool()
    async def container_env_snapshot(
        containers_dir: str = "",
        dev_repos: str = "",
    ) -> dict:
        """Capture environment snapshot for Clew reproducibility tracking.

        Returns JSON with container version, SIF hash, host package versions,
        dev repo git commits, and lock file hashes.

        Args:
            containers_dir: Path to containers directory (auto-detected if empty).
            dev_repos: Comma-separated paths to git repos to include.
        """
        from ._mcp.handlers import env_snapshot_handler

        repos = (
            [r.strip() for r in dev_repos.split(",") if r.strip()]
            if dev_repos
            else None
        )
        return await env_snapshot_handler(
            containers_dir=containers_dir or None,
            dev_repos=repos,
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for scitex-container-mcp command (stdio transport)."""
    if not FASTMCP_AVAILABLE:
        import sys

        print("=" * 60)
        print("fastmcp is required: pip install 'scitex-container[mcp]'")
        print("=" * 60)
        sys.exit(1)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

# EOF
