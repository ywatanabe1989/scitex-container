Quickstart
==========

CLI Quickstart
--------------

Check container status across Apptainer and Docker:

.. code-block:: bash

   scitex-container status

Build an Apptainer SIF from a definition file:

.. code-block:: bash

   scitex-container build --def-name scitex-final

List available container versions:

.. code-block:: bash

   scitex-container list

Switch active container version:

.. code-block:: bash

   scitex-container switch 2.19.5

Create a writable sandbox from a SIF:

.. code-block:: bash

   scitex-container sandbox create --sif scitex-final.sif

Install host-side dependencies (TeX Live, ImageMagick):

.. code-block:: bash

   scitex-container host install

Rebuild Docker Compose services:

.. code-block:: bash

   scitex-container docker rebuild

Python API Quickstart
---------------------

.. code-block:: python

   import scitex_container as sc

   # Apptainer operations
   sc.apptainer.build(def_name="scitex-final", sandbox=True)
   sc.apptainer.switch_version("2.19.5", containers_dir="/opt/containers")
   versions = sc.apptainer.list_versions(containers_dir="/opt/containers")
   status = sc.apptainer.status()

   # Host operations
   sc.host.check_packages()

   # Docker operations
   sc.docker.rebuild(env="prod")

   # Environment snapshot
   snapshot = sc.env_snapshot()

MCP Server Quickstart
---------------------

Start the MCP server for AI agent integration:

.. code-block:: bash

   scitex-container-mcp

Install to Claude Code:

.. code-block:: bash

   scitex-container mcp install
