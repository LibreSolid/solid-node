import os
import time
import json
import trimesh
from solid_node.exceptions import MeshNotRendered, NonRigidSolid


class SpatialNodeMixin:

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
