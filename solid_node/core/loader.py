# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Project discovery and the one, shared node-reference resolver."""

import inspect
import os
import sys
import tomllib
from importlib import import_module

from solid_node.node.base import AbstractBaseNode
from solid_node.test import TestCase


class ProjectManifestError(Exception):
    pass


class AmbiguousNodeError(Exception):
    pass


def discover_project(origin=None):
    """Return ``(root, model_reference)`` for the nearest Solid project."""
    origin = os.path.realpath(origin or os.getcwd())
    directory = origin if os.path.isdir(origin) else os.path.dirname(origin)
    while True:
        manifest = os.path.join(directory, 'pyproject.toml')
        try:
            with open(manifest, 'rb') as stream:
                config = tomllib.load(stream)
            solid = config.get('tool', {}).get('solid-node')
            if solid is not None:
                model = solid.get('model')
                if not isinstance(model, str) or not model:
                    raise ProjectManifestError(
                        f"{manifest} has [tool.solid-node] but no model reference")
                return directory, model
        except FileNotFoundError:
            pass
        parent = os.path.dirname(directory)
        if parent == directory:
            raise ProjectManifestError(
                f"No pyproject.toml with [tool.solid-node] found above {origin}")
        directory = parent


def project_root(origin=None):
    return discover_project(origin)[0]


def _within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return os.path.commonpath((path, root)) == root


def _seed_project_path(root):
    if root not in sys.path:
        sys.path.insert(0, root)


def import_module_from_path(path, root=None):
    root = root or project_root(path)
    path = os.path.realpath(path)
    if not _within(path, root):
        raise ProjectManifestError(f"{path} is outside project root {root}")
    relative = os.path.relpath(path, root)
    if not relative.endswith('.py'):
        raise ProjectManifestError(f"Can only load .py files, not {path}")
    module_name = os.path.splitext(relative)[0].replace(os.sep, '.')
    if module_name.endswith('.__init__'):
        module_name = module_name[:-9]
    _seed_project_path(root)
    package = module_name.split('.', 1)[0]
    package_module = sys.modules.get(package)
    if package_module is not None and not _within(
            getattr(package_module, '__file__', ''), root):
        sys.modules.pop(package, None)
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        loaded_path = os.path.realpath(getattr(loaded, '__file__', ''))
        if loaded_path != path:
            # Test runs and long-lived hosts can load identically named
            # projects sequentially; never let that turn a reference into a
            # class object from the previous project.
            del sys.modules[module_name]
            package = module_name.rpartition('.')[0]
            if package:
                sys.modules.pop(package, None)
    return import_module(module_name)


def _defined_classes(path, module, base):
    return [(name, klass) for name, klass in module.__dict__.items()
            if isinstance(klass, type) and issubclass(klass, base)
            and klass.__name__ == name
            and os.path.realpath(inspect.getfile(klass)) == os.path.realpath(path)]


def find_class(path, module, BaseClass):
    """Compatibility helper: find the only locally defined class."""
    candidates = _defined_classes(path, module, BaseClass)
    if BaseClass is AbstractBaseNode and len(candidates) > 1:
        names = ', '.join(sorted(name for name, _ in candidates))
        raise AmbiguousNodeError(
            f"{path} defines multiple node classes ({names}); name a class in the reference")
    return candidates[0][1] if candidates else None


def _reference_parts(reference):
    left, separator, name = reference.rpartition(':')
    target = left if separator else reference
    candidate = target if os.path.isabs(target) else os.path.join(os.getcwd(), target)
    is_path = target.endswith('.py') or os.path.isfile(candidate)
    return target, (name if separator else None), is_path


def resolve_node(reference=None, origin=None):
    """Resolve a manifest, qualifier, path, or hybrid reference to a class.

    Path and qualifier routes deliberately import the module by its project
    dotted name, preserving class identity and ``sys.modules`` coherence.
    """
    if reference is None:
        # Only the manifest can say what the project's model is, so the
        # working directory is what identifies the project.
        root, reference = discover_project(origin)
        target, class_name, is_path = _reference_parts(reference)
    else:
        target, class_name, is_path = _reference_parts(reference)
        # A path identifies the project as surely as it identifies the file:
        # discover from the file itself, not from wherever the caller happens
        # to be standing. A qualifier carries no location, so it falls back to
        # the working directory.
        root = project_root(origin or (
            os.path.abspath(target) if is_path else None))
    if is_path:
        path = target if os.path.isabs(target) else os.path.realpath(
            os.path.join(os.getcwd(), target))
        if not os.path.isfile(path):
            raise ProjectManifestError(f"Node file not found: {target}")
        module = import_module_from_path(path, root)
    else:
        module_name = target
        _seed_project_path(root)
        loaded = sys.modules.get(module_name)
        if loaded is not None and not _within(
                getattr(loaded, '__file__', ''), root):
            sys.modules.pop(module_name, None)
            package = module_name.rpartition('.')[0]
            if package:
                sys.modules.pop(package, None)
        module = import_module(module_name)
        path = os.path.realpath(getattr(module, '__file__', ''))
        if not path:
            raise ProjectManifestError(f"Node module has no source file: {target}")

    if class_name:
        klass = getattr(module, class_name, None)
        if not isinstance(klass, type) or not issubclass(klass, AbstractBaseNode):
            raise ProjectManifestError(f"{reference} does not name an AbstractBaseNode class")
        klass_path = os.path.realpath(inspect.getfile(klass))
        if not _within(klass_path, root):
            raise ProjectManifestError(
                f"{reference} names a class outside project root {root}")
    else:
        klass = find_class(path, module, AbstractBaseNode)
        if klass is None:
            raise ProjectManifestError(f"No node class found in {reference}")
    return klass, path, root


def load_node(reference=None):
    klass, referenced_path, _ = resolve_node(reference)
    node = klass()
    # The named file is part of the selected entry point even when it is a
    # package facade; the implementation source is already in node.files.
    node.files.add(referenced_path)
    return node


def load_tests(path, root=None):
    """Return every companion ``TestCase`` defined next to ``path``."""
    root = root or project_root(path)
    path = os.path.realpath(path)
    filename = 'test.py' if os.path.basename(path) == '__init__.py' else \
        f"test_{os.path.basename(path)}"
    test_path = os.path.join(os.path.dirname(path), filename)
    if not os.path.exists(test_path):
        return []
    module = import_module_from_path(test_path, root)
    return [klass for _, klass in _defined_classes(test_path, module, TestCase)]


def load_test(path):
    """Backward-compatible singular API; callers should use ``load_tests``."""
    tests = load_tests(path)
    return tests[0]() if tests else None
