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

    `targets` are keyed by driver name and expressed in DESIGN units;
    `duration` is in seconds, converted to whole ticks by the
    simulation that triggers it. The targets are copied on the way in
    so a declaration cannot be edited through the mapping a caller
    happens to still hold.
    """

    def __init__(self, targets, duration):
        duration = finite_seconds(duration, 'instruction duration')
        if duration < 0:
            raise ValueError(
                f'instruction duration must be non-negative, not {duration}')
        self.targets = dict(targets)
        self.duration = duration

    def __repr__(self):
        return f'<instruction {self.targets} over {self.duration}s>'
