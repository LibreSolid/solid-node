# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Project discovery and the one, shared node-reference resolver."""

import inspect
import os
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib import import_module

from solid_node.node.base import AbstractBaseNode
from solid_node.node.declarative import parse_overrides
from solid_node.simulation.enumeration import bind_declared_defaults

__all__ = ['load_node', 'parse_overrides', 'read_project', 'select_model']


class ProjectManifestError(Exception):
    pass


class AmbiguousNodeError(Exception):
    pass


#: A declared model name: one word, so it can never be read as a qualifier
#: (which carries a `.` or a `:`) or as a path.
MODEL_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')


@dataclass(frozen=True)
class Model:
    """One model a project declares.

    `name` is None for the single model of a manifest without a `models`
    table; `build_dir` is where that model publishes -- the build root
    itself for a single model, `<build root>/<name>` for a declared one.
    """

    name: str | None
    reference: str
    build_dir: str


@dataclass(frozen=True)
class Project:
    """What a manifest says about a project: its root and its models."""

    root: str
    manifest: str
    build_root: str
    models: tuple
    default: Model | None
    #: Whether the manifest declares its models by name.
    named: bool

    def model(self, name):
        """The declared model called `name`, or None."""
        for model in self.models:
            if model.name is not None and model.name == name:
                return model
        return None

    @property
    def names(self):
        return [model.name for model in self.models if model.name]


def _find_manifest(origin=None):
    origin = os.path.realpath(origin or os.getcwd())
    directory = origin if os.path.isdir(origin) else os.path.dirname(origin)
    while True:
        manifest = os.path.join(directory, 'pyproject.toml')
        try:
            with open(manifest, 'rb') as stream:
                config = tomllib.load(stream)
            solid = config.get('tool', {}).get('solid-node')
            if solid is not None:
                return directory, manifest, solid
        except FileNotFoundError:
            pass
        parent = os.path.dirname(directory)
        if parent == directory:
            raise ProjectManifestError(
                f"No pyproject.toml with [tool.solid-node] found above {origin}")
        directory = parent


def read_project(origin=None):
    """The nearest Solid project above `origin`, as a `Project`.

    Reads the manifest and looks at the project root's directories; never
    imports project code, so a host may call it as often as it likes.
    """
    root, manifest, solid = _find_manifest(origin)
    # Local import: builder imports this module at load time.
    from solid_node.core.builder import project_build_root
    build_root = project_build_root(root)
    table = solid.get('models')
    model = solid.get('model')
    if table is None:
        if not isinstance(model, str) or not model:
            raise ProjectManifestError(
                f"{manifest} has [tool.solid-node] but no model reference")
        only = Model(None, model, build_root)
        return Project(root, manifest, build_root, (only,), only, False)

    if not isinstance(table, dict) or not table:
        raise ProjectManifestError(
            f"{manifest} declares [tool.solid-node.models] with no models")
    models = []
    for name, reference in table.items():
        if not MODEL_NAME.match(name):
            raise ProjectManifestError(
                f"{manifest} declares the model name {name!r}; a name is one "
                f"word of letters, digits, underscores and hyphens")
        if not isinstance(reference, str) or ':' not in reference:
            raise ProjectManifestError(
                f"{manifest} declares model {name!r} as {reference!r}; a "
                f"model is a reference of the form package.module:Class")
        if os.path.isdir(os.path.join(root, name)):
            raise ProjectManifestError(
                f"{manifest} declares a model named {name!r}, but {name}/ is "
                f"a directory at the project root and its artifacts would "
                f"mirror into the model's build directory; rename the model")
        models.append(Model(name, reference, os.path.join(build_root, name)))
    default = None
    if model is not None:
        default = next((m for m in models if m.name == model), None)
        if default is None:
            raise ProjectManifestError(
                f"{manifest} sets model = {model!r}, which must name one of "
                f"the declared models: {', '.join(m.name for m in models)}")
    return Project(root, manifest, build_root, tuple(models), default, True)


