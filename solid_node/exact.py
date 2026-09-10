# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Exact B-rep geometry shared by nodes and geometric assertions."""

from collections import OrderedDict
import math
import os
import struct
import tempfile
import time

import cadquery as cq
import numpy as np
import trimesh
from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf
from OCP.TopTools import TopTools_ListOfShape

from solid_node import currency


_shape_cache = {}

# The cache key of every shape `_shape_cache` currently holds, by object
# address. An address is only a safe identity while something keeps the
# object alive, and `_shape_cache` is exactly that: an entry here is added
# and removed with the shape it names, so an address can never be reused
# behind a surviving entry.
#
# A shape cannot be its own key. `Shape.__eq__` is `isSame()`, which
# compares the underlying TShape and IGNORES location, so a shape and a
# differently placed copy of it compare equal -- keying placements on the
# shape would serve one part's placement for another's.
_shape_keys = {}

# One placed shape per (shape cache key, exact matrix bytes), and one bounding box per
# shape cache key. `placed_shape` runs a full `BRepBuilderAPI_Transform`
# over the B-rep -- 6-19 ms on real parts -- and an animated assertion
# places the same solid by the same matrix at every candidate pair it
# visits.
#
# This is deliberately access ordered and bounded. A trajectory can contain
# indefinitely many distinct poses, so insertion-order-only eviction would
# unnecessarily discard a useful working set and unbounded retention would
# retain every old OCCT shape for the lifetime of the process.
_PLACEMENT_CACHE_LIMIT = 512
_placement_cache = OrderedDict()
_bounds_cache = {}

# One (F, 2, 3) float64 array of local face AABBs per shape cache key,
# beside `_bounds_cache`. It is safe to cache under that key because it is
# a pure function of the exact geometry: `cached_face_boxes` below takes
# every box with `useTriangulation=False`, so no triangulation a shape may
# come to carry -- attached, replaced, or discarded after this entry is
# filled -- can ever change what is already served under this identity.
_face_box_cache = {}


def _reset_placement_cache():
    """Drop retained exact placements for direct isolation or a new run.

    This is intentionally an internal seam: callers can clear a process-local
    working set, but cannot configure or inspect cache policy as public API.
    """
    _placement_cache.clear()


def _evict(brep_file):
    """Drop every cached artifact derived from a rebuilt file."""
    for key in [key for key in _shape_cache if key[0] == brep_file]:
        _shape_keys.pop(id(_shape_cache.pop(key)), None)
        _bounds_cache.pop(key, None)
        _face_box_cache.pop(key, None)
        for placement in [placement for placement in _placement_cache
                          if placement[0] == key]:
            del _placement_cache[placement]


def cached_shape(brep_file):
    """Load one immutable CadQuery shape per ``(path, mtime)``."""
    mtime = os.path.getmtime(brep_file)
    key = (brep_file, mtime)
    cached = _shape_cache.get(key)
    if cached is None:
        _evict(brep_file)
        cached = cq.Shape.importBrep(brep_file)
        _shape_cache[key] = cached
        _shape_keys[id(cached)] = key
    return cached


def shape_identity(shape):
    """The cache key of a shape this module holds, or None.

    None means "no stable identity": a shape composed for this comparison
    or read from a node whose BREP is not current. A caller keying work on
    geometry must not cache such a shape's results.
    """
    return _shape_keys.get(id(shape))


def cached_bounding_box(shape):
    """The shape's local bounding box, computed once per cached shape.

    A shape with no cache identity -- one composed for this comparison, or
    read from a node whose BREP is not current -- is measured directly, as
    it is today.
    """
    key = _shape_keys.get(id(shape))
    if key is None:
        return shape.BoundingBox()
    bounds = _bounds_cache.get(key)
    if bounds is None:
        bounds = shape.BoundingBox()
        _bounds_cache[key] = bounds
    return bounds


