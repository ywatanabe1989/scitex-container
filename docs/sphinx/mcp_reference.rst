MCP Reference
=============

scitex-container exposes an MCP (Model Context Protocol) server so that
AI agents can manage containers autonomously.

Starting the Server
-------------------

.. code-block:: bash

   scitex-container-mcp

Or via the CLI helper:

.. code-block:: bash

   scitex-container mcp install  # Install to Claude Code config

Available MCP Tools
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tool
     - Description
   * - ``status``
     - Show unified container/host status dashboard
   * - ``build``
     - Build a SIF container from a definition file
   * - ``list``
     - List available container versions
   * - ``switch``
     - Switch active container version
   * - ``rollback``
     - Roll back to previous version
   * - ``deploy``
     - Deploy a container version
   * - ``cleanup``
     - Remove old container versions
   * - ``sandbox_create``
     - Create writable sandbox from SIF
   * - ``docker_rebuild``
     - Rebuild Docker Compose services
   * - ``docker_restart``
     - Restart Docker services
   * - ``host_install``
     - Install host-side packages
   * - ``host_check``
     - Check host package status
   * - ``env_snapshot``
     - Capture reproducibility snapshot
