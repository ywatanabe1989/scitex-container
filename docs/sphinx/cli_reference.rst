CLI Reference
=============

The ``scitex-container`` CLI provides unified container management for
Apptainer and Docker.

Global Options
--------------

.. code-block:: text

   scitex-container [OPTIONS] COMMAND [ARGS]...

   Options:
     --version          Show version and exit.
     --help-recursive   Show help for all commands recursively.
     --help             Show this message and exit.

Apptainer Commands
------------------

build
~~~~~

Build a SIF container from a definition file.

.. code-block:: bash

   scitex-container build [OPTIONS]

list
~~~~

List all available container versions.

.. code-block:: bash

   scitex-container list [OPTIONS]

switch
~~~~~~

Switch the active container version.

.. code-block:: bash

   scitex-container switch VERSION

rollback
~~~~~~~~

Roll back to the previous container version.

.. code-block:: bash

   scitex-container rollback [OPTIONS]

deploy
~~~~~~

Deploy a container version to the active slot.

.. code-block:: bash

   scitex-container deploy VERSION

cleanup
~~~~~~~

Remove old container versions to free disk space.

.. code-block:: bash

   scitex-container cleanup [OPTIONS]

verify
~~~~~~

Verify a container can be executed successfully.

.. code-block:: bash

   scitex-container verify [OPTIONS]

Sandbox Commands
----------------

.. code-block:: bash

   scitex-container sandbox COMMAND [ARGS]...

sandbox create
~~~~~~~~~~~~~~

Convert a SIF to a writable sandbox directory.

.. code-block:: bash

   scitex-container sandbox create [OPTIONS]

sandbox to-sif
~~~~~~~~~~~~~~

Convert a sandbox directory back to a SIF.

.. code-block:: bash

   scitex-container sandbox to-sif [OPTIONS]

Docker Commands
---------------

.. code-block:: bash

   scitex-container docker COMMAND [ARGS]...

docker rebuild
~~~~~~~~~~~~~~

Rebuild Docker Compose services.

.. code-block:: bash

   scitex-container docker rebuild [OPTIONS]

docker restart
~~~~~~~~~~~~~~

Restart running Docker services.

.. code-block:: bash

   scitex-container docker restart [OPTIONS]

Host Commands
-------------

.. code-block:: bash

   scitex-container host COMMAND [ARGS]...

host install
~~~~~~~~~~~~

Install host-side packages (TeX Live, ImageMagick, etc.).

.. code-block:: bash

   scitex-container host install [OPTIONS]

host check
~~~~~~~~~~~

Check status of required host packages.

.. code-block:: bash

   scitex-container host check [OPTIONS]

Status Dashboard
----------------

.. code-block:: bash

   scitex-container status [OPTIONS]

Displays a unified dashboard showing the status of Apptainer containers,
Docker services, and host package installations.

Environment Snapshot
--------------------

.. code-block:: bash

   scitex-container env-snapshot [OPTIONS]

Capture a reproducibility snapshot of the current environment (Python
packages, container versions, host configuration).

MCP Commands
------------

.. code-block:: bash

   scitex-container mcp COMMAND [ARGS]...

mcp install
~~~~~~~~~~~

Install the MCP server configuration for Claude Code.

.. code-block:: bash

   scitex-container mcp install
