# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Tiny, non-functional fixture modules for tests/test_loader_node_marker.py.

These classes are never instantiated or rendered -- find_class only
inspects class objects structurally -- so they skip all the CAD
machinery real node fixtures (tests/meta_project/) need. Kept out of
meta_project because they exist purely to unit-test
solid_node.core.loader.find_class, not to be run through `solid test`.
"""
