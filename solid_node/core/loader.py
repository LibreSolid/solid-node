import os
import inspect
from importlib import import_module
from solid_node.node.base import AbstractBaseNode

def load_node(path):
    if not path.endswith('.py'):
        raise Exception("Can only load .py files")

    path = os.path.realpath(path)
    relative_path = os.path.relpath(path)
    module_name = relative_path.replace('/', '.')[:-3]

    module = import_module(module_name)

    for name, klass in module.__dict__.items():
        if isinstance(klass, type) and issubclass(klass, AbstractBaseNode) \
           and inspect.getfile(klass) == path:
            return klass()
