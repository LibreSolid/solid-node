import os
import sys
import inspect
from importlib import import_module
from solid_node.node.base import AbstractBaseNode
from solid_node.test import TestCase

sys.path.append(os.getcwd())

def load_node(path):
    if not path.endswith('.py'):
        raise Exception("Can only load .py files")
    return load_instance(path, AbstractBaseNode)

def load_test(path):
    if not path.endswith('.py'):
        raise Exception("Can only load .py files")

    parts = path.split('/')
    parts[-1] = f'test_{parts[-1]}'
    path = '/'.join(parts)

    if os.path.exists(path):
        return load_instance(path, TestCase)

def load_instance(path, BaseClass):
    path = os.path.realpath(path)
    module = import_module_from_path(path)
    klass = find_class(path, module, BaseClass)
    return klass()


def import_module_from_path(path):
    relative_path = os.path.relpath(path)
    module_name = relative_path.replace('/', '.')[:-3]
    return import_module(module_name)


def find_class(path, module, BaseClass):
    for name, klass in module.__dict__.items():
        if isinstance(klass, type) and issubclass(klass, BaseClass) \
           and inspect.getfile(klass) == path:
            return klass
