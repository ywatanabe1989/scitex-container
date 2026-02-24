#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/_cli/__init__.py
"""CLI package for scitex-container.

Entry point: scitex-container  (maps to main() here)
"""

from __future__ import annotations

import inspect

import click

from ._apptainer import (
    build,
    cleanup,
    deploy,
    list_containers,
    rollback,
    switch,
    verify,
)
from ._docker import docker
from ._env_snapshot import env_snapshot_cmd
from ._host import host
from ._mcp import mcp
from ._sandbox import sandbox
from ._status import status


def _print_help_recursive(ctx, group, prefix="scitex-container"):
    """Recursively print help for a group and all its subcommands/subgroups."""
    click.secho(f"━━━ {prefix} ━━━", fg="cyan", bold=True)
    click.echo(group.get_help(ctx))

    commands = group.list_commands(ctx) or []
    for name in sorted(commands):
        cmd = group.get_command(ctx, name)
        if cmd is None:
            continue
        sub_prefix = f"{prefix} {name}"
        with click.Context(cmd, info_name=name, parent=ctx) as sub_ctx:
            click.echo()
            if isinstance(cmd, click.Group):
                _print_help_recursive(sub_ctx, cmd, prefix=sub_prefix)
            else:
                click.secho(f"━━━ {sub_prefix} ━━━", fg="cyan", bold=True)
                click.echo(cmd.get_help(sub_ctx))


@click.group()
@click.version_option(package_name="scitex-container")
@click.option(
    "--help-recursive", is_flag=True, help="Show help for all commands recursively"
)
@click.pass_context
def main(ctx, help_recursive):
    """scitex-container: Unified container management (Apptainer + Docker + host)."""
    if help_recursive:
        _print_help_recursive(ctx, main)
        ctx.exit(0)


# Apptainer commands (top-level)
main.add_command(build)
main.add_command(list_containers)
main.add_command(switch)
main.add_command(rollback)
main.add_command(deploy)
main.add_command(cleanup)
main.add_command(verify)

# Sub-groups
main.add_command(sandbox)
main.add_command(docker)
main.add_command(host)
main.add_command(mcp)

# Unified status dashboard
main.add_command(status)

# Clew reproducibility snapshot
main.add_command(env_snapshot_cmd)


@main.command("list-python-apis")
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v with signatures, -vv +docstring"
)
def list_python_apis(verbose: int):
    """List scitex_container Python APIs (apptainer, docker, host modules)."""
    import scitex_container.apptainer as apptainer_mod
    import scitex_container.docker as docker_mod
    import scitex_container.host as host_mod

    modules = [
        ("apptainer", apptainer_mod),
        ("docker", docker_mod),
        ("host", host_mod),
    ]

    for mod_name, mod in modules:
        public_names = [n for n in dir(mod) if not n.startswith("_")]
        click.secho(f"{mod_name}: {len(public_names)} APIs", fg="green", bold=True)

        for name in sorted(public_names):
            obj = getattr(mod, name, None)
            if obj is None:
                continue

            if callable(obj) and not isinstance(obj, type):
                if verbose == 0:
                    click.echo(f"  {name}")
                elif verbose >= 1:
                    try:
                        sig_str = str(inspect.signature(obj))
                    except (ValueError, TypeError):
                        sig_str = "()"
                    click.echo(f"  {click.style(name, fg='white', bold=True)}{sig_str}")
                    if verbose >= 2:
                        doc = inspect.getdoc(obj)
                        if doc:
                            first_line = doc.split("\n")[0].strip()
                            click.echo(f"    {first_line}")
            elif isinstance(obj, type):
                click.echo(f"  {name}  [class]")
            else:
                if verbose >= 1:
                    click.echo(f"  {name} = {obj!r}")
                else:
                    click.echo(f"  {name}")

        click.echo()


__all__ = ["main"]

# EOF
