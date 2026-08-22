# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.exact import build123d_shape
from solid_node.node.exact_leaf import ExactLeafNode


class Build123dNode(ExactLeafNode):
    """
    Represents a 3D object created using the build123d tool.

    build123d is a boundary-representation backend over the same OCCT that
    CadQueryNode uses, so the exact-adapter contract -- exact, shape(),
    as_scad() -- is ExactLeafNode's. What is build123d's own is the namespace
    and the solid-shaped-result rule below.

    Note that this module never imports build123d. See build123d_shape().
    """

    namespace = 'build123d'

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

        The check stays here rather than on ExactLeafNode because it is not
        the exact contract's: a CadQuery render is legitimately a Workplane,
        which is not a solid until shape_from_rendered unwraps it.
        """
        super().validate(rendered)

        shape = build123d_shape(rendered)
        if shape is None or not shape.Solids():
            raise Exception(
                f"{self.name} is a Build123dNode and should render a "
                f"build123d solid -- a Part, Solid or Compound, or a builder "
                f"whose .part is one -- not {type(rendered).__name__}"
            )
