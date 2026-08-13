# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from .base import AbstractBaseNode


class LeafNode(AbstractBaseNode):
    """This is a base class for all leaf nodes, which are nodes
    that generate solid structures.
    Each LeafNode subclass uses a different technology to generate
    a solid, and outputs the result as STL.
    LeafNode subclasses are in the solid_node.node.adapters.* namespace.
    """

    _type = 'LeafNode'

    # Each LeafNode subclass can declare a namespace, and objects
    # returned by render() must belong to that namespace
    namespace = None

    @property
    def time(self):
        """Raise an exception, as leaf nodes cannot rely on time.
        Implementing a FlexibleNode is in the roadmap"""
        raise Exception(f"Leaf node cannot rely on time, animation should be "
                        "done on internal nodes")

    @property
    def children(self):
        """Returns an empty tuple, as leaf nodes have no children"""
        return tuple()

    def _render_can_be_skipped(self):
        """A leaf knows its own source set at construction, so it can
        answer this before doing any work -- unlike an internal node.

        Both artifacts must be current, not just the STL: the scad is
        what regenerates the STL if it is ever lost, and skipping is
        only safe while the pair on disk is the pair this source would
        produce.
        """
        return (
            self.optimize
            and self.rigid
            and self._up_to_date(self.stl_file)
            and self._up_to_date(self.scad_file)
            and (not self.exact or self._up_to_date(self.brep_file))
        )

    def as_scad(self, rendered):
        """Internally, the project is composed using OpenScad to render
        all STLs, so each LeafNode subclass must be able to output
        scad code"""
        raise NotImplementedError(f"LeafNode subclass {self.__class__} must "
                                  "be able to output scad")

    def validate(self, rendered):
        """Check if rendered result is an object of proper namespace"""
        if type(rendered) in (list, tuple):
            raise Exception(f"{self.__class__} is a LeafNode and should return "
                            f"a {self.namespace} object, not a list")

        if self.namespace and not type(rendered).__module__.startswith(self.namespace):
            raise Exception(f"{self.__class__} is a LeafNode and should render "
                            f"as {self.namespace} child, not {type(rendered)}")
