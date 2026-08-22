# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import import_stl
from solid_node.exact import (build123d_shape, cached_shape,
                              shape_from_rendered, write_brep, write_stl)
from solid_node.node.leaf import LeafNode


class Build123dNode(LeafNode):
    """
    Represents a 3D object created using the build123d tool.

    build123d is a boundary-representation backend over the same OCCT that
    CadQueryNode uses, so this adapter is exact: it produces its own STL and
    BREP through the kernel and never needs OpenSCAD to render them.

    Note that this module never imports build123d. See build123d_shape().
    """

    namespace = 'build123d'

    @property
    def exact(self):
        return True

    def validate(self, rendered):
        """Reject anything but a solid, on top of the inherited list and
        namespace checks.

        The namespace cannot carry this adapter alone. build123d's solids,
        sketches and curves are all under the `build123d` namespace -- Part
        and Compound in build123d.topology.composite, Solid in
        build123d.topology.three_d, but also Rectangle in
        build123d.objects_sketch and Line in build123d.objects_curve -- so
        `namespace` admits a sketch as readily as a part. Left to itself, a
        returned sketch would fail later and far less legibly, inside the STL
        export.
        """
        super().validate(rendered)

        shape = build123d_shape(rendered)
        if shape is None or not shape.Solids():
            raise Exception(
                f"{self.name} is a Build123dNode and should render a "
                f"build123d solid -- a Part, Solid or Compound, or a builder "
                f"whose .part is one -- not {type(rendered).__name__}"
            )

    def shape(self):
        if self._up_to_date(self.brep_file):
            return cached_shape(self.brep_file)
        if self.model is not None:
            return shape_from_rendered(self.model)
        rendered = self.render()
        self.validate(rendered)
        return shape_from_rendered(rendered)

    def as_scad(self, rendered):
        """Export the model to STL and returns a scad code to render it.

        The export is skipped when the artifact on disk was already produced
        from these sources, the same guard CadQueryNode's adapter carries.
        """
        shape = shape_from_rendered(rendered)
        if not self._up_to_date(self.stl_file):
            write_stl(shape, self.stl_file, self.mtime)
        if not self._up_to_date(self.brep_file):
            write_brep(shape, self.brep_file, self.mtime)
        return import_stl(self.local_stl)
