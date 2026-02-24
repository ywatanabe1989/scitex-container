Installation
============

Requirements
------------

- Python >= 3.10
- Apptainer or Docker (for container operations)

Install from PyPI
-----------------

Core package (CLI only):

.. code-block:: bash

   pip install scitex-container

With MCP server support (for AI agent integration):

.. code-block:: bash

   pip install scitex-container[mcp]

Full installation (all optional dependencies):

.. code-block:: bash

   pip install scitex-container[all]

Install from Source
-------------------

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-container.git
   cd scitex-container
   pip install -e ".[all]"

Verify Installation
-------------------

.. code-block:: bash

   scitex-container --version
   scitex-container status
