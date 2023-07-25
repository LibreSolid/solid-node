import os
import time
import cadquery as cq
from solid2 import import_stl
from solid_node.node.leaf import LeafNode


class CadQueryNode(LeafNode):
    """
    Represents a 3D object created using the CadQuery tool.
    """

    namespace = 'cadquery.cq'

    def as_scad(self, rendered):
        cq.exporters.export(rendered, self.stl_file, 'STL')
        os.utime(self.stl_file, (time.time(), self.mtime))
        return import_stl(self.local_stl)
