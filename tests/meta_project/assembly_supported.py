# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Green fixture for assertAssemblySupported: three groups whose parts
are all genuinely held against gravity, each by a different mechanism.

The groups are spread along Y so they never touch, and each is asserted
on its own subtree -- the assembly's furthest extent along gravity is
the hook post's foot, and a group standing on its own base is grounded
by ITS lowest solid, not by another group's. The whole-assembly test
then anchors every group explicitly.
"""

from solid_node.node import AssemblyNode

from .support_parts import Block, Hook, LeftHook, RightHook


class AssemblySupported(AssemblyNode):

    def __init__(self):
        self.stack = Stack()
        self.hanging = Hanging()
        self.fitted = Fitted()
        self.leaning = Leaning()
        super().__init__()
        self.hanging.translate([0, 20, 0])
        self.fitted.translate([0, 40, 0])
        self.leaning.translate([0, 60, 0])

    def render(self):
        return [self.stack, self.hanging, self.fitted, self.leaning]


class Stack(AssemblyNode):
    """A base, a block resting flush on it, and a third block seated
    0.3 above -- clearance play well inside the 1.0 default drop."""

    def __init__(self):
        self.base = Block([4, 4, 2])
        self.block = Block([2, 2, 2])
        self.seated = Block([2, 2, 2])
        super().__init__()
        self.block.translate([1, 1, 2])
        self.seated.translate([1, 1, 4.3])

    def render(self):
        return [self.base, self.block, self.seated]


class Hanging(AssemblyNode):
    """A post and a hook that hangs beside it, held only by the lip
    reaching over the post's top face: dropping the hook drives that lip
    into the post."""

    def __init__(self):
        self.post = Block([2, 2, 6])
        self.hook = Hook()
        super().__init__()
        self.post.translate([0, 0, -5])

    def render(self):
        return [self.post, self.hook]


class Fitted(AssemblyNode):
    """A post and a block held on its side by a press fit: the two share
    a face and nothing else, so no drop can prove the hold and the test
    has to declare it."""

    def __init__(self):
        self.post = Block([2, 2, 6])
        self.block = Block([2, 2, 2])
        super().__init__()
        self.post.translate([0, 0, -5])
        self.block.translate([2, 0, -1])

    def render(self):
        return [self.post, self.block]


class Leaning(AssemblyNode):
    """Two interlocking pieces holding each other, with a slab reaching
    under the LEFT one only: the right piece is grounded solely through
    the cycle edge onto its neighbour."""

    def __init__(self):
        self.slab = Block([2, 2, 1.5])
        self.left = LeftHook()
        self.right = RightHook()
        super().__init__()

    def render(self):
        return [self.slab, self.left, self.right]
