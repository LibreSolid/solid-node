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
import time
import json
import trimesh
from solid_node.exceptions import MeshNotRendered, NonRigidSolid


class SpatialNodeMixin:
    """Adds get_mesh_dimensions() method to a node, that calculates
    the width, height and depth of the object's bounding box.
    Internally it renders an STL, loads the mesh and cache the
    results.

    This is an experimental code that seems unfunctional.
    """


    @property
    def cache_file(self):
        return f'{self.basepath}.dimensions.json'

    @property
    def cached_dimensions(self):
        if not os.path.exists(self.cache_file):
            return
        serialized = open(self.cache_file).read()
        return json.loads(serialized)

    def cache_dimensions(self, dimensions):
        serialized = json.dumps(dimensions)
        with open(self.cache_file, 'w') as fh:
            fh.write(serialized)
        os.utime(self.cache_file, (time.time(), self.mtime))

    def get_mesh_dimensions(self):
        """Returns the dimension of the object"""
        if not self.rigid:
            raise NonRigidSolid()

        try:
            return self._dimensions
        except AttributeError:
            pass

        cached = self.cached_dimensions

        if self._up_to_date(self.cache_file):
            return cached

        if not self._up_to_date(self.stl_file):
            if cached:
                return cached
            raise MeshNotRendered()

        mesh = trimesh.load(self.stl_file)
        box = mesh.bounding_box.bounds
        dimensions = [ box[1][i] - box[0][i] for i in range(3) ]

        self._dimensions = dimensions
        self.cache_dimensions(dimensions)
        return dimensions
