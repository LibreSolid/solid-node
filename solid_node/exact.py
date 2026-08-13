# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Exact B-rep geometry shared by nodes and geometric assertions."""

import os
import tempfile
import time

import cadquery as cq
import trimesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf
from OCP.TopTools import TopTools_ListOfShape


_shape_cache = {}


def cached_shape(brep_file):
    """Load one immutable CadQuery shape per ``(path, mtime)``."""
    mtime = os.path.getmtime(brep_file)
    key = (brep_file, mtime)
    cached = _shape_cache.get(key)
    if cached is None:
        for stale_key in [key for key in _shape_cache
                          if key[0] == brep_file]:
            del _shape_cache[stale_key]
        cached = cq.Shape.importBrep(brep_file)
        _shape_cache[key] = cached
    return cached


def shape_from_rendered(rendered):
    """Return all shapes produced by a CadQuery render as one shape."""
    shapes = list(rendered.vals()) if hasattr(rendered, 'vals') else [rendered]
    if not shapes:
        raise ValueError('CadQuery render produced no shape')
    if len(shapes) == 1:
        return shapes[0]
    return cq.Compound.makeCompound(shapes)


def _atomic_export(path, mtime, exporter):
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    os.close(descriptor)
    try:
        exporter(temporary)
        os.utime(temporary, (time.time(), mtime))
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def write_brep(shape, path, mtime):
    _atomic_export(path, mtime, shape.exportBrep)


def write_stl(shape, path, mtime, *, remove_degenerate=False):
    # Match CadQueryNode's historical cq.exporters.export defaults.
    def export(temporary):
        shape.exportStl(temporary, tolerance=0.1, angularTolerance=0.1)
        if remove_degenerate:
            mesh = trimesh.load(temporary, file_type='stl')
            mesh.update_faces(mesh.nondegenerate_faces())
            mesh.remove_unreferenced_vertices()
            mesh.export(temporary, file_type='stl')

    _atomic_export(path, mtime, export)


def placed_shape(shape, matrix):
    """Place a local shape using the framework's composed 4x4 matrix."""
    transform = gp_Trsf()
    transform.SetValues(*[float(matrix[row, column])
                          for row in range(3) for column in range(4)])
    return cq.Shape.cast(
        BRepBuilderAPI_Transform(shape.wrapped, transform, True).Shape())


def _boolean(operation, first, second, first_name, second_name):
    algorithm = {
        'intersection': BRepAlgoAPI_Common,
        'fusion': BRepAlgoAPI_Fuse,
    }[operation]()
    arguments = TopTools_ListOfShape()
    arguments.Append(first.wrapped)
    tools = TopTools_ListOfShape()
    tools.Append(second.wrapped)
    algorithm.SetArguments(arguments)
    algorithm.SetTools(tools)
    algorithm.SetRunParallel(True)
    try:
        algorithm.Build()
        if not algorithm.IsDone():
            raise RuntimeError('kernel reported not-done')
        return cq.Shape.cast(algorithm.Shape())
    except Exception as error:
        raise RuntimeError(
            f"Exact {operation} failed for {first_name} and "
            f"{second_name}: {error}"
        ) from error


def intersect_shapes(first, second, first_name, second_name):
    return _boolean('intersection', first, second, first_name, second_name)


def fuse_shapes(first, second, first_name, second_name):
    return _boolean('fusion', first, second, first_name, second_name)


def solid_count(shape):
    return len(shape.Solids())


def solid_volume(shape):
    return sum(solid.Volume() for solid in shape.Solids())
