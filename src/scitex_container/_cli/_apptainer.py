#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/_cli/_apptainer.py
"""CLI commands for Apptainer container operations."""

from __future__ import annotations

import click


def register(main: click.Group) -> None:
    """Register all Apptainer commands onto main."""
    main.add_command(build)
    main.add_command(list_containers)
    main.add_command(switch)
    main.add_command(rollback)
    main.add_command(deploy)
    main.add_command(cleanup)
    main.add_command(verify)


@click.command()
@click.argument("name", default="scitex-final")
@click.option(
    "--sandbox", is_flag=True, help="Build a sandbox directory instead of SIF."
)
@click.option("--base", is_flag=True, help="Build the base image instead of final.")
@click.option("--force", "-f", is_flag=True, help="Force rebuild even if up-to-date.")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory.")
def build(name, sandbox, base, force, output_dir):
    """Build a SIF or sandbox from a .def file."""
    from scitex_container.apptainer import build as do_build

    try:
        output_path = do_build(
            def_name=name,
            output_dir=output_dir,
            force=force,
            sandbox=sandbox,
        )
        click.secho(f"Built: {output_path}", fg="green")
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)
    except RuntimeError as exc:
        click.secho(f"Build failed: {exc}", fg="red", err=True)
        click.secho(
            "Tip: check that apptainer is installed and the .def file exists.",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)


@click.command(name="list")
@click.option(
    "--dir", "-d", "containers_dir", type=click.Path(), help="Containers directory."
)
def list_containers(containers_dir):
    """List available container versions."""
    from pathlib import Path

    from scitex_container.apptainer import (
        find_containers_dir,
        get_active_version,
        list_versions,
    )

    try:
        cdir = Path(containers_dir) if containers_dir else find_containers_dir()
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)

    versions = list_versions(cdir)
    if not versions:
        click.echo(f"No versioned SIFs found in {cdir}")
        return

    active = get_active_version(cdir)
    click.secho(f"Container versions in {cdir}:", fg="cyan")
    for v in versions:
        marker = click.style(" *", fg="green") if v["active"] else "  "
        version_str = click.style(v["version"], fg="green" if v["active"] else "white")
        click.echo(f"  {marker} {version_str}  {v['size']}  {v['date']}")

    if active:
        click.echo()
        click.echo(f"  Active: {click.style(active, fg='green', bold=True)}")


@click.command()
@click.argument("version")
@click.option(
    "--dir", "-d", "containers_dir", type=click.Path(), help="Containers directory."
)
@click.option(
    "--sudo", "use_sudo", is_flag=True, help="Use sudo for symlink operations."
)
def switch(version, containers_dir, use_sudo):
    """Switch active container to VERSION."""
    from pathlib import Path

    from scitex_container.apptainer import (
        find_containers_dir,
        get_active_version,
        switch_version,
    )

    try:
        cdir = Path(containers_dir) if containers_dir else find_containers_dir()
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)

    old_version = get_active_version(cdir)

    try:
        switch_version(version, cdir, use_sudo=use_sudo)
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        click.secho(
            "Tip: run 'scitex-container list' to see available versions.",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)
    except RuntimeError as exc:
        click.secho(f"Switch failed: {exc}", fg="red", err=True)
        raise SystemExit(1)

    if old_version:
        click.secho(f"Switched {old_version} -> {version}", fg="green")
    else:
        click.secho(f"Activated version {version}", fg="green")


@click.command()
@click.option(
    "--dir", "-d", "containers_dir", type=click.Path(), help="Containers directory."
)
@click.option(
    "--sudo", "use_sudo", is_flag=True, help="Use sudo for symlink operations."
)
def rollback(containers_dir, use_sudo):
    """Revert to the previous container version."""
    from pathlib import Path

    from scitex_container.apptainer import find_containers_dir, get_active_version
    from scitex_container.apptainer import rollback as do_rollback

    try:
        cdir = Path(containers_dir) if containers_dir else find_containers_dir()
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)

    old_version = get_active_version(cdir)

    try:
        new_version = do_rollback(cdir, use_sudo=use_sudo)
    except RuntimeError as exc:
        click.secho(f"Rollback failed: {exc}", fg="red", err=True)
        click.secho(
            "Tip: rollback requires at least two versions to be present.",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)

    click.secho(f"Rolled back {old_version} -> {new_version}", fg="green")


