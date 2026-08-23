# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Numbers the wrapper modules correct their meshes by.

Imported by `parts.py`, so it must reach a node's tracked file set
transitively: a constant an `adjust` hook scales by decides the
artifact's geometry every bit as much as the mesh file does.
"""

#: A mesh exported in inches, brought to the framework's millimeters.
MILLIMETRES_PER_INCH = 25.4
