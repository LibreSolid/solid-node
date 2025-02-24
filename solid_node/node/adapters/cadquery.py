import os
import sys
import time
import inspect
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
