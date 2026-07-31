# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import cube
from solid_node.node import Solid2Node


class Lonely(Solid2Node):
    """A leaf that imports no project module.

    It lives in the same package as every other fixture node, so it is
    the witness that resolving an import does not drag the package
    __init__ -- and through it the whole project -- into a node's
    tracked set.
    """

    def render(self):
        return cube(3)
