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
