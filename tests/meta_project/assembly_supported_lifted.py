# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Animated fixture: a block resting flush on its base at t=0, lifted
3mm clear of it by t=1.

The support verdict has to come from the instant the runner placed the
assembly at, so the same one-line assertion passes at the first instant
and fails at the second -- the assertion itself neither accepts nor sets
a keyframe.
"""

from solid_node.node import AssemblyNode

from .support_parts import Block


class AssemblySupportedLifted(AssemblyNode):

    def __init__(self):
        self.base = Block([4, 4, 2])
        self.block = Block([2, 2, 2])
        super().__init__()

    def render(self):
        # t=0: resting flush at z=2; t=.5: 1.5 clear, past the drop;
        # t=1: 3 clear.
        self.block.translate([1, 1, 2 + 3 * self.time])
        return [self.base, self.block]
