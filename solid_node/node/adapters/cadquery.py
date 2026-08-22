# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
from solid_node.node.exact_leaf import ExactLeafNode


class CheckCQEditor(type):
    """This metaclass will check if we are in the context of
    CQ-editor, if so, use no base classes, otherwise inherit
    ExactLeafNode.

    It drops whatever bases were declared rather than naming one, so it is
    unaffected by what the adapter inherits from.
    """
    def __new__(mcs, name, bases, namespace):
        if sys.modules.get('cq_editor.__main__', None):
            bases = tuple()

        return super().__new__(mcs, name, bases, namespace)


class CadQueryNode(ExactLeafNode, metaclass=CheckCQEditor):
    """
    Represents a 3D object created using the CadQuery tool.

    The exact-adapter contract -- exact, shape(), as_scad() -- is
    ExactLeafNode's; CadQuery adds only its namespace and the CQ-editor
    metaclass.
    """
    namespace = 'cadquery.cq'
