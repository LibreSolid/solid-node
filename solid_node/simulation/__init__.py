# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Stepped simulation: drivers, instructions, and the fixed-dt loop.

A machine that is not periodic -- a printer executing instructions, a
car with independent steering and throttle -- cannot be written as a
function of ADR-008's single looping scalar. This package is the layer
that produces the driver snapshots the node layer already knows how to
bind: state advances here, in exactly one place, and geometry stays a
pure function of the snapshot.

The dependency runs one way. solid_node.node never imports this
package; a project declares Drivers as class attributes and the
simulation discovers them off the class -- across the whole linked
tree, by qualified id (`enumeration.qualified_drivers`) -- so a node
without drivers carries no simulation import anywhere.

The exports below are resolved on first access rather than at import,
for the same reason `solid_node/node/__init__.py` resolves its backend
exports that way. Importing a submodule runs this file first, so the
eager re-export list this replaces meant that
`from solid_node.simulation.enumeration import tree_declares_drivers`
-- what the serializer does on every publication, and the loader on
every node load -- ran `.scenario`, which imports `solid_node.test`
and through it `solid_node.exact` and `cadquery`. A project that runs
no scenario paid for the whole exact stack to publish a document.

Deferral is safe here for the same reason it is safe there: nothing
dispatches on a registry built by these imports, so none of them is
load-bearing for a side effect. And it does not make the test
framework optional -- naming `ScenarioTest` imports it exactly as
before.
"""

from importlib import import_module
from importlib.util import find_spec


# Each deferred export and the submodule that defines it. This is the
# whole public surface of the package; `__all__` is derived from it so
# the two cannot drift apart.
_EXPORTS = {
    'Driver': 'driver',
    'RampProgram': 'driver',
    'qualified_drivers': 'enumeration',
    'qualified_instructions': 'enumeration',
    'Instruction': 'instruction',
    'ScenarioTest': 'scenario',
    'Sim': 'sim',
    # The running mode's error kinds, and the entries its crossing and
    # stop records are made of. Lazy like every export here, and for one
    # more reason: naming any of them imports the running engine, which a
    # model declaring no running time never pays for.
    'RunConflict': 'run',
    'UnsupportedLaw': 'program',
    'TooManyCrossings': 'program',
    'Crossing': 'program',
    'Stop': 'program',
}

__all__ = list(_EXPORTS)


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
        # `solid_node.simulation.sim` after importing only the package.
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
