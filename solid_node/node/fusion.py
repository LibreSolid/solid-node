# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.exact import (cached_shape, fuse_shapes, placed_shape,
                              write_brep, write_stl)
from .base import _compose_solid_matrix
from .internal import InternalNode


class FusionNode(InternalNode):
    """
    Represents a fusion of components into a single, inseparable unit.
    This internal node can contain LeafNode or other FusionNode instances.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'FusionNode'

    @property
    def time(self):
        """You can't use self.time with a FusionNode, as the resulting object
        is expected to be rigid."""
        raise Exception(
            "FusionNode cannot rely on time; use AssemblyNode for animation")

    def validate(self, rendered):
        """A fusion combines solids into one solid, so every child must
        be rigid. You fuse first and assemble afterwards; an assembled
        thing has no single geometry to fuse.

        Checked here rather than in InternalNode so the base class does
        not have to know its own subclasses. Rigidity is determined by
        node type (ADR-003 as amended by ADR-039), so a child's `rigid`
        is already final at validation time -- nothing has to be
        rendered to ask the question.
        """
        super().validate(rendered)

        for child in rendered:
            if not child.rigid:
                raise Exception(
                    f"{self.name} cannot fuse non-rigid child {child.name}; "
                    "fuse solids first, then assemble them")

    def shape(self):
        if not self.exact:
            return super().shape()
        if self._up_to_date(self.brep_file):
            return cached_shape(self.brep_file)
        placed = [
            placed_shape(child.shape(), _compose_solid_matrix(child))
            for child in self.children
        ]
        result = placed[0]
        for child, child_shape in zip(self.children[1:], placed[1:]):
            result = fuse_shapes(result, child_shape, self.name, child.name)
        return result

    def generate_stl(self):
        if not self.exact:
            return super().generate_stl()
        if (self._up_to_date(self.stl_file)
                and self._up_to_date(self.brep_file)):
            return
        shape = self.shape()
        write_brep(shape, self.brep_file, self.mtime)
        write_stl(
            shape, self.stl_file, self.mtime, remove_degenerate=True)
