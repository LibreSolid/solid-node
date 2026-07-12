# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
        self.children = children

        scads = []

        for child in children:
            scads.append(child.assemble(self.root))
            self.files.update(child.files)
            self.rigid = self.rigid and child.rigid

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
