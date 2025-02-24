import os
import tempfile
import inspect
from solid2 import scad_render, import_scad
from solid2.core.parse_scad import get_scad_file_as_dict
from solid2.core.utils import resolve_scad_filename
from solid_node.node.leaf import LeafNode


class OpenScadNode(LeafNode):
    """
    Python wrapper around a pure scad module
    """

    namespace = 'solid2.core.object_factory'

    def __init__(self, source, *args, name=None, **kwargs):
        """Receives a source code and arguments, imports an OpenScad module from
        the source and renders it using *args and **kwargs
        The OpenScad code must implement a module with same name as file

        Args:
           source (str): The .scad source code, in the same folder as the python file
           *args: will be passed as arguments to the OpenScad module
           name keyword argument: the name of this node, defaul to name of the class
           **kwargs: will be passed as keyword arguments to the openscad module
        """
        frame = inspect.currentframe().f_back
        caller = frame.f_globals.get('__file__')
        basedir = os.path.dirname(caller)
        source_path = os.path.join(basedir, source)
        self.openscad_source = os.path.realpath(source_path)
        self.openscad_code = open(self.openscad_source).read()
        self.args = args
        self.kwargs = kwargs
        self.module_name = source.split('/')[-1].split('.')[0]

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
