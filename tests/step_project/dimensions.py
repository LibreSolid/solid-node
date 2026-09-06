# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A number an `adjust` hook corrects a STEP part by.

Imported by `parts.py`, so it must reach a node's tracked file set
transitively: a constant an `adjust` hook scales by decides the
artifact's geometry every bit as much as the STEP document does (as
`stl_project/dimensions.py` does for the STL tests).
"""

#: A vendor part authored at half the scale a project actually wants.
SCALE_FACTOR = 2.0

#: The sewing tolerance an `adjust` hook uses to close a vendor part
#: published as bare faces.
SEWING_TOLERANCE = 0.01
