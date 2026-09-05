# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The declared time base of an animation timeline.

`AssemblyNode.time` is one entry of the driver snapshot with a symbolic
fallback (ADR-008): bound, it reports the bound number; unbound, solid2's
`$t`, the normalized 0..1 turn every document consumer plays. What that
number MEANS was the binder's choice -- a keyframe bound a fraction, a
stepped simulation bound seconds -- and nothing let the model settle it.

A root assembly settles it here::

    class WallClock(AssemblyNode):
        time = Time(loop=12 * 3600)

`loop` is the span of machine time, in seconds, that one turn of the
timeline covers. From then on `self.time` reads SECONDS on every path:
`$t * loop` when nothing is bound, so the published expressions carry
the conversion and `$t` stays the slider; the bound number under
`set_keyframe`, the testing decorators and `Sim`, all of which state
seconds. Every assembly below the root reads the root's time base.

The declaration is a data descriptor bound to the name `time` -- the
same shape `DriverDeclaration` has, and for the same reason: the
declaration is class metadata shared by every instance, the value
belongs to one node's snapshot, and `self.time` has to stay the single
read surface. It is not a driver: it is never enumerated into a
document's `drivers` table, has no default to bind, and is published as
`$t` already.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Time:
    """A root assembly's time base: `time = Time(loop=<seconds>)`.

    Frozen on purpose, like a driver declaration: an attribute that
    could be assigned here would be state shared by every node of the
    class. Readable off the class (`Root.time.loop`) without
    constructing anything, so a producer can publish the loop the way
    it publishes the driver table.
    """

    loop: float

    def __post_init__(self):
        loop = self.loop
        if (isinstance(loop, bool) or not isinstance(loop, (int, float))
                or not math.isfinite(loop) or loop <= 0):
            raise ValueError(
                f'Time(loop=...) must be a positive finite number of '
                f'seconds, the span of machine time one turn of the '
                f'timeline covers; got {loop!r}')
        object.__setattr__(self, 'loop', float(loop))

    def __set_name__(self, owner, name):
        if name != 'time':
            raise TypeError(
                f"{owner.__name__}.{name}: a time base is declared as "
                f"'time', the property every simulate() reads; "
                f"'{name}' would leave nothing to tie it to. Write "
                f"time = Time(loop=...).")
        from .assembly import AssemblyNode
        if not issubclass(owner, AssemblyNode):
            raise TypeError(
                f'{owner.__name__} cannot declare a time base: only an '
                f'AssemblyNode animates, so only an AssemblyNode has a '
                f'time to declare the base of.')

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        from .assembly import read_time
        return read_time(instance)

    def __set__(self, instance, value):
        raise AttributeError(
            f'time of {type(instance).__name__} cannot be assigned: its '
            f'value belongs to the bound snapshot. Use '
            f'set_keyframe({value!r}) -- in seconds, under a declared '
            f'time base.')


def declared_time(cls):
    """The `Time` declaration of `cls`, or None when it declares none.

    Base-first through the MRO, stopping at the first `time` found: a
    subclass inherits its parent's declaration, and a class whose
    nearest `time` is the base property declares nothing. A class with
    no `time` at all -- not a node -- declares nothing either.
    """
    for klass in getattr(cls, '__mro__', ()):
        found = vars(klass).get('time')
        if found is None:
            continue
        return found if isinstance(found, Time) else None
    return None
