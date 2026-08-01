# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

from solid_node.cli import manage
from solid_node.core.builder import Builder
from solid_node.core.export import export_node, WidgetBundleMissing
from solid_node.node import AssemblyNode
from solid_node.node.base import AbstractBaseNode

from .base import BaseNodeTest
from . import flat_project


class SerializedOperation:
    """The producer contract consumes the raw serialized operation value."""

    def __init__(self, serialized):
        self.serialized = serialized


class Cube(AbstractBaseNode):
    """A real rigid node with a fixture-owned STL, avoiding OpenSCAD.

    The parity fixture deliberately uses a concrete node instead of a mock so
    the producer walks exercise ``AssemblyNode._link_child`` exactly as a
    project does.  Its artifact is already present because the test is about
    document serialization, not STL compilation.
    """

    _type = 'Cube'
    rigid = True

    def __init__(self, build_dir, name=None, color='#123456'):
        self._fixture_build_dir = build_dir
        super().__init__(name=name)
        self.color = color
        self.stl_file = os.path.join(build_dir, 'parts', 'cube.stl')
        os.makedirs(os.path.dirname(self.stl_file), exist_ok=True)
        with open(self.stl_file, 'w') as artifact:
            artifact.write('solid cube\nendsolid cube\n')
        self.operations = [
            SerializedOperation(['t', ['1', '2', '3']]),
        ]

    @property
    def mtime(self):
        return 42


class RecreatedAndReboundAssembly(AssemblyNode):
    """Recreates ``gear`` on every render, exposing producer drift."""

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        super().__init__()
        self.color = '#abcdef'
        self.operations = [
            SerializedOperation(['r', '$t * 360', [0, 0, 1]]),
        ]

    @property
    def mtime(self):
        return 24

    def render(self):
        self.gear = Cube(self._fixture_build_dir)
        return [self.gear]


class ExplicitNameAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        super().__init__()

    def render(self):
        self.gear = Cube(self._fixture_build_dir, name='drive_gear')
        return [self.gear]


class AttributeNameAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        self.input_gear = Cube(build_dir)
        self.output_gear = Cube(build_dir)
        super().__init__()

    def render(self):
        return [self.input_gear, self.output_gear]


class ListAndTupleNameAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        self.gears = [Cube(build_dir), Cube(build_dir)]
        self.posts = (Cube(build_dir), Cube(build_dir))
        super().__init__()

    def render(self):
        return [*self.gears, *self.posts]


class ChildrenOnlyNameAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        super().__init__()

    def render(self):
        child = Cube(self._fixture_build_dir)
        self.children = [child]
        return [child]


class ClassNameFallbackAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        super().__init__()

    def render(self):
        return [Cube(self._fixture_build_dir)]


class NonListNonRigidAssembly(AssemblyNode):

    def __init__(self, build_dir):
        self._fixture_build_dir = build_dir
        super().__init__()

    def render(self):
        return Cube(self._fixture_build_dir)


