# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Top-level package for Solid Framework API.

The backend classes below are resolved on first access rather than at
import. Importing any submodule runs this file first, so the eager
re-export list this replaces meant that `from solid_node.node.base import
AbstractBaseNode` -- what the loader, the builder, the piece inventory,
the test manager and the simulation enumerator all do -- pulled
`solid_node.exact` and therefore `cadquery` into every `solid`
invocation, including ones that touch no geometry at all.

Nothing here dispatches on a registry of subclasses, so no import was
load-bearing for a side effect and deferral is safe. PEP 562 hands back
the real class rather than a proxy, which matters: `CadQueryNode` is
built by the `CheckCQEditor` metaclass and consumers test these classes
with `issubclass` and `isinstance`.

`StlRenderStart` stays eager. `base` is on every path that matters and
costs about 0.11 s, so deferring it would complicate this module for no
measurable gain.

Build parameters are deliberately NOT here. `Length`, `Angle`, `Count`,
`Ratio`, `Scalar`, `Flag`, `Quantity` and `declared_parameters` are
exported by `solid_node.parameters`, so that an import line says which of
its names is a node kind and which is a knob on the machine. Only the
structural half of the declaration layer -- `declared_children` -- is a
node export. Do not re-export a parameter kind here: a second working
path restores exactly the ambiguity the split removed.
"""

__author__ = """Luis Fagundes"""
__email__ = 'lhfagundes@gmail.com'
__version__ = '0.4.0'

from importlib import import_module
from importlib.util import find_spec

from .base import StlRenderStart


# Each deferred export and the submodule that defines it. This is the
# whole public surface of the package; `__all__` is derived from it so
# the two cannot drift apart.
_EXPORTS = {
    'AssemblyNode': 'assembly',
    'Port': 'ports',
    'RotationalPort': 'ports',
    'TranslationalPort': 'ports',
    'SignalPort': 'ports',
    'declared_ports': 'ports',
    'declared_children': 'declarative',
    'FusionNode': 'fusion',
    'CadQueryNode': 'adapters.cadquery',
    'Build123dNode': 'adapters.build123d',
    'SheetLeafNode': 'sheet_leaf',
    'Build123dSheetNode': 'adapters.build123d_sheet',
    'FlexibleNode': 'flexible',
    'MolejoNode': 'adapters.molejo',
    'Solid2Node': 'adapters.solid2',
    'OpenScadNode': 'adapters.openscad',
    'JScadNode': 'adapters.jscad',
    'StlNode': 'adapters.stl',
    'property_as_number': 'decorators',
}

__all__ = ['StlRenderStart', *_EXPORTS]


def _load(module_name, requested):
    """Import `.module_name`, blaming `requested` if it cannot be.

    A failed deferred import must not reach the caller as a missing
    attribute: `hasattr` and every other lookup that treats an accessor
    as a probe would turn a broken install into "no such name". The
    original error is re-raised -- same class, same `name`, same
    traceback -- with the requested export spliced into its message, so
    the report says both what is broken and what asked for it.
    """
    try:
        return import_module(f'.{module_name}', __name__)
    except ImportError as failure:
        blame = (f'{failure} (raised resolving {__name__}.{requested} '
                 f'from .{module_name})')
        # Both, deliberately: `ImportError.__str__` reports `msg` when it
        # is set and falls back to `args` otherwise, so setting only one
        # leaves the other stale for anything that reads it directly.
        failure.msg = blame
        failure.args = (blame, *failure.args[1:])
        raise


def _submodule(name):
    """The submodule called `name`, or None when there is no such file.

    Only an absent submodule may become an `AttributeError`; one that
    exists and fails to import is a broken install and reports itself.
    """
    if name.startswith('__') and name.endswith('__'):
        return None
    try:
        if find_spec(f'{__name__}.{name}') is None:
            return None
    except (ImportError, ValueError):
        return None
    return _load(name, name)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        # The eager re-exports used to bind every submodule as a side
        # effect of the import machinery, so a consumer could read
        # `solid_node.node.assembly` after importing only the package.
        module = _submodule(name)
        if module is None:
            raise AttributeError(
                f'module {__name__!r} has no attribute {name!r}')
        globals()[name] = module
        return module

    value = getattr(_load(module_name, name), name)
    # Cached before returning, so a later access is a plain dict lookup
    # and a submodule that reads a lazy name off this package during its
    # own import cannot re-enter this accessor forever.
    globals()[name] = value
    return value


def __dir__():
    return sorted({*globals(), *__all__})
