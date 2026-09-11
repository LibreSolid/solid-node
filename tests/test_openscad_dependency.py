# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import argparse
import io
import os
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

import cadquery as cq
from solid2 import cube
from solid2.core.object_base import OpenSCADConstant

from solid_node.manager.snapshot import Snapshot
from solid_node.node import (Build123dNode, CadQueryNode, FusionNode,
                             JScadNode, Solid2Node)
from solid_node.openscad import OpenScadUnavailable, openscad_binary
from solid_node.viewers import openscad as openscad_viewer
from solid_node.viewers.openscad import OpenScadRenderer


class ExactBox(CadQueryNode):
    def render(self):
        return cq.Workplane('XY').box(2, 2, 2)


class Build123dBox(Build123dNode):
    def render(self):
        import build123d as b3d
        return b3d.Box(2, 2, 2)


class FacetedBox(Solid2Node):
    def render(self):
        return cube(2)


class ExactPair(FusionNode):
    def __init__(self):
        self.left = ExactBox()
        self.right = ExactBox().translate([3, 0, 0])
        super().__init__()

    def render(self):
        return [self.left, self.right]


class MixedExactPair(FusionNode):
    """One solid modelled half in CadQuery and half in build123d. Both
    backends render through the same kernel, so the pair carries no
    OpenSCAD dependency either."""

    def __init__(self):
        self.cadquery_half = ExactBox()
        self.build123d_half = Build123dBox().translate([3, 0, 0])
        super().__init__()

    def render(self):
        return [self.cadquery_half, self.build123d_half]


class FacetedPair(FusionNode):
    def __init__(self):
        self.exact_child = ExactBox()
        self.faceted_child = FacetedBox()
        super().__init__()

    def render(self):
        return [self.exact_child, self.faceted_child]


class OpenScadDependencyTest(TestCase):
    def setUp(self):
        openscad_binary.cache_clear()
        self.directory = tempfile.TemporaryDirectory()
        self.old_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name

    def tearDown(self):
        openscad_binary.cache_clear()
        if self.old_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.old_build_dir
        self.directory.cleanup()

    def test_mesh_leaf_missing_binary_names_node_backend_and_remedy(self):
        node = FacetedBox(name='housing')
        node.assemble()

        with patch('solid_node.openscad.shutil.which', return_value=None), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'the subprocess must not be attempted')):
            with self.assertRaisesRegex(
                    RuntimeError, 'housing.*Solid2Node.*install OpenSCAD'):
                node.generate_stl()

    def test_faceted_fusion_does_not_use_openscad_after_children_are_current(self):
        node = FacetedPair()
        node.build_stls()
        os.remove(node.stl_file)

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'faceted fusion must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'the subprocess must not be attempted')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))

    def test_exact_fusion_never_consults_openscad(self):
        node = ExactPair()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'exact geometry must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'exact geometry must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))
        self.assertTrue(os.path.exists(node.brep_file))

    def test_build123d_leaf_never_consults_openscad(self):
        node = Build123dBox()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'exact geometry must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'exact geometry must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))
        self.assertTrue(os.path.exists(node.brep_file))

    def test_fusion_mixing_exact_backends_never_consults_openscad(self):
        node = MixedExactPair()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'exact geometry must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'exact geometry must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))
        self.assertTrue(os.path.exists(node.brep_file))

    def test_symbolic_value_missing_binary_names_node_and_evaluation(self):
        node = FacetedBox(name='animated-arm')

        with patch('solid_node.openscad.shutil.which', return_value=None), \
             patch('solid_node.node.adapters.solid2.Popen',
                   side_effect=AssertionError('must fail before launch')):
            with self.assertRaisesRegex(
                    RuntimeError, 'animated-arm.*symbolic.*OpenSCAD'):
                node.as_number(OpenSCADConstant('$t'))

    def test_gui_viewer_is_not_an_openscad_dependency_path(self):
        self.assertFalse(hasattr(openscad_viewer, 'OpenScadViewer'))

    def test_renderer_missing_binary_names_web_alternative(self):
        renderer = OpenScadRenderer()
        args = argparse.Namespace(
            camera=None, autocenter=False, viewall=False, imgsize='100x100',
            projection=None, colorscheme=None, preview=False, view=None,
        )
        runner = Mock(side_effect=AssertionError('must fail before launch'))

        with patch.dict(os.environ, {'DISPLAY': ':1'}), \
             patch('solid_node.openscad.shutil.which', return_value=None):
            with self.assertRaisesRegex(
                    RuntimeError,
                    'OpenSCAD snapshot renderer.*--renderer web'):
                renderer.render(Mock(scad_file='part.scad'), args, 'part.png',
                                runner)
        self.assertFalse(os.path.exists('part.png'))

    def test_snapshot_does_not_substitute_the_web_renderer(self):
        snapshot = Snapshot()
        args = argparse.Namespace(
            path='part.py',
            output=os.path.join(self.directory.name, 'part.png'),
            time=0.0, camera=None, autocenter=False, viewall=False,
            imgsize='100x100', projection=None, colorscheme=None, render=False,
            preview=False, view=None, renderer='openscad',
        )
        browser_render = patch(
            'solid_node.viewers.browser.BrowserRenderer.render')
        with patch.object(snapshot, '_load_and_prepare_node',
                          return_value=Mock(scad_file='part.scad')), \
             patch('solid_node.manager.snapshot.OPENSCAD_RENDERER.render',
                   side_effect=OpenScadUnavailable(
                       'the OpenSCAD snapshot renderer',
                       'rendering launches OpenSCAD', 'use --renderer web')), \
             browser_render as web, \
             patch('sys.stderr', new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit):
                snapshot.handle(args)

        web.assert_not_called()
        self.assertIn('--renderer web', stderr.getvalue())
        self.assertFalse(os.path.exists(args.output))


