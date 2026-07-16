# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node.base import AbstractBaseNode
from .elsewhere import Imported


class Main(AbstractBaseNode):
    pass


NODE = Imported
