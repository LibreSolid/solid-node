# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class NamedSizes(AssemblyNode):
    """Green fixture (skill-repo improvements.md #3): two Cubes with
    explicit, DISTINCT names and different sizes. This already passes
    on the OLD framework too -- different names already meant different
    artifact files, so it does not by itself expose the bug. The real
    lie is the SAME-name case: see
    tests.test_uniq_id.SameNameDifferentParamsBuildTest, which same-name
    siblings colliding in the viewer tree (a separate open issue, #16)
    make awkward to express as a meta fixture. Kept here as the
    adversarial green twin, proving the fix does not regress the
    already-working distinct-names case."""

    def __init__(self):
        self.small = Cube(size=1.0, name='small')
        self.big = Cube(size=2.0, name='big')
        super().__init__()

    def render(self):
        return [self.small, self.big]
