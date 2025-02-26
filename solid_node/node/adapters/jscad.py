import os
import sys
import time
from solid2 import import_stl
from subprocess import Popen
from solid_node.node.leaf import LeafNode


class JScadNode(LeafNode):
    """
    A JScad node. You just need to declare the property "jscad_source" with
    the path of your JScad source code. It must be placed in the same directory
    of the python file containing this node.

    You need to have jscad cli tool installed in $PATH, and node dependencies
    installed in the directory you are running solid from.
    """

    jscad_source = None

    def __init__(self, name=None):
        if not self.jscad_source:
            raise Exception('OpenJScadNode subclass must declare "jscad_source" '
                            'property with path with a valid OpenJScad js file')
        module = sys.modules[self.__class__.__module__]
        basedir = os.path.dirname(module.__file__)
        source_path = os.path.join(basedir, self.jscad_source)
        self.jscad_source = os.path.realpath(source_path)

        super().__init__(name=name)

    def get_source_file(self):
        return self.jscad_source

    def render(self):
        return self

    def as_scad(self, _):

        cmd = [
            'jscad',
            self.jscad_source,
            '-o', self.stl_file,
        ]
        print('\n' + ' '.join(cmd))
        proc = Popen(cmd)
        proc.communicate()
        try:
            os.utime(self.stl_file, (time.time(), self.mtime))
        except FileNotFoundError:
            pass
        return import_stl(self.local_stl)
