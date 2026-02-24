#!/usr/bin/env python3
"""Basic import tests for scitex-container."""


def test_import_package():
    import scitex_container

    assert hasattr(scitex_container, "__version__")


def test_import_submodules():
    from scitex_container import apptainer, docker, host

    assert apptainer is not None
    assert docker is not None
    assert host is not None


def test_import_env_snapshot():
    from scitex_container import env_snapshot

    assert callable(env_snapshot)


def test_import_verify():
    from scitex_container.apptainer import verify

    assert callable(verify)


def test_cli_entry_point():
    from scitex_container._cli import main

    assert main is not None


# EOF
