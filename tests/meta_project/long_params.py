# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cube


class LongParams(Solid2Node):
    """Green fixture (skill-repo improvements.md #13): a leaf whose
    constructor takes a long list-valued parameter. On the OLD
    framework, kwargs serialize verbatim into the artifact filename, so
    a list this long blows the filesystem's 255-byte name limit --
    OSError: File name too long, hit in practice by a wall parametrized
    with per-gear tip circles. RED today for exactly that reason; green
    once the key is hashed."""

    def __init__(self, profile=None):
        self.profile = (
            profile if profile is not None
            else [i * 0.1 for i in range(150)]
        )
        super().__init__(profile=self.profile)

    def render(self):
        return cube(sum(self.profile) % 20 + 1, center=True)
