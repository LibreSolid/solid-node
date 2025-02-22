import os
import sys
import time
import inspect
import cadquery as cq
from solid2 import import_stl
from solid_node.node.leaf import LeafNode


def running_inside_cq_editor() -> bool:
    """Detect if we are running inside CQ-Editor"""
    for frame in inspect.stack():
        module = inspect.getmodule(frame.frame)
        if module and module.__name__ == 'cq_editor.__main__':
            return True
    return False


class TypeDecider(type):
    """This metaclass will check if we are in the context of
    CQ-editor, if so, use no base classes, otherwise inherit
    LeafNode."""
    def __new__(mcs, name, bases, namespace):
        if running_inside_cq_editor():
            bases = tuple()
        else:
            bases = (LeafNode,)
        return super().__new__(mcs, name, bases, namespace)


class CadQueryNode(metaclass=TypeDecider):
    """
    Represents a 3D object created using the CadQuery tool.
    """

    namespace = 'cadquery.cq'

    def as_scad(self, rendered):
        cq.exporters.export(rendered, self.stl_file, 'STL')
        os.utime(self.stl_file, (time.time(), self.mtime))
        return import_stl(self.local_stl)
