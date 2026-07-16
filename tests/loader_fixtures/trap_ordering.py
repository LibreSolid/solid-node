# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The exact trap that bit a real agent session: a helper class named
so it reads first alphabetically/logically ends up defined BEFORE the
main class in the file. Under the old first-defined-wins loader this
silently loaded the helper instead of the node under test. With a
NODE marker naming the main class explicitly, the right class must
load regardless of definition order."""

from solid_node.node.base import AbstractBaseNode


class Helper(AbstractBaseNode):
    """Defined first -- the trap."""


class Main(AbstractBaseNode):
    """The actual node under test, defined second."""


NODE = Main
