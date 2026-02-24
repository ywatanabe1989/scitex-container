#!/usr/bin/env python3
# Timestamp: "2026-02-25"
# File: src/scitex_container/_cli/_mcp.py
"""MCP CLI sub-group for scitex-container.

Commands:
- scitex-container mcp list-tools   List all registered MCP tools
- scitex-container mcp doctor       Check FastMCP availability and tool health
- scitex-container mcp start        Start the MCP server
"""

from __future__ import annotations

import click


@click.group(invoke_without_command=True)
@click.option("--help-recursive", is_flag=True, help="Show help for all subcommands")
@click.pass_context
def mcp(ctx, help_recursive):
    """MCP (Model Context Protocol) server management."""
    if help_recursive:
        _print_help_recursive(ctx)
        ctx.exit(0)
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _print_help_recursive(ctx):
    """Print help for mcp and all its subcommands."""
    fake_parent = click.Context(click.Group(), info_name="scitex-container")
    parent_ctx = click.Context(mcp, info_name="mcp", parent=fake_parent)

    click.secho("━━━ scitex-container mcp ━━━", fg="cyan", bold=True)
    click.echo(mcp.get_help(parent_ctx))

    for name in sorted(mcp.list_commands(ctx) or []):
        cmd = mcp.get_command(ctx, name)
        if cmd is None:
            continue
        click.echo()
        click.secho(f"━━━ scitex-container mcp {name} ━━━", fg="cyan", bold=True)
        with click.Context(cmd, info_name=name, parent=parent_ctx) as sub_ctx:
            click.echo(cmd.get_help(sub_ctx))


def _format_tool_signature(tool_name: str, tool_obj) -> str:
    """Format an MCP tool as a Python-like function signature."""
    if not hasattr(tool_obj, "parameters") or not tool_obj.parameters:
        return f"  {click.style(tool_name, fg='green', bold=True)}()"

    schema = tool_obj.parameters
    props = schema.get("properties", {})
    required = schema.get("required", [])

    params = []
    for name, info in props.items():
        ptype = info.get("type", "any")
        default = info.get("default")
        if name in required:
            p = f"{click.style(name, fg='white', bold=True)}: {click.style(ptype, fg='cyan')}"
        elif default is not None:
            def_str = repr(default) if len(repr(default)) < 20 else "..."
            p = (
                f"{click.style(name, fg='white', bold=True)}: "
                f"{click.style(ptype, fg='cyan')} = {click.style(def_str, fg='yellow')}"
            )
        else:
            p = (
                f"{click.style(name, fg='white', bold=True)}: "
                f"{click.style(ptype, fg='cyan')} = {click.style('None', fg='yellow')}"
            )
        params.append(p)

    name_s = click.style(tool_name, fg="green", bold=True)
    return f"  {name_s}({', '.join(params)})"


