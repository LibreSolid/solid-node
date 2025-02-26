import os
import sys
import tempfile
from solid2 import scad_render, import_scad
from solid2.core.parse_scad import get_scad_file_as_dict
from solid2.core.utils import resolve_scad_filename
from solid_node.node.leaf import LeafNode


class OpenScadNode(LeafNode):
    """
    A pure OpenScad node. You just need to declare the property "scad_source" with
    the path of your OpenScad source code. It must be placed in the same directory
    of the python file containing this node.

    The scad file must contain a module with the same name of the file, or you
    may specify the property "module_name" with the module name.
    """

    namespace = 'solid2.core.object_factory'
    scad_source = None
    module_name = None

    def __init__(self, *args, name=None, **kwargs):
        """Receives args, an optional name keyword argument and a list of keyword
        arguments. The list of arguments and keyword arguments will be passed as
        parameter to the module.

        Args:
           *args: will be passed as arguments to the OpenScad module
           name keyword argument: the name of this node, defaul to name of the class
           **kwargs: will be passed as keyword arguments to the openscad module
        """
        module = sys.modules[self.__class__.__module__]
        basedir = os.path.dirname(module.__file__)
        source_path = os.path.join(basedir, self.scad_source)
        self.openscad_source = os.path.realpath(source_path)
        self.openscad_code = open(self.openscad_source).read()
        self.args = args
        self.kwargs = kwargs
        if self.module_name is None:
            self.module_name = self.openscad_source.split('/')[-1].split('.')[0]

        super().__init__(*args, name=name, **kwargs)

    def get_source_file(self):
        """Gets the openscad source code path"""
        return self.openscad_source

    def render(self):
        """Imports the OpenScad source code and renders into a solid2 object"""
        filename = resolve_scad_filename(self.openscad_source)
        scad = get_scad_file_as_dict(filename)
        try:
            module = scad[self.module_name]
        except KeyError:
            raise Exception(f"No module {self.module_name} found in {self.openscad_source}")
        rendered = module(*self.args, **self.kwargs)
        return rendered

    def as_scad(self, rendered):
        """Returns the rendered argument (do nothing)"""
        return rendered

    @property
    def scad_code(self):
        """The contents of the code, plus a module call"""
        rendered = scad_render(self.model)
        module_call = rendered.strip().split('\n')[-1]
        return f'{self.openscad_code}\n\n{module_call}'