class JScadDependencyBoundaryTest(TestCase):
    def test_current_jscad_artifact_never_launches_openscad(self):
        node = object.__new__(JScadNode)
        node.stl_file = 'current.stl'
        with patch.object(JScadNode, '_up_to_date', return_value=True), \
             patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'current JSCAD artifact must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'JSCAD must not launch OpenSCAD')):
            node.generate_stl()

    def test_jscad_produces_its_artifact_without_checking_openscad(self):
        from tests.source_set_project.jsblock import JsBlock

        with tempfile.TemporaryDirectory() as directory:
            old_build_dir = os.environ.get('SOLID_BUILD_DIR')
            os.environ['SOLID_BUILD_DIR'] = directory
            try:
                def launch_jscad(command):
                    process = Mock(returncode=0)

                    def render_jscad():
                        with open(command[-1], 'wb') as output:
                            output.write(b'solid jscad\nendsolid jscad\n')

                    process.communicate.side_effect = render_jscad
                    return process

                with patch('solid_node.node.adapters.jscad.Popen',
                           side_effect=launch_jscad), \
                     patch('solid_node.node.base.require_openscad',
                           side_effect=AssertionError(
                               'JSCAD must not check OpenSCAD')):
                    node = JsBlock()
                    node.assemble()
                    node.generate_stl()

                self.assertTrue(node._up_to_date(node.stl_file))
            finally:
                if old_build_dir is None:
                    os.environ.pop('SOLID_BUILD_DIR', None)
                else:
                    os.environ['SOLID_BUILD_DIR'] = old_build_dir


class OpenScadAvailabilityTest(TestCase):
    def tearDown(self):
        openscad_binary.cache_clear()

    def test_binary_is_resolved_only_once_per_process(self):
        openscad_binary.cache_clear()
        with patch('solid_node.openscad.shutil.which',
                   return_value='/usr/bin/openscad') as which:
            self.assertEqual(openscad_binary(), '/usr/bin/openscad')
            self.assertEqual(openscad_binary(), '/usr/bin/openscad')

        which.assert_called_once_with('openscad')
