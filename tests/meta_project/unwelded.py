# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode, FusionNode

from .parts import Cube


class Unwelded(AssemblyNode):
    """Red fixture: the solid IS one connected body, so the build's
    integrity check passes -- but the two features the test names reach
    each other only through a third.

    This is the gap the build cannot see and the removed body-count
    assertions could not express either. `assertJoined` must still fail
    here, or it adds nothing over the guarantee the builder already
    gives."""

    def __init__(self):
        self.bracket = Bracket()
        super().__init__()

    def render(self):
        self.bracket.translate([25, 0, 0])
        return [self.bracket]


class Bracket(FusionNode):
    """hub -- bridge -- boss, welded in a chain. Every link overlaps
    its neighbour, so the fusion is a single body, but hub and boss are
    0.2mm apart and never touch."""

    def __init__(self):
        self.hub = Cube()
        self.bridge = Cube()
        self.boss = Cube()
        super().__init__()
        self.bridge.translate([0.6, 0, 0])
        self.boss.translate([1.2, 0, 0])

    def render(self):
        return [self.hub, self.bridge, self.boss]
