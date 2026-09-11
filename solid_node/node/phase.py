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

It also holds the ENUMERATION: the whole-tree pass one outermost
``render()`` opens (`whole-tree-fixpoint`). An enumeration is a single
solve of a tree -- every assembly's phase runs once, parents before
children, and what one assembly's own attempt could not resolve is
deferred here rather than refused. `Enumeration.deferred` and
`Enumeration.reads` are plain lists a caller in `solid_node.motion` fills
and drains; this module never imports that layer and knows nothing about
what a "deferred item" or a "binder" is -- it just keeps the containers
and the stack, exactly as it keeps the phase stack next to it.
"""

import sys
import warnings


RENDER = 'render'
SIMULATE = 'simulate'


class Phase:
    """One assembly running one lifecycle method."""

    __slots__ = ('assembly', 'kind', 'applied', 'read', 'bound')

    def __init__(self, assembly, kind):
        self.assembly = assembly
        self.kind = kind
        # Every operation applied while this phase is innermost, so a
        # render that turns out to have read nothing can untag them.
        self.applied = []
        # The first driver, time or port read, as (what, name), or None.
        self.read = None
        # Every coordinate slot BOUND while this phase is running --
        # the author's own simulate() and this assembly's own relation
        # attempt alike -- so the assembly's NEXT phase can clear
        # exactly what this one bound (whole-tree-fixpoint).
        self.bound = []


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


def note_bound(slot):
    """Report that `slot` was just bound, while a SIMULATE phase is
    running -- the author's own binding and a relation's/wiring's/derived
    coordinate's alike, since both happen while that assembly's phase is
    current. Recorded on the phase so its own NEXT run's `clear_solved`
    knows what to drop; a binding made in a RENDER phase or with no phase
    at all is not recorded, exactly as an operation applied there is
    never swept."""
    phase = current()
    if phase is not None and phase.kind == SIMULATE:
        phase.bound.append(slot)


##############################################
# The enumeration: one tree pass, one solve

class Enumeration:
    """One ENUMERATION of a tree: opened by the `render()` call that
    finds none in progress, closed when that call returns.

    `deferred` and `reads` are generic containers; what they hold is
    `solid_node.motion.couplings`'s business (a `_Deferred` bundle of a
    relation/wiring/derived-coordinate leftover, and an unbound-read
    record) -- this module only keeps the list alive for the length of
    the pass.
    """

    __slots__ = ('deferred', 'reads')

    def __init__(self):
        self.deferred = []
        self.reads = []


_enumerations = []


def current_enumeration():
    """The open enumeration, or None outside any tree pass."""
    return _enumerations[-1] if _enumerations else None


def open_enumeration():
    enumeration = Enumeration()
    _enumerations.append(enumeration)
    return enumeration


def close_enumeration():
    _enumerations.pop()


def note_unbound_read(slot):
    """Report a read of a coordinate slot holding NO value, made while a
    SIMULATE phase is running and an enumeration is open -- the read the
    `couplings` "a read of a coordinate a relation binds is refused"
    rule is judged against, at the end of the enumeration, by what the
    slot's binder turns out to be.

    Costs two attribute reads off the calling frame's code object and a
    tuple; the frame itself is never kept. A read outside any simulate
    phase, or with no enumeration open (a bare construction, a test
    reading a coordinate after the walk is long over), is not recorded --
    there is no pass left to judge it at the end of.
    """
    phase = current()
    enumeration = current_enumeration()
    if phase is None or phase.kind != SIMULATE or enumeration is None:
        return
    frame = sys._getframe(2)
    enumeration.reads.append(
        (slot, phase.assembly, type(phase.assembly),
         frame.f_code.co_filename, frame.f_lineno))


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
