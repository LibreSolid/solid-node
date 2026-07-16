# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node.base import AbstractBaseNode


class Main(AbstractBaseNode):
    pass


class NotANode:
    """Not an AbstractBaseNode subclass -- an invalid NODE target."""


NODE = NotANode