class ExportBuildSnapshotParityTest(TestCase):
    """Both document producers must serialize the same node tree."""

    def _documents(self, factory=RecreatedAndReboundAssembly):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        export_build = os.path.join(root, 'export-build')
        build_build = os.path.join(root, 'normal-build')
        export_dir = os.path.join(root, 'export')

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': export_build}):
            export_root = factory(export_build)
            with patch.object(export_root, 'build_stls'):
                export_node(export_root, export_dir, widget=False)

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': build_build}):
            build_root = factory(build_build)
            builder = Builder('model.py', build_dir=build_build)
            builder.node = build_root
            builder._write_viewer_snapshot()

        with open(os.path.join(export_dir, 'manifest.json')) as manifest:
            export = json.load(manifest)
        with open(os.path.join(build_build, 'viewer.json')) as snapshot:
            build = json.load(snapshot)
        return export, build, export_dir, build_build

    def test_recreated_rebound_child_names_match(self):
        export, build, _, _ = self._documents()

        self.assertEqual(
            [child['name'] for child in export['root']['children']],
            [child['name'] for child in build['root']['children']],
        )

    def test_common_document_fields_and_distinct_model_roots(self):
        export, build, export_dir, build_dir = self._documents()

        self.assertEqual(export['format'], 'solid-node-export')
        self.assertEqual(build['format'], 'solid-node-export')
        self.assertEqual(export['version'], build['version'])
        self.assertEqual(export['animation'], build['animation'])

        export_root = export['root']
        build_root = build['root']
        self.assertEqual(
            {key: export_root[key] for key in
             ('name', 'type', 'color', 'mtime', 'operations')},
            {key: build_root[key] for key in
             ('name', 'type', 'color', 'mtime', 'operations')},
        )
        export_child = export_root['children'][0]
        build_child = build_root['children'][0]
        self.assertEqual(
            {key: export_child[key] for key in
             ('name', 'type', 'color', 'mtime', 'operations')},
            {key: build_child[key] for key in
             ('name', 'type', 'color', 'mtime', 'operations')},
        )
        self.assertEqual(export_child['model'], 'models/parts/cube.stl')
        self.assertEqual(build_child['model'], 'parts/cube.stl')
        self.assertTrue(os.path.isfile(
            os.path.join(export_dir, export_child['model'])))
        self.assertFalse(os.path.isdir(os.path.join(build_dir, 'models')))
        self.assertEqual(export_root['color'], '#abcdef')
        self.assertEqual(export_root['operations'],
                         [['r', '$t * 360', [0, 0, 1]]])
        self.assertEqual(export_child['color'], '#123456')
        self.assertEqual(export_child['operations'],
                         [['t', ['1', '2', '3']]])

    def test_attribute_linking_boundaries_match(self):
        boundaries = (
            (ExplicitNameAssembly, ['drive_gear']),
            (AttributeNameAssembly, ['input_gear', 'output_gear']),
            (ListAndTupleNameAssembly,
             ['gears-0', 'gears-1', 'posts-0', 'posts-1']),
            (ChildrenOnlyNameAssembly, ['children-0']),
            (ClassNameFallbackAssembly, ['Cube']),
        )
        for factory, expected in boundaries:
            with self.subTest(factory=factory.__name__):
                export, build, _, _ = self._documents(factory)
                self.assertEqual(
                    [child['name'] for child in export['root']['children']],
                    expected,
                )
                self.assertEqual(
                    [child['name'] for child in build['root']['children']],
                    expected,
                )

    def test_rigid_and_non_list_non_rigid_boundaries_match(self):
        export, build, _, _ = self._documents(Cube)
        self.assertEqual(export['root']['model'], 'models/parts/cube.stl')
        self.assertEqual(build['root']['model'], 'parts/cube.stl')
        self.assertNotIn('children', export['root'])
        self.assertNotIn('children', build['root'])

        export, build, _, _ = self._documents(NonListNonRigidAssembly)
        self.assertNotIn('model', export['root'])
        self.assertNotIn('children', export['root'])
        self.assertNotIn('model', build['root'])
        self.assertNotIn('children', build['root'])


class ExportBaseTest(BaseNodeTest):
    """Exports a node into a directory inside the test build dir (so
    tearDown cleans it up) and loads the manifest back.

    widget=False by default: the widget bundle is built by npm/CI, not
    present in a plain python test environment; the widget tests below
    patch in a fake bundle."""

    def export(self, node, widget=False, **kwargs):
        self.out_dir = os.path.join(self.build_dir, 'export_out')
        export_node(node, self.out_dir, widget=widget, **kwargs)
        manifest_path = os.path.join(self.out_dir, 'manifest.json')
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path) as fh:
            self.manifest = json.load(fh)
        return self.manifest

    def assertModelExported(self, node_data):
        """The node's model path must point at a real, non-empty STL
        inside the export directory."""
        model = node_data['model']
        self.assertTrue(model.startswith('models/'))
        path = os.path.join(self.out_dir, model)
        self.assertTrue(os.path.exists(path), f'{path} missing')
        self.assertGreater(os.path.getsize(path), 0)


class ExportRigidLeafTest(ExportBaseTest):
    """A rigid leaf root exports a manifest with a single model and no
    children."""

    def test_manifest_root_is_leaf_with_model(self):
        manifest = self.export(flat_project.SimpleCylinder())
        root = manifest['root']

        self.assertEqual(root['type'], 'LeafNode')
        self.assertEqual(root['name'], 'SimpleCylinder')
        self.assertNotIn('children', root)
        self.assertModelExported(root)

    def test_manifest_has_format_and_animation_defaults(self):
        manifest = self.export(flat_project.SimpleCylinder())

        self.assertEqual(manifest['format'], 'solid-node-export')
        self.assertEqual(manifest['version'], 1)
        self.assertEqual(manifest['animation'], {'fps': 30, 'frames': 360})

    def test_animation_parameters_are_configurable(self):
        manifest = self.export(flat_project.SimpleCylinder(),
                               fps=12, frames=60)

        self.assertEqual(manifest['animation'], {'fps': 12, 'frames': 60})


