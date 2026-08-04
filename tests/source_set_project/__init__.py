# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A project package shaped like a real one.

In the conventional layout the package __init__ IS the root assembly's
source, so it imports every node beneath it. Python executes this file
when resolving any relative import inside the package -- which is
exactly why the source walk must follow only the modules a statement
names and never the package it traverses. Were it to follow this file,
every node here would depend on every other one and a single edit
would invalidate the whole project.
"""

from solid_node.node import AssemblyNode

from .block import Block
from .cyl import Cyl
from .lonely import Lonely


class Assembly(AssemblyNode):

    def render(self):
        return [Cyl(), Lonely()]