@click.command()
@click.option(
    "--target",
    "-t",
    "target_dir",
    type=click.Path(),
    default="/opt/scitex/singularity",
    show_default=True,
    help="Deployment target directory.",
)
@click.option(
    "--dir",
    "-d",
    "containers_dir",
    type=click.Path(),
    help="Source containers directory.",
)
def deploy(target_dir, containers_dir):
    """Copy active SIF to production target directory."""
    from pathlib import Path

    from scitex_container.apptainer import find_containers_dir
    from scitex_container.apptainer import deploy as do_deploy

    try:
        cdir = Path(containers_dir) if containers_dir else find_containers_dir()
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)

    try:
        do_deploy(source_dir=cdir, target_dir=Path(target_dir))
    except (FileNotFoundError, RuntimeError) as exc:
        click.secho(f"Deploy failed: {exc}", fg="red", err=True)
        click.secho(
            "Tip: ensure an active version is set (run 'scitex-container switch').",
            fg="yellow",
            err=True,
        )
        raise SystemExit(1)

    click.secho(f"Deployed to {target_dir}", fg="green")


@click.command()
@click.option(
    "--keep",
    "-k",
    type=int,
    default=3,
    show_default=True,
    help="Number of recent versions to keep.",
)
@click.option(
    "--dir", "-d", "containers_dir", type=click.Path(), help="Containers directory."
)
def cleanup(keep, containers_dir):
    """Remove old container versions, keeping the N most recent."""
    from pathlib import Path

    from scitex_container.apptainer import find_containers_dir
    from scitex_container.apptainer import cleanup as do_cleanup

    try:
        cdir = Path(containers_dir) if containers_dir else find_containers_dir()
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)

    removed = do_cleanup(cdir, keep=keep)

    if removed:
        click.secho(f"Removed {len(removed)} old version(s):", fg="yellow")
        for path in removed:
            click.echo(f"  {path.name}")
    else:
        click.secho("No old versions to remove.", fg="green")


@click.command()
@click.argument("sif_path", required=False)
@click.option("--def", "def_path", help="Path to .def file to verify against.")
@click.option("--lock-dir", help="Directory containing lock files.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def verify(sif_path, def_path, lock_dir, as_json):
    """Verify SIF integrity: hash, .def origin, and lock file consistency."""
    import json as json_mod

    from scitex_container.apptainer import (
        find_containers_dir,
        get_active_version,
        verify as do_verify,
    )

    if not sif_path:
        try:
            cdir = find_containers_dir()
            active = get_active_version(cdir)
            if active:
                sif_path = str(cdir / f"scitex-v{active}.sif")
            else:
                click.secho(
                    "No active SIF found. Provide SIF_PATH argument.",
                    fg="red",
                    err=True,
                )
                raise SystemExit(1)
        except FileNotFoundError as exc:
            click.secho(str(exc), fg="red", err=True)
            raise SystemExit(1)

    result = do_verify(sif_path=sif_path, def_path=def_path, lock_dir=lock_dir)

    if as_json:
        click.echo(json_mod.dumps(result, indent=2))
    else:
        _print_verify_result(result)

    raise SystemExit(0 if result["overall"] == "pass" else 1)


def _print_verify_result(result: dict) -> None:
    """Pretty-print verification results."""
    status_colors = {"pass": "green", "fail": "red", "skip": "yellow"}

    click.secho("Container Verification Report", fg="cyan", bold=True)
    click.echo()

    # SIF
    sif = result["sif"]
    click.echo(f"  SIF: {sif['path']}")
    if sif["exists"]:
        click.echo(f"  SHA256: {sif['sha256']}")
    else:
        click.secho("  NOT FOUND", fg="red")
    click.echo()

    # Checks
    for check_name, label in [
        ("def_origin", ".def Origin"),
        ("pip_lock", "pip Packages"),
        ("dpkg_lock", "dpkg Packages"),
    ]:
        check = result[check_name]
        status = check["status"]
        color = status_colors.get(status, "white")
        badge = click.style(f"[{status.upper()}]", fg=color, bold=True)
        click.echo(f"  {badge} {label}: {check['detail']}")

    click.echo()
    overall = result["overall"]
    color = "green" if overall == "pass" else "red"
    click.secho(f"  Overall: {overall.upper()}", fg=color, bold=True)


# EOF
