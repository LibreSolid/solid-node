# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A project whose parts come from committed STL meshes.

Shaped like a real project: wrapper modules declare the parts, an
assembly places them, and a fusion machines one of them to fit. The
`.stl` files themselves are not committed -- `tests/test_stl_node.py`
generates them from CadQuery parts before it runs, so the round trip
(authored part -> mesh file -> imported part) is the fixture (design
D7 of the `stl-node` change).
"""

from .rack import Rack
