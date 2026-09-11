# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Opt-in real JSCAD producer integration.

The ordinary suite does not require the external CLI.  When it is on PATH,
this fixture proves the native producer's actual output contract rather than
counting a mocked process as integration evidence.
"""

import shutil
from unittest import skipUnless
from unittest.mock import patch

import trimesh

from .base import BaseNodeTest
from .source_set_project.jsblock import JsBlock


@skipUnless(shutil.which('jscad'), 'jscad CLI is not installed')
class JScadIntegrationTest(BaseNodeTest):

    def test_native_jscad_producer_builds_without_openscad(self):
        node = JsBlock()
        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError('OpenSCAD boundary used')):
            node.build_stls()

        mesh = trimesh.load(node.stl_file, force='mesh')
        self.assertAlmostEqual(mesh.volume, 125.0, places=5)
        self.assertEqual(mesh.bounds.tolist(),
                         [[-2.5, -2.5, -2.5], [2.5, 2.5, 2.5]])