def _measured_face_boxes(shape):
    """One local AABB per face of ``shape``, taken with
    ``BRepBndLib.Add_s(face.wrapped, box, False)`` -- OCCT's own tolerance
    enlargement, no triangulation. ``useTriangulation=False`` keeps a face
    box a pure function of the exact surface: with ``True`` the box would
    depend on whether a triangulation happens to be attached and at what
    deflection, which is state an STL export or a viewer read can change
    on a shape this cache is already holding, and a cached measurement
    must be a pure function of its key. It is also conservative by
    construction -- bounding a face from its surface's own poles/parametric
    bounds plus its tolerance is outward-only slack, never inward -- where
    CadQuery's own ``BoundingBox()`` instead calls ``AddOptimal_s``, a
    tighter but slower route that meshes the shape and is unnecessary for
    a superset test.

    Returns an ``(F, 2, 3)`` float64 array, ``(0, 2, 3)`` for a shape with
    no faces.
    """
    faces = shape.Faces()
    boxes = np.empty((len(faces), 2, 3), dtype=np.float64)
    for index, face in enumerate(faces):
        box = Bnd_Box()
        BRepBndLib.Add_s(face.wrapped, box, False)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
        boxes[index, 0, :] = (xmin, ymin, zmin)
        boxes[index, 1, :] = (xmax, ymax, zmax)
    return boxes


def cached_face_boxes(shape):
    """The shape's local per-face bounding boxes, computed once per cached
    shape identity -- mirrors ``cached_bounding_box`` exactly, including
    its escape hatch: a shape with no cache identity -- one composed for
    this comparison, or read from a node whose BREP is not current -- is
    measured directly, every time, and never cached.
    """
    key = _shape_keys.get(id(shape))
    if key is None:
        return _measured_face_boxes(shape)
    boxes = _face_box_cache.get(key)
    if boxes is None:
        boxes = _measured_face_boxes(shape)
        _face_box_cache[key] = boxes
    return boxes


def build123d_shape(rendered):
    """The OCCT shape of a build123d render result, or None if ``rendered``
    did not come from build123d.

    build123d and CadQuery are two front ends over one OCCT: every object of
    either wraps a single TopoDS_Shape, exposed as ``.wrapped``. Rewrapping
    that shape is therefore the whole conversion, and it is why a build123d
    node's exact geometry is carried as the CadQuery ``Shape`` the rest of
    this module trades in -- every consumer below (placement, fuse, common,
    BREP persistence, volume) then needs no backend special case, and a
    fusion may freely mix the two backends.

    build123d is recognised by module name rather than imported.
    ``solid_node.node`` imports every adapter eagerly and importing build123d
    costs about 1.6 seconds, which a project modelling in another backend
    should not pay.

    A builder is not itself geometry: ``with BuildPart() as part:`` is
    build123d's headline idiom, and returning the builder rather than its
    ``.part`` is the first mistake a user makes, so the finished part is
    taken. Returning None rather than raising leaves the diagnosis to
    Build123dNode.validate(), which can name the node.
    """
    if not type(rendered).__module__.startswith('build123d'):
        return None
    if not hasattr(rendered, 'wrapped'):
        rendered = getattr(rendered, 'part', None)
    if getattr(rendered, 'wrapped', None) is None:
        return None
    return cq.Shape.cast(rendered.wrapped)


def shape_from_rendered(rendered):
    """Return all shapes produced by a render as one shape."""
    from_build123d = build123d_shape(rendered)
    if from_build123d is not None:
        return from_build123d
    shapes = list(rendered.vals()) if hasattr(rendered, 'vals') else [rendered]
    if not shapes:
        raise ValueError('CadQuery render produced no shape')
    if len(shapes) == 1:
        return shapes[0]
    return cq.Compound.makeCompound(shapes)


