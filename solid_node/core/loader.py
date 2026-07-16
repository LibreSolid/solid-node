# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import inspect
from importlib import import_module
from solid_node.node.base import AbstractBaseNode
from solid_node.test import TestCase

sys.path.append(os.getcwd())


def load_node(path):
    if not path.endswith('.py'):
        raise Exception(f"Can only load .py files, not {path}")
    return load_instance(path, AbstractBaseNode)


def load_test(path):
    if not path.endswith('.py'):
        raise Exception(f"Can only load .py files, not {path}")

    parts = path.split('/')
    if parts[-1] == '__init__.py':
        parts[-1] = 'test.py'
    else:
        parts[-1] = f'test_{parts[-1]}'
    test_path = '/'.join(parts)
    if os.path.exists(test_path):
        return load_instance(test_path, TestCase)


def load_instance(path, BaseClass):
    path = os.path.realpath(path)
    module = import_module_from_path(path)
    klass = find_class(path, module, BaseClass)
    return klass()


def import_module_from_path(path):
    relative_path = os.path.relpath(path)
    module_name = relative_path.replace('/', '.')[:-3]
    return import_module(module_name)


NODE_MARKER = 'NODE'


class AmbiguousNodeError(Exception):
    """Raised when a file loaded by path defines several
    AbstractBaseNode subclasses and no NODE marker (or an invalid one)
    names which one is the actual node."""


def find_class(path, module, BaseClass):
    """Return the class in `module` to instantiate for `path`.

    Historically this returned the FIRST BaseClass subclass defined in
    the file -- an unenforced "main class first" convention that,
    when violated, silently loaded the wrong node. For AbstractBaseNode
    lookups (node files, not test files) a file may instead set a
    module-level `NODE = MyClass` to name the node class explicitly; a
    file defining several node classes with no such marker now fails
    loudly instead of silently picking one. TestCase resolution
    (load_test) is unaffected: the marker rule is for NODE classes
    only.
    """
    candidates = [
        (name, klass) for name, klass in module.__dict__.items()
        if isinstance(klass, type) and issubclass(klass, BaseClass)
        and inspect.getfile(klass) == path
    ]

    if BaseClass is AbstractBaseNode:
        marker = getattr(module, NODE_MARKER, None)
        if marker is not None:
            return _resolve_marker(path, BaseClass, marker)
        if len(candidates) > 1:
            names = ', '.join(sorted(name for name, _ in candidates))
            raise AmbiguousNodeError(
                f"{path} defines multiple node classes ({names}) and "
                f"has no NODE marker to say which one is the node -- "
                f"add NODE = <ClassName> naming the intended one.")

    if not candidates:
        return None
    return candidates[0][1]


def _resolve_marker(path, BaseClass, marker):
    if not (isinstance(marker, type) and issubclass(marker, BaseClass)):
        raise AmbiguousNodeError(
            f"{path} sets NODE = {marker!r}, which is not a "
            f"{BaseClass.__name__} subclass.")
    if inspect.getfile(marker) != path:
        raise AmbiguousNodeError(
            f"{path} sets NODE = {marker.__name__}, but that class "
            f"is not defined in this file (it's imported) -- NODE "
            f"must name a class defined in this same file.")
    return marker
