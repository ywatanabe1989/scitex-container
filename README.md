# scitex-container

<p align="center">
  <a href="https://scitex.ai">
    <img src="docs/scitex-logo-blue-cropped.png" alt="SciTeX" width="400">
  </a>
</p>

<p align="center"><b>Unified container management for Apptainer and Docker</b></p>

<p align="center">
  <a href="https://badge.fury.io/py/scitex-container"><img src="https://badge.fury.io/py/scitex-container.svg" alt="PyPI version"></a>
  <a href="https://scitex-container.readthedocs.io/"><img src="https://readthedocs.org/projects/scitex-container/badge/?version=latest" alt="Documentation"></a>
  <a href="https://github.com/ywatanabe1989/scitex-container/actions/workflows/ci.yml"><img src="https://github.com/ywatanabe1989/scitex-container/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
</p>

<p align="center">
  <a href="https://scitex-container.readthedocs.io/">Full Documentation</a> · <code>pip install scitex-container</code>
</p>

---

## Installation

Requires Python >= 3.10.

```bash
pip install scitex-container
```

With MCP server support (for AI agent integration):

```bash
pip install scitex-container[mcp]
```

Full installation:

```bash
pip install scitex-container[all]
```

## CLI Quickstart

```bash
# Unified status dashboard
scitex-container status

# Build Apptainer SIF from definition file
scitex-container build --def-name scitex-final

# Version management
scitex-container list
scitex-container switch 2.19.5
scitex-container rollback

# Show all commands
scitex-container --help-recursive
```

<details>
<summary><strong>Sandbox Operations</strong></summary>

<br>

```bash
scitex-container sandbox create --sif scitex-final.sif
scitex-container sandbox maintain --sandbox scitex-sandbox/
```

</details>

<details>
<summary><strong>Host Package Management</strong></summary>

<br>

```bash
scitex-container host install          # Install TeX Live + ImageMagick
scitex-container host check            # Verify host packages
scitex-container host mounts           # Show configured bind mounts
```

</details>

<details>
<summary><strong>Docker Operations</strong></summary>

<br>

```bash
scitex-container docker rebuild        # Rebuild Compose services
scitex-container docker restart        # Restart services
```

</details>

<details>
<summary><strong>Verification & Reproducibility</strong></summary>

<br>

```bash
scitex-container verify                # Verify SIF integrity against lock files
scitex-container env-snapshot          # Capture environment reproducibility snapshot
scitex-container env-snapshot --json   # JSON output for Clew integration
```

</details>

## Python API

```python
import scitex_container as sc

# Apptainer container management
sc.apptainer.build(def_name="scitex-final", sandbox=True)
sc.apptainer.list_versions(containers_dir="/opt/containers")
sc.apptainer.switch_version("2.19.5", containers_dir="/opt/containers")
sc.apptainer.rollback(containers_dir="/opt/containers")

# Host package management
sc.host.check_packages()

# Docker operations
sc.docker.rebuild(env="prod")
sc.docker.restart(env="prod")

# Environment reproducibility snapshot (Clew integration point)
snapshot = sc.env_snapshot()
```

<details>
<summary><strong>Verification API</strong></summary>

<br>

```python
# Verify container integrity
result = sc.apptainer.verify(sif_path="/opt/containers/scitex-final.sif")
# Returns: {sif, def_origin, pip_lock, dpkg_lock, overall}

# Command builder for scitex-cloud terminal integration
args = sc.apptainer.build_exec_args(
    container_path="/opt/containers/scitex-final.sif",
    username="user01",
    host_user_dir=Path("/data/users/user01"),
    host_project_dir=Path("/data/projects/proj01"),
    project_slug="proj01",
    texlive_prefix="/usr",
)
```

</details>

## MCP Server

<details>
<summary><strong>AI Agent Integration</strong></summary>

<br>

scitex-container exposes an MCP server so AI agents (Claude, etc.) can
manage containers autonomously.

```bash
# Start MCP server
scitex-container-mcp

# Install to Claude Code
scitex-container mcp install
```

| Tool | Description |
|------|-------------|
| `status` | Unified container/host status dashboard |
| `build` | Build SIF from definition file |
| `list` | List available container versions |
| `switch` | Switch active container version |
| `rollback` | Roll back to previous version |
| `sandbox_create` | Create writable sandbox from SIF |
| `docker_rebuild` | Rebuild Docker Compose services |
| `host_install` | Install host-side packages |
| `env_snapshot` | Capture reproducibility snapshot |
| `verify` | Verify SIF integrity against lock files |

</details>

---

> AGPL-3.0 — because research infrastructure deserves the same freedoms as the software it runs on.

<p align="center">
  <a href="https://scitex.ai" target="_blank"><img src="docs/scitex-icon-navy-inverted.png" alt="SciTeX" width="40"/></a>
</p>

<!-- EOF -->