def _atomic_export(path, mtime_ns, exporter, digest=None, fingerprint=None):
    """Write, stamp, and vouch for one exact artifact.

    `digest` and `fingerprint` are the node's source record, written beside the
    artifact by `currency.publish` in the same step that puts it in place -- an
    artifact and the record of what produced it are written together or
    not at all. Defaulting the digest to None means "no record", which costs a
    rebuild and never a stale answer, so a caller outside a node (an
    assertion helper, a test) is served correctly without one.
    """
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    os.close(descriptor)
    try:
        exporter(temporary)
        os.utime(temporary, ns=(time.time_ns(), mtime_ns))
        currency.publish(temporary, path, digest, fingerprint)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def write_brep(shape, path, mtime_ns, digest=None, fingerprint=None):
    _atomic_export(path, mtime_ns, shape.exportBrep, digest, fingerprint)


def write_stl(shape, path, mtime_ns, linear_deflection, angular_deflection,
             digest=None, fingerprint=None):
    """Tessellate `shape` to an STL artifact without degenerate triangles.

    OCCT's mesher emits zero-area triangles on some vendor solids (shafts,
    standoffs, stepper frames); they add nothing to the surface and break
    the mesh engine's edge pairing, so every exact artifact -- a leaf's or
    a fused solid's -- drops them, after tessellating at whatever precision
    the caller asks for.

    `linear_deflection` and `angular_deflection` are required rather than
    defaulted: the framework's historical values (0.1 mm, 0.1 rad) live in
    exactly one place, the class attribute declarations on `ExactLeafNode`
    and `FusionNode` (see `deflections`), not duplicated here as a second
    default a reader could find and trust.
    """
    def export(temporary):
        shape.exportStl(temporary, tolerance=linear_deflection,
                        angularTolerance=angular_deflection)
        mesh = trimesh.load(temporary, file_type='stl', process=False)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.export(temporary, file_type='stl')

    _atomic_export(path, mtime_ns, export, digest, fingerprint)


_DEFLECTION_UNITS = {
    'linear_deflection': 'millimetres',
    'angular_deflection': 'radians',
}


def _validated_deflection(node, attribute):
    value = getattr(node, attribute)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        unit = _DEFLECTION_UNITS[attribute]
        raise ValueError(
            f'{node.name}.{attribute} must be a positive finite number '
            f'of {unit}, not {value!r}')
    return float(value)


def deflections(node):
    """Read and validate the tessellation precision `node` declares.

    Reads `node.linear_deflection` and `node.angular_deflection` -- class
    attributes `ExactLeafNode` and `FusionNode` declare with the
    framework's historical defaults (0.1 mm, 0.1 rad) -- at the point the
    artifact is about to be written, which is what lets a node whose
    artifacts are already current skip the validation entirely.

    A value is refused unless it is a real number (`bool` excluded --
    `True` is not a deflection), finite, and strictly positive; the error
    names the node and the offending attribute.
    """
    return (_validated_deflection(node, 'linear_deflection'),
           _validated_deflection(node, 'angular_deflection'))


def _place(shape, values):
    transform = gp_Trsf()
    transform.SetValues(*values)
    return cq.Shape.cast(
        BRepBuilderAPI_Transform(shape.wrapped, transform, True).Shape())


def placed_shape(shape, matrix):
    """Place a local shape using the framework's composed 4x4 matrix.

    Cached per ``(shape cache key, exact matrix bytes)``, so a solid placed by
    the same matrix twice while retained is transformed once. The matrix is
    compared by the exact IEEE-754 values sent to OCCT: a placement difference
    too small to see (including signed zero) is still a different placement,
    and this cache introduces no tolerance or rounding of its own. A shape
    with no cache identity is placed uncached, exactly as before.
    """
    values = tuple(float(matrix[row, column])
                   for row in range(3) for column in range(4))
    key = _shape_keys.get(id(shape))
    if key is None:
        return _place(shape, values)
    placement = (key, struct.pack('!12d', *values))
    placed = _placement_cache.get(placement)
    if placed is None:
        placed = _place(shape, values)
        while len(_placement_cache) >= _PLACEMENT_CACHE_LIMIT:
            _placement_cache.popitem(last=False)
        _placement_cache[placement] = placed
    else:
        _placement_cache.move_to_end(placement)
    return placed


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
