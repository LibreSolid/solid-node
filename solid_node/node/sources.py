# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The set of project files a node's source really depends on.

A node used to track only the file it was defined in, which is wrong
whenever geometry comes from somewhere else: v8-engine's crankshaft.py
and cylinder_unit.py both take dimensions from kinematics.py, a module
that defines no node. Editing it changed the model and moved no tracked
mtime, so every artifact still reported up to date.

The closure below is deliberately an over-approximation. An extra file
in the set costs an unnecessary rebuild; a missing one serves a stale
model, which is the worse failure, so every ambiguity resolves toward
including the file.
"""

import ast
import os
import sys
from importlib.util import resolve_name


# The framework is a library, not project source. It normally lives in
# site-packages, well outside any project, but when the framework tests
# itself the checkout IS the working directory -- so exclude it by path
# rather than relying on where it happens to be installed.
FRAMEWORK_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Per-file import lists, keyed on (path, mtime) so an edited file is
# re-parsed and its stale entry evicted -- the same shape as the base
# mesh cache in base.py.
_import_cache = {}


def source_closure(src):
    """Every project file the node defined in `src` depends on.

    Returns `src` itself together with the project-local modules it
    imports, transitively. The spelling of `src` is preserved: callers
    compare it against node.src.
    """
    # Local import avoids the loader -> node.base -> sources import cycle.
    from solid_node.core.loader import project_root
    root = project_root(src)
    start = os.path.realpath(src)

    found = {start}
    pending = [start]
    while pending:
        for path in _project_imports(pending.pop(), root):
            if path not in found:
                found.add(path)
                pending.append(path)

    found.discard(start)
    return {src} | found


def _project_imports(path, root):
    mtime = os.path.getmtime(path) if os.path.exists(path) else None
    key = (path, mtime)
    cached = _import_cache.get(key)
    if cached is None:
        for stale in [k for k in _import_cache if k[0] == path]:
            del _import_cache[stale]
        cached = _import_cache[key] = _parse_project_imports(path, root)
    return cached


def _parse_project_imports(path, root):
    if not path.endswith('.py'):
        # A JScadNode's source file is its .js; nothing to parse.
        return frozenset()

    try:
        with open(path, 'rb') as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError):
        # A file the builder is about to fail on anyway. Tracking
        # nothing extra here leaves today's behaviour untouched.
        return frozenset()

    package = _package_of(path)

    names = set()
    for statement in ast.walk(tree):
        if isinstance(statement, ast.Import):
            names.update(alias.name for alias in statement.names)
        elif isinstance(statement, ast.ImportFrom):
            names.update(_import_from_targets(statement, package))

    return frozenset(
        found for found in (_project_file(name, root) for name in names)
        if found is not None
    )


def _package_of(path):
    """The package a file was imported as, needed to resolve its
    relative imports. Taken from the interpreter, which has already
    done the resolution correctly."""
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and os.path.realpath(filename) == path:
            return getattr(module, '__package__', None) or None
    return None


def _import_from_targets(statement, package):
    """Module names a `from ... import ...` statement can refer to."""
    module = statement.module or ''

    if statement.level:
        if package is None:
            return ()
        try:
            base = resolve_name('.' * statement.level + module, package)
        except (ImportError, ValueError):
            return ()
    else:
        base = module

    if not base:
        return ()

    # An imported name may itself be a submodule (`from pkg import mod`),
    # so offer both readings and let sys.modules decide.
    return [base] + [f'{base}.{alias.name}' for alias in statement.names]


def _project_file(name, root):
    """The project file a module name resolves to, or None if it is not
    one the node should track."""
    module = sys.modules.get(name)
    if module is None:
        return None

    filename = getattr(module, '__file__', None)
    if not filename:
        return None

    path = os.path.realpath(filename)

    # A package __init__ is, in the conventional layout, the root
    # assembly's own source: it imports every node in the project.
    # Python executes it to resolve any relative import, so following
    # it would put every node's source in every node's set and one edit
    # would invalidate everything. The cost is that a constant reached
    # through the package rather than through a named module is not
    # tracked -- that import is a child depending on its parent, the
    # one direction the tree's upward aggregation cannot express.
    if os.path.basename(path) == '__init__.py':
        return None

    if not path.startswith(root + os.sep):
        return None

    if path == FRAMEWORK_DIR or path.startswith(FRAMEWORK_DIR + os.sep):
        return None

    return path