def discover_project(origin=None):
    """Return ``(root, model_reference)`` for the nearest Solid project.

    The reference is the default model's; None when the project declares
    models and no default.
    """
    project = read_project(origin)
    return project.root, (project.default.reference if project.default
                          else None)


def project_root(origin=None):
    return _find_manifest(origin)[0]


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


def _default_reference(project):
    if project.default is None:
        raise ProjectManifestError(
            f"{project.manifest} declares models {', '.join(project.names)} "
            f"and no default; name one, or set model = \"<name>\"")
    return project.default.reference


def _named_reference(reference, origin=None):
    """A bare word that a project declares as a model name is that
    model's reference; anything else is left for the other spellings."""
    target, class_name, is_path = _reference_parts(reference)
    if is_path or class_name is not None or not MODEL_NAME.match(target):
        return reference
    model = read_project(origin).model(target)
    return model.reference if model else reference


@dataclass(frozen=True)
class Selection:
    """What a command is about to work on: the concrete reference to load
    and, for a project model, the build directory it owns."""

    reference: str | None
    build_dir: str | None
    model: Model | None

    def anchor(self):
        """Make `build_dir` this process's build directory -- and its
        children's, through the environment -- before any node is loaded.
        A selection that is not a project model leaves the directory as it
        is: a sub-node builds in the build root, as it always did."""
        if self.build_dir is None:
            return
        from solid_node.core.builder import anchor_build_dir
        anchor_build_dir(os.path.dirname(self.build_dir)
                         if self.model and self.model.name else self.build_dir,
                         self.build_dir)


def select_model(reference=None, origin=None):
    """Turn a reference, or none, into the thing to load and where it
    builds. No reference selects the default model; a declared name its
    model; anything else passes through untouched, to be read by the
    loader's other spellings."""
    if reference is None:
        project = read_project(origin)
        model = project.default
        if model is None:
            _default_reference(project)
        return Selection(model.reference, model.build_dir, model)
    target, class_name, is_path = _reference_parts(reference)
    if not is_path and class_name is None and MODEL_NAME.match(target):
        model = read_project(origin).model(target)
        if model is not None:
            return Selection(model.reference, model.build_dir, model)
    return Selection(reference, None, None)


def resolve_node(reference=None, origin=None):
    """Resolve a manifest, qualifier, path, or hybrid reference to a class.

    Path and qualifier routes deliberately import the module by its project
    dotted name, preserving class identity and ``sys.modules`` coherence.
    """
    if reference is None:
        # Only the manifest can say what the project's model is, so the
        # working directory is what identifies the project.
        project = read_project(origin)
        root, reference = project.root, _default_reference(project)
        target, class_name, is_path = _reference_parts(reference)
    else:
        reference = _named_reference(reference, origin)
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


def load_node(reference=None, overrides=None):
    """The root node `reference` names, realized with its defaults --
    or, for a root that declares parameters, with `overrides`: the
    `name=value` words of `--set`, each parsed by the declared kind and
    checked as a Python caller's value would be."""
    klass, referenced_path, _ = resolve_node(reference)
    node = klass(**parse_overrides(klass, overrides))
    # The named file is part of the selected entry point even when it is a
    # package facade; the implementation source is already in node.files.
    node.files.add(referenced_path)
    # A driver-declaring assembly reads its drivers in render(), and every
    # build, test and viewer path renders long before a simulation exists,
    # so the declarations' own defaults are bound here -- across the whole
    # tree, by qualified id -- rather than restated in the project's
    # __init__. A tree that declares no driver is left strictly alone, so
    # a driverless project loads exactly as it always did.
    #
    # This is the layer that may import the simulation package; the node
    # layer never does.
    bind_declared_defaults(node)
    return node


def load_tests(path, root=None):
    """Return every companion ``TestCase`` defined next to ``path``."""
    # Imported here rather than at module scope because this is its only
    # use site, and this module is on the path of every node-scoped
    # command: `solid_node.test` reaches `solid_node.exact` and so
    # `cadquery`, which a build has no use for. Deferred, not optional --
    # discovering a test still imports the framework, right here.
    from solid_node.test import TestCase

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
