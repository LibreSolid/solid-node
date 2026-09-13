# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Named instructions: driver targets in design units, plus a duration.

An instruction is what a button press means. A maker states "home X"
as `x = 0` in millimetres, not as 0 microsteps: the spike wrote its
targets in driver-native units and recorded that as a seam to close
(spike/FINDINGS.md seam 4). The conversion itself belongs to the
driver declaration, which is the one place that knows what a native
unit of that driver is worth, so an instruction stays a plain record
of intent and carries no unit knowledge at all.

Semantics are deliberately held to target-plus-duration linear ramps.
Sequencing ("home X, then home Y") is the beginning of a program, and
that is the G-code layer's job -- faking it here would have to be
unfaked later.
"""

from .timebase import finite_seconds


class Instruction:
    """A named event source declared on an assembly.

    An instruction states exactly ONE of two things, both keyed by
    class-local driver name and both in DESIGN units:

    - `targets`, where the drivers are to LAND -- the absolute form
      every existing document publishes; and
    - `by`, how far they are to TRAVEL from wherever they stand -- the
      relative form a running machine needs, where "advance the dial one
      step" has no absolute answer (OpenSpec change
      ``run-owns-the-coordinates``).

    Both, or neither, is refused here: an instruction that stated both
    would have two answers for one press, and one that stated neither
    would move nothing. The one given reads back under its own name and
    the other reads `None`.

    `duration` is in seconds, converted to whole ticks by the simulation
    that triggers it. The mapping is copied on the way in so a
    declaration cannot be edited through one a caller happens to still
    hold.
    """

    def __init__(self, targets=None, duration=None, *, by=None):
        if (targets is None) == (by is None):
            raise TypeError(
                'an instruction states exactly one of targets= (where the '
                'drivers land) and by= (how far they travel from where '
                'they stand), both in design units; '
                f'got targets={targets!r} and by={by!r}.')
        duration = finite_seconds(duration, 'instruction duration')
        if duration < 0:
            raise ValueError(
                f'instruction duration must be non-negative, not {duration}')
        self.targets = None if targets is None else dict(targets)
        self.by = None if by is None else dict(by)
        self.duration = duration

    @property
    def relative(self):
        """Whether this instruction states travel rather than a landing
        place."""
        return self.by is not None

    def __repr__(self):
        stated = (f'by {self.by}' if self.relative else f'to {self.targets}')
        return f'<instruction {stated} over {self.duration}s>'
