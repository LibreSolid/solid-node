import trimesh
from solid_node.exceptions import MeshNotRendered, NonRigidSolid


class SpatialNodeMixin:

    @property
    def dimensions(self):
        if not self.rigid:
            raise NonRigidSolid()

        if not self._up_to_date(self.stl_file):
            raise MeshNotRendered()

        try:
            return self._dimensions
        except AttributeError:
            pass

        mesh = trimesh.load(self.stl_file)
        box = mesh.bounding_box.bounds
        dimensions = [ box[1][i] - box[0][i] for i in range(3) ]
        self._dimensions = dimensions
        return dimensions

    @property
    def width(self):
        return self.dimensions[0]

    @property
    def depth(self):
        return self.dimensions[1]

    @property
    def height(self):
        return self.dimensions[2]
