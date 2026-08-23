# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Run framework code in an interpreter where `manifold3d` is absent.

The mesh engine ships no WebAssembly wheel, so a browser runtime simply
does not have it. This helper reproduces that environment honestly in a
subprocess rather than stubbing the module: a `sys.meta_path` finder
refuses `manifold3d`, so every import of it raises
`ModuleNotFoundError` exactly as it would on a machine without the
wheel.

`trimesh` is imported BEFORE the blocker is installed on purpose.
trimesh treats `manifold3d` as one optional boolean engine among
several, probes for it with `importlib.util.find_spec` at import time,
and copes with its absence; blocking it earlier would only reproduce
trimesh's probe, not the framework's own hard requirement, which is
what is under test.
"""

import os
import subprocess
import sys


BASEDIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASEDIR)
BUILD_DIR = os.path.join(BASEDIR, '_build_meta')

BLOCKER = '''
import sys, trimesh


class _MeshEngineAbsent:
    """Refuse manifold3d the way an interpreter without the wheel does."""

    def find_spec(self, name, target=None, path=None):
        if name == 'manifold3d' or name.startswith('manifold3d.'):
            raise ModuleNotFoundError(
                "No module named 'manifold3d'", name='manifold3d')
        return None


sys.meta_path.insert(0, _MeshEngineAbsent())
sys.modules.pop('manifold3d', None)
'''


def run_python(snippet):
    """Run `snippet` in a subprocess with no importable `manifold3d`."""
    return subprocess.run(
        [sys.executable, '-c', BLOCKER + snippet],
        cwd=REPO_DIR, env=dict(os.environ, PYTHONPATH=REPO_DIR),
        capture_output=True, text=True, timeout=300,
    )


def run_solid_test(path):
    """Run `solid test <path>` with no importable `manifold3d`.

    Mirrors `tests/test_meta.py`'s subprocess harness, so a verdict here
    is comparable test-for-test with the same fixture's ordinary run.
    """
    return subprocess.run(
        [sys.executable, '-c',
         BLOCKER + 'from solid_node.cli import manage; manage()',
         'test', path],
        cwd=REPO_DIR,
        env=dict(os.environ, SOLID_BUILD_DIR=BUILD_DIR, PYTHONPATH=REPO_DIR),
        capture_output=True, text=True, timeout=300,
    )


def mesh_engine_is_installed():
    """True when this interpreter really has the mesh engine, so a test
    can state plainly that it is comparing against a genuine baseline."""
    try:
        import manifold3d  # noqa: F401
    except ImportError:
        return False
    return True
