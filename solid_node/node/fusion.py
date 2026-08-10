# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from .internal import InternalNode


class FusionNode(InternalNode):
    """
    Represents a fusion of components into a single, inseparable unit.
    This is an internal node that can contain instances of LeafNode or other FusionNode.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'FusionNode'

    @property
    def time(self):
        """You can't use self.time with a FusionNode, as the resulting object
        is expected to be rigid."""
        raise Exception(f"FusionNode cannot rely on time, use AssemblyNode for animation")

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
