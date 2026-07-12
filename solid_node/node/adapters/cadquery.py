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

import os
import sys
import time
import cadquery as cq
from solid2 import import_stl
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

    def as_scad(self, rendered):
        """Export the model to STL and returns a scad code to render it"""
        cq.exporters.export(rendered, self.stl_file, 'STL')
        os.utime(self.stl_file, (time.time(), self.mtime))
        return import_stl(self.local_stl)