@mcp.command("list-tools")
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v signatures, -vv +description"
)
def list_tools(verbose: int):
    """List all registered MCP tools with signatures."""
    try:
        from scitex_container.mcp_server import FASTMCP_AVAILABLE
        from scitex_container.mcp_server import mcp as mcp_server
    except ImportError:
        click.secho("ERROR: Could not import MCP server", fg="red", err=True)
        raise SystemExit(1) from None

    if not FASTMCP_AVAILABLE:
        click.secho(
            "ERROR: FastMCP not installed. Run: pip install 'scitex-container[mcp]'",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    if mcp_server is None:
        click.secho("ERROR: MCP server not initialized", fg="red", err=True)
        raise SystemExit(1)

    # Collect tools via FastMCP internal registry
    try:
        tools_map = mcp_server._tool_manager._tools
    except AttributeError:
        tools_map = getattr(mcp_server, "_tools", {})

    if not tools_map:
        click.secho("No tools registered (or unable to inspect).", fg="yellow")
        return

    click.secho(f"scitex-container MCP: {len(tools_map)} tools", fg="cyan", bold=True)
    click.echo()

    for tool_name in sorted(tools_map.keys()):
        tool_obj = tools_map[tool_name]
        if verbose == 0:
            click.echo(f"  {tool_name}")
        elif verbose == 1:
            click.echo(_format_tool_signature(tool_name, tool_obj))
        else:
            click.echo(_format_tool_signature(tool_name, tool_obj))
            desc = getattr(tool_obj, "description", None)
            if desc and isinstance(desc, str):
                click.echo(f"    {desc.split(chr(10))[0].strip()}")
            elif hasattr(tool_obj, "fn") and tool_obj.fn:
                import inspect

                docstring = inspect.getdoc(tool_obj.fn)
                if docstring:
                    click.echo(f"    {docstring.split(chr(10))[0].strip()}")
            click.echo()


@mcp.command("doctor")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diagnostics")
def doctor(verbose: bool):
    """Check FastMCP availability and MCP tool health."""
    issues = []

    click.secho("scitex-container MCP Doctor", fg="cyan", bold=True)
    click.echo()

    # Check 1: FastMCP installation
    click.echo("Checking FastMCP installation... ", nl=False)
    try:
        from fastmcp import FastMCP  # noqa: F401

        click.secho("OK", fg="green")
        if verbose:
            import fastmcp

            click.echo(f"  Version: {getattr(fastmcp, '__version__', 'unknown')}")
    except ImportError:
        click.secho("FAIL", fg="red")
        issues.append("FastMCP not installed. Run: pip install 'scitex-container[mcp]'")

    # Check 2: MCP server import
    click.echo("Checking MCP server module... ", nl=False)
    try:
        from scitex_container.mcp_server import FASTMCP_AVAILABLE
        from scitex_container.mcp_server import mcp as mcp_server

        if FASTMCP_AVAILABLE and mcp_server is not None:
            click.secho("OK", fg="green")
        else:
            click.secho("WARN", fg="yellow")
    except ImportError as e:
        click.secho("FAIL", fg="red")
        issues.append(f"Could not import MCP server: {e}")

    # Check 3: Handler imports
    click.echo("Checking MCP handlers... ", nl=False)
    try:
        from scitex_container._mcp.handlers import (  # noqa: F401
            build_handler,
            host_check_handler,
            status_handler,
        )

        click.secho("OK", fg="green")
    except ImportError as e:
        click.secho("FAIL", fg="red")
        issues.append(f"Could not import handlers: {e}")

    # Check 4: Tool count
    click.echo("Checking tool registration... ", nl=False)
    try:
        from scitex_container.mcp_server import mcp as mcp_server

        if mcp_server is not None:
            try:
                tools_map = mcp_server._tool_manager._tools
            except AttributeError:
                tools_map = getattr(mcp_server, "_tools", {})
            n = len(tools_map)
            if n >= 10:
                click.secho(f"OK ({n} tools)", fg="green")
            else:
                click.secho(f"WARN ({n} tools, expected 10+)", fg="yellow")
        else:
            click.secho("SKIP (FastMCP unavailable)", fg="yellow")
    except Exception as e:
        click.secho("FAIL", fg="red")
        issues.append(f"Tool registration check failed: {e}")

    # Summary
    click.echo()
    if issues:
        click.secho(f"Issues Found: {len(issues)}", fg="red", bold=True)
        for issue in issues:
            click.echo(f"  x {issue}")
    else:
        click.secho("All checks passed!", fg="green", bold=True)

    raise SystemExit(1 if issues else 0)


@mcp.command("start")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "sse", "http"]),
    default="stdio",
    help="Transport type (default: stdio)",
)
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
@click.option(
    "--port", "-p", default=8086, type=int, help="Port to bind (default: 8086)"
)
def start(transport: str, host: str, port: int):
    """Start the MCP server."""
    try:
        from scitex_container.mcp_server import FASTMCP_AVAILABLE
        from scitex_container.mcp_server import mcp as mcp_server
    except ImportError:
        click.secho("ERROR: Could not import MCP server", fg="red", err=True)
        click.echo("Run: pip install 'scitex-container[mcp]'")
        raise SystemExit(1) from None

    if not FASTMCP_AVAILABLE or mcp_server is None:
        click.secho(
            "ERROR: MCP server not available (FastMCP missing)", fg="red", err=True
        )
        raise SystemExit(1)

    click.secho(f"Starting MCP server (transport={transport})...", fg="cyan")
    if transport == "stdio":
        mcp_server.run(transport="stdio")
    else:
        mcp_server.run(transport=transport, host=host, port=port)


# EOF
