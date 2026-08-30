# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.exact import _atomic_export
from solid_node.node.sheet_leaf import SheetLeafNode


# How far off the XY plane a profile may sit and still count as on it.
# Loose enough for the rounding a placement composes, tight enough that a
# profile authored on another plane is caught.
_PLANE_TOLERANCE = 1e-6


def _export_dxf(face, path, mtime_ns, digest=None):
    """Write one validated planar face as a nominal cut file.

    Nominal: the authored profile at model scale, in millimeters, with no
    kerf or other machine compensation. Compensation is a property of a
    machine and a material, not of the part, and the persisted BREP keeps
    the exact profile available to a future offsetting exporter.

    build123d's own DXF exporter is used rather than a tessellation, so a
    circular hole reaches the cutter as a circle at its modelled radius
    instead of a polygon that would cut tight.

    Deliberately a private, single-purpose function rather than a method:
    it converts a validated face to a file and knows nothing about nodes,
    so a second sheet backend can be given its own without either growing
    a backend switch (ADR-047's pattern). It borrows exact.py's atomic
    export only for the write-and-stamp convention every other artifact
    already uses -- what is written is build123d's business, not the
    backend-neutral exact layer's.
    """
    import build123d as b3d

    exporter = b3d.ExportDXF(unit=b3d.Unit.MM)
    exporter.add_shape(face)
    _atomic_export(path, mtime_ns, exporter.write, digest)


class Build123dSheetNode(SheetLeafNode):
    """A sheet part authored as a build123d profile.

    The whole adapter is the three backend-specific steps SheetLeafNode
    asks for -- reduce a profile result to one planar face, extrude it,
    write it as a cut file. The contract around them is the sheet base's,
    and the exact-adapter contract under that is ExactLeafNode's: the
    extrusion is an ordinary build123d Part, so namespace validation,
    the OCCT rewrap, and the STL/BREP writes are the ones every other
    exact adapter already goes through.

    This is not a Build123dNode. Both drive build123d, but a Build123dNode
    renders a solid it authored, while a sheet part's solid is derived and
    only its profile is authored -- and the two must stay distinct types,
    since `isinstance` and the MRO backend walk both distinguish adapters
    that way.

    Like the other build123d adapter, this module never imports build123d
    at import time: `solid_node.node` imports every adapter eagerly, and
    build123d costs about 1.6 seconds a project on another backend should
    not pay.
    """

    namespace = 'build123d'

    def profile(self):
        """The part's cut profile: a build123d `Sketch`, a `Face`, or a
        `BuildSketch` builder holding one."""
        raise NotImplementedError(
            f"{self.__class__} is a Build123dSheetNode and must implement "
            "profile(), returning a build123d sketch, face or BuildSketch")

    def _profile_faces(self, profile):
        """The planar faces of a build123d profile result.

        Empty for anything that is not a planar 2D object, so the sheet
        base can name the type the node produced: a solid has solids, a
        curve has no faces at all, and a foreign object is not build123d's.
        A solid is the interesting rejection -- Build123dNode would accept
        it, and its six planar faces would otherwise read as six parts.

        A builder is not itself geometry. `with BuildSketch() as sketch:`
        is build123d's headline sketch idiom, so the finished `.sketch` is
        taken, exactly as Build123dNode takes a builder's `.part`.
        """
        if not type(profile).__module__.startswith('build123d'):
            return []
        if not hasattr(profile, 'wrapped'):
            profile = getattr(profile, 'sketch', None)
        if getattr(profile, 'wrapped', None) is None:
            return []
        if profile.solids() or profile.shells():
            return []
        return [face for face in profile.faces() if face.is_planar]

    def _lies_on_xy_plane(self, face):
        normal = face.normal_at()
        if abs(abs(normal.Z) - 1) > _PLANE_TOLERANCE:
            return False
        box = face.bounding_box()
        return (abs(box.min.Z) <= _PLANE_TOLERANCE
                and abs(box.max.Z) <= _PLANE_TOLERANCE)

    def _extrude(self, face):
        """The profile swept along +Z by the thickness.

        The direction is given explicitly rather than left to the face's
        own normal, so a profile authored with a reversed normal still
        yields the part the contract promises: from the XY plane up to
        Z = thickness.
        """
        import build123d as b3d

        return b3d.extrude(face, amount=self.thickness, dir=(0, 0, 1))

    def _write_dxf(self, face, path, mtime_ns, digest=None):
        _export_dxf(face, path, mtime_ns, digest)
