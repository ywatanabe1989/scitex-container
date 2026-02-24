#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/_cli/_sandbox.py
"""CLI sandbox sub-group for Apptainer sandbox management."""

from __future__ import annotations

import click


@click.group()
def sandbox():
    """Manage Apptainer sandbox directories."""


@sandbox.command(name="create")
@click.option(
    "--source", "-s", "source_sif", type=click.Path(), help="Source SIF file."
)
@click.option(
    "--output", "-o", "output_dir", type=click.Path(), help="Output sandbox directory."
)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing sandbox.")
def sandbox_create(source_sif, output_dir, force):
    """Convert a SIF image into a writable sandbox directory."""
    from pathlib import Path

    from scitex_container.apptainer import sandbox_create as do_create

    if not source_sif:
        click.secho("Error: --source/-s is required.", fg="red", err=True)
        raise SystemExit(1)

    sif_path = Path(source_sif)
    out_path = (
        Path(output_dir)
        if output_dir
        else sif_path.parent / (sif_path.stem + "-sandbox")
    )

    if out_path.exists() and not force:
        click.secho(f"Sandbox already exists: {out_path}", fg="yellow", err=True)
        click.secho("Use --force to overwrite.", fg="yellow", err=True)
        raise SystemExit(1)

    try:
        result = do_create(source_sif=sif_path, output_dir=out_path)
        click.secho(f"Sandbox created: {result}", fg="green")
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)
    except RuntimeError as exc:
        click.secho(f"Sandbox creation failed: {exc}", fg="red", err=True)
        raise SystemExit(1)


@sandbox.command(name="maintain")
@click.argument("command", nargs=-1, required=True)
@click.option("--sandbox-dir", "-s", type=click.Path(), help="Sandbox directory path.")
def sandbox_maintain(command, sandbox_dir):
    """Run a maintenance COMMAND inside a sandbox (writable + fakeroot)."""
    from pathlib import Path

    from scitex_container.apptainer import sandbox_maintain as do_maintain

    if not sandbox_dir:
        click.secho("Error: --sandbox-dir/-s is required.", fg="red", err=True)
        raise SystemExit(1)

    try:
        rc = do_maintain(sandbox_dir=Path(sandbox_dir), command=list(command))
        if rc != 0:
            click.secho(f"Command exited with code {rc}", fg="yellow", err=True)
            raise SystemExit(rc)
        click.secho("Maintenance command completed.", fg="green")
    except FileNotFoundError as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1)


# EOF