class ExportAssemblyTest(ExportBaseTest):
    """An assembly exports a tree: the assembly itself has children and
    no model; rigid children carry their own operations and models."""

    def test_two_pipes_tree(self):
        manifest = self.export(flat_project.TwoPipes())
        root = manifest['root']

        self.assertEqual(root['type'], 'AssemblyNode')
        self.assertNotIn('model', root)

        children = root['children']
        self.assertEqual(len(children), 2)
        self.assertEqual([c['name'] for c in children],
                         ['SimplePipe', 'SimplePipe'])

        # The first pipe sits at the origin, the second is translated
        self.assertEqual(children[0]['operations'], [])
        self.assertEqual(children[1]['operations'],
                         [['t', ['100', '0', '0']]])

        for child in children:
            self.assertModelExported(child)

    def test_identical_children_share_one_model_file(self):
        # Both SimplePipe instances have the same parameters, so they
        # resolve to the same STL artifact -- the export must not
        # duplicate it, and both children must reference the same path.
        manifest = self.export(flat_project.TwoPipes())
        children = manifest['root']['children']

        self.assertEqual(children[0]['model'], children[1]['model'])

        models_dir = os.path.join(self.out_dir, 'models')
        stls = [f for _, _, files in os.walk(models_dir)
                for f in files if f.endswith('.stl')]
        self.assertEqual(len(stls), 1)

    def test_nested_assembly_exports_recursively(self):
        # ThirdLevel is assemblies three levels deep: only the
        # SimpleCylinder leaves at the bottom are rigid, so the tree
        # must recurse all the way down and only leaves carry models.
        manifest = self.export(flat_project.ThirdLevel())
        root = manifest['root']

        self.assertEqual(root['type'], 'AssemblyNode')
        self.assertEqual(len(root['children']), 2)
        for child in root['children']:
            self.assertEqual(child['type'], 'AssemblyNode')
            self.assertNotIn('model', child)
            for grandchild in child['children']:
                self.assertEqual(grandchild['type'], 'AssemblyNode')
                for leaf in grandchild['children']:
                    self.assertEqual(leaf['type'], 'LeafNode')
                    self.assertModelExported(leaf)

        # The second instance was rotated by the assembly
        self.assertEqual(root['children'][1]['operations'],
                         [['r', '180', [0, 1, 0]]])


class Spinner(AssemblyNode):
    """An animated assembly: the pipe angle is a $t expression that
    must reach the manifest unevaluated, for the widget to animate."""

    def render(self):
        return [
            flat_project.SimplePipe().rotate(self.time * 360, [0, 0, 1]),
        ]


class ExportAnimationTest(ExportBaseTest):

    def test_time_expression_is_exported_raw(self):
        manifest = self.export(Spinner())
        child = manifest['root']['children'][0]

        (op,) = child['operations']
        self.assertEqual(op[0], 'r')
        self.assertIn('$t', op[1])
        self.assertEqual(op[2], [0, 0, 1])
        self.assertModelExported(child)


class ExportWidgetTest(ExportBaseTest):
    """The export embeds the standalone viewer: the prebuilt JS bundle
    (viewers/widget/dist/solid-widget.js, produced by npm/CI) and the
    static index.html next to the manifest."""

    BUNDLE_CONTENT = '/* fake solid-widget bundle */'

    def setUp(self):
        super().setUp()
        os.makedirs(self.build_dir, exist_ok=True)
        self.fake_bundle = os.path.join(self.build_dir, 'solid-widget.js')
        with open(self.fake_bundle, 'w') as fh:
            fh.write(self.BUNDLE_CONTENT)
        patcher = patch('solid_node.core.export.WIDGET_BUNDLE',
                        self.fake_bundle)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_widget_files_are_copied(self):
        self.export(flat_project.SimpleCylinder(), widget=True)

        bundle = os.path.join(self.out_dir, 'solid-widget.js')
        with open(bundle) as fh:
            self.assertEqual(fh.read(), self.BUNDLE_CONTENT)

        index = os.path.join(self.out_dir, 'index.html')
        with open(index) as fh:
            html = fh.read()
        self.assertIn('solid-widget.js', html)
        self.assertIn('manifest.json', html)

    def test_no_widget_skips_viewer_files(self):
        self.export(flat_project.SimpleCylinder(), widget=False)

        self.assertFalse(
            os.path.exists(os.path.join(self.out_dir, 'index.html')))
        self.assertFalse(
            os.path.exists(os.path.join(self.out_dir, 'solid-widget.js')))

    def test_missing_bundle_raises_with_build_instructions(self):
        os.remove(self.fake_bundle)

        with self.assertRaises(WidgetBundleMissing) as ctx:
            self.export(flat_project.SimpleCylinder(), widget=True)

        self.assertIn('npm', str(ctx.exception))


class ExportCliTest(TestCase):
    """`solid export <path>` is registered and dispatches with defaults."""

    def test_export_dispatches_with_path_and_defaults(self):
        with patch.object(sys, 'argv', ['solid', 'export', 'somefile.py']):
            with patch('solid_node.manager.export.Export.handle') as handle:
                manage()

        self.assertTrue(handle.called)
        args = handle.call_args[0][0]
        self.assertEqual(args.path, 'somefile.py')
        self.assertEqual(args.output, 'export')
        self.assertEqual(args.fps, 30)
        self.assertEqual(args.frames, 360)
        self.assertTrue(args.widget)

    def test_no_widget_flag(self):
        with patch.object(sys, 'argv',
                          ['solid', 'export', 'somefile.py', '--no-widget']):
            with patch('solid_node.manager.export.Export.handle') as handle:
                manage()

        args = handle.call_args[0][0]
        self.assertFalse(args.widget)
