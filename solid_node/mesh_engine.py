# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Conditional availability contract for the `manifold3d` mesh engine.

The mesh engine decides faceted geometry. Exact geometry is decided by
the boundary-representation kernel and never reads a Manifold, so a
project whose model is entirely exact must not be made to carry the
dependency -- the same conditional treatment ADR-046 gave the OpenSCAD
binary, applied to a compiled wheel.

`manifold3d` publishes no WebAssembly wheel, so on that surface the
dependency is not merely unwanted but unavailable.
"""

from functools import lru_cache


class MeshEngineUnavailable(RuntimeError):
    """A requested operation cannot run without the manifold3d engine."""

    def __init__(self, needed_by, reason):
        super().__init__(
            f"{needed_by} requires the manifold3d mesh engine because "
            f"{reason}; install it with 'pip install manifold3d'. Exact "
            f"geometry does not need it: a model whose every compared part "
            f"is exact is decided by the boundary-representation kernel")


@lru_cache(maxsize=1)
def mesh_engine():
    """Resolve the mesh engine once for this process, only when a path
    needs it. Returns ``(Manifold, Mesh)`` or ``None`` when absent."""
    try:
        from manifold3d import Manifold, Mesh
    except ImportError:
        return None
    return Manifold, Mesh


def require_mesh_engine(needed_by, reason):
    """Return ``(Manifold, Mesh)`` or raise one actionable error."""
    engine = mesh_engine()
    if engine is None:
        raise MeshEngineUnavailable(needed_by, reason)
    return engine
