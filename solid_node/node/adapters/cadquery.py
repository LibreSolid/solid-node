# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
from solid2 import import_stl
from solid_node.exact import (cached_shape, shape_from_rendered, write_brep,
                              write_stl)
from solid_node.node.leaf import LeafNode


class CheckCQEditor(type):
    """This metaclass will check if we are in the context of
    CQ-editor, if so, use no base classes, otherwise inherit
    LeafNode."""
    def __new__(mcs, name, bases, namespace):
        if sys.modules.get('cq_editor.__main__', None):
            bases = tuple()

        return super().__new__(mcs, name, bases, namespace)


class CadQueryNode(LeafNode, metaclass=CheckCQEditor):
    """
    Represents a 3D object created using the CadQuery tool.
    """
    namespace = 'cadquery.cq'

    @property
    def exact(self):
        return True

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

        The export is skipped when the STL on disk was already produced
        from these sources -- the same guard generate_stl() has always
        had, which this path used to run upstream of. A node that opts
        out of optimization still reaches here, so the guard belongs on
        the adapter and not only on the assemble() shortcut.
        """
        shape = shape_from_rendered(rendered)
        if not self._up_to_date(self.stl_file):
            write_stl(shape, self.stl_file, self.mtime)
        if not self._up_to_date(self.brep_file):
            write_brep(shape, self.brep_file, self.mtime)
        return import_stl(self.local_stl)
