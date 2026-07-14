# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from solid2 import cylinder, translate
from .two import TwoCylinders


class TwoCylindersTwice(AssemblyNode):

    def render(self):
        return [
            TwoCylinders(),
            TwoCylinders().rotate(180, [1, 0, 0]),
        ]
