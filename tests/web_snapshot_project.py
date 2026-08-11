# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import cube, translate

from solid_node.node import Solid2Node


class AsymmetricSnapshotPart(Solid2Node):
    """Deliberately lacks rotational or mirror symmetry for camera tests."""

    def render(self):
        return (
            cube([32, 8, 5])
            + translate(20, 4, 5)(cube([6, 19, 17]))
            + translate(3, -8, 2)(cube([9, 8, 9]))
        )
