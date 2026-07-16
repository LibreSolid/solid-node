# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from .base import AbstractBaseNode
from solid2 import union


class InternalNode(AbstractBaseNode):
    """Internal nodes combine its children nodes in some way to make
    a node with several solids."""

    @property
    def time(self):
        """Each internal node must implement property `time` to handle
        animation"""
        raise NotImplementedError(f"InternalNode subclass {self.__class__} "
                                  "must deal with animation time")

    def as_scad(self, children):
        """Renders a scad of the combined children"""
        scads = []

        for child in children:
            self._link_child(child)
            scads.append(child.assemble(self.root))
            self.files.update(child.files)
            self.rigid = self.rigid and child.rigid

        # Assigned only AFTER the loop above: self.children is a plain
        # (non-private) list attribute, so setting it before deriving
        # names would make _attr_name_for's list-membership pass match
        # every child against IT -- including a child not referenced
        # by any real attribute of self, defeating the "keep the class
        # name" fallback (skill-repo improvements.md #16).
        self.children = children

        if len(scads) > 1:
            rendered = union()(scads)
        else:
            rendered = scads[0]

        return rendered

    def validate(self, rendered):
        """Check that rendered result is a list"""
        if type(rendered) not in (list, tuple):
            raise Exception(f"{self.__class__}.render() should return a list, "
                            f"not {type(rendered)}")

        for child in rendered:
            if not issubclass(type(child), AbstractBaseNode):
                raise Exception(f"{self.__class__}.render() returned invalid "
                                f"type {type(child)}")
            if type(child) is type(self):
                raise Exception(f"{self.__class__}.render() cannot return its "
                                "own type")
