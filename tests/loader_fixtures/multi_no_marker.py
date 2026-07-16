# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node.base import AbstractBaseNode


class Main(AbstractBaseNode):
    """Two node classes, no NODE marker: the loader must refuse to
    silently guess and fail loudly instead."""


class Helper(AbstractBaseNode):
    pass
