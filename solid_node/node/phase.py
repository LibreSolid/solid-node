# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The lifecycle phase an assembly is in while its code runs.

An assembly builds the machine at rest in ``render()`` and moves it in
``simulate()``. The framework runs the two one after the other and needs
to know, while an author's code runs, which of them it is executing: an
operation applied during ``simulate()`` is motion -- inserted innermost,
tagged with the simulating assembly, swept before its next run -- and one
applied during a once-only ``render()`` is rest placement that persists.
A driver, time or port read during ``render()`` is what tells the
framework that a class has not migrated yet, and is reported here.

This module holds only the stack and the reporter, and imports nothing
from the node layer, so the descriptors that report reads (a driver
declaration, a port slot, the ``time`` property) can import it without
a cycle.
"""

import warnings


RENDER = 'render'
SIMULATE = 'simulate'


class Phase:
    """One assembly running one lifecycle method."""

    __slots__ = ('assembly', 'kind', 'applied', 'read')

    def __init__(self, assembly, kind):
        self.assembly = assembly
        self.kind = kind
        # Every operation applied while this phase is innermost, so a
        # render that turns out to have read nothing can untag them.
        self.applied = []
        # The first driver, time or port read, as (what, name), or None.
        self.read = None


_stack = []


def current():
    """The innermost phase, or None outside any lifecycle method."""
    return _stack[-1] if _stack else None


def push(assembly, kind):
    phase = Phase(assembly, kind)
    _stack.append(phase)
    return phase


def pop():
    _stack.pop()


def note_read(what, name):
    """Report that a driver, time or port value was read, or a port
    bound: ``what`` is the verb phrase the warning prints, ``'read
    driver'``, ``'read time'``, ``'read port'`` or ``'bound port'``.

    Only a render phase records it -- a read in ``simulate()`` is the
    point of ``simulate()`` -- and only the first is kept, which is the
    one the deprecation warning names. A binding counts like a read
    because a once-only render() would bind once and never rebind.
    """
    phase = current()
    if phase is not None and phase.kind == RENDER and phase.read is None:
        phase.read = (what, name)


_warned = set()


def warn_legacy_render(assembly, read):
    """One FutureWarning per class whose render() read a driver.

    FutureWarning rather than DeprecationWarning because Python shows
    the former to end users by default and hides the latter outside
    ``__main__`` and test runners; a maker running ``solid build`` has to
    see this one. Deduplicated by class here rather than by call site,
    so the message does not depend on which walker rendered first.
    """
    cls = type(assembly)
    if cls in _warned:
        return
    _warned.add(cls)
    what, name = read
    warnings.warn(
        f"{cls.__name__}.render() {what} '{name}'. Reading drivers, time "
        f"or ports in render(), or binding a port there, is deprecated: "
        f"render() builds the machine at rest and the framework runs it "
        f"once per instance. Move the read or binding and the operations "
        f"it feeds into simulate(), which runs on every instant. Until "
        f"then {cls.__name__} re-renders per binding as before.",
        FutureWarning, stacklevel=3)
