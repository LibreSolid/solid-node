# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import shutil
import argparse
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock

from solid_node.manager.snapshot import Snapshot, COLORSCHEMES, VIEW_OPTIONS


BASEDIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASEDIR, '_build')

os.environ['SOLID_BUILD_DIR'] = BUILD_DIR


class SnapshotImgsizeValidationTest(TestCase):
    """Test _validate_imgsize method for various formats"""

    def setUp(self):
        self.snapshot = Snapshot()

    def test_valid_imgsize_1920x1080(self):
        self.assertTrue(self.snapshot._validate_imgsize('1920x1080'))

    def test_valid_imgsize_800x600(self):
        self.assertTrue(self.snapshot._validate_imgsize('800x600'))

    def test_valid_imgsize_3840x2160(self):
        self.assertTrue(self.snapshot._validate_imgsize('3840x2160'))

    def test_valid_imgsize_uppercase_X(self):
        self.assertTrue(self.snapshot._validate_imgsize('1920X1080'))

    def test_invalid_imgsize_no_separator(self):
        self.assertFalse(self.snapshot._validate_imgsize('1920'))

    def test_invalid_imgsize_wrong_separator(self):
        self.assertFalse(self.snapshot._validate_imgsize('1920:1080'))

    def test_invalid_imgsize_text(self):
        self.assertFalse(self.snapshot._validate_imgsize('invalid'))

    def test_invalid_imgsize_zero_width(self):
        self.assertFalse(self.snapshot._validate_imgsize('0x1080'))

    def test_invalid_imgsize_zero_height(self):
        self.assertFalse(self.snapshot._validate_imgsize('1920x0'))

    def test_invalid_imgsize_negative(self):
        self.assertFalse(self.snapshot._validate_imgsize('-100x100'))

    def test_invalid_imgsize_float(self):
        self.assertFalse(self.snapshot._validate_imgsize('100.5x200'))

    def test_invalid_imgsize_empty(self):
        self.assertFalse(self.snapshot._validate_imgsize(''))

    def test_invalid_imgsize_three_parts(self):
        self.assertFalse(self.snapshot._validate_imgsize('100x200x300'))


class SnapshotTimeValidationTest(TestCase):
    """Test --time parameter validation in handle()"""

    def setUp(self):
        self.snapshot = Snapshot()
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def tearDown(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def _make_args(self, time_value):
        """Create mock args with specified time value"""
        args = argparse.Namespace(
            path='dummy/path',
            output='snapshot.png',
            time=time_value,
            camera=None,
            autocenter=False,
            viewall=False,
            imgsize='1920x1080',
            projection='perspective',
            colorscheme='Cornfield',
            render=True,
            preview=False,
            view=None,
        )
        return args

    def test_time_valid_zero(self):
        """Time value 0.0 should be valid"""
        args = self._make_args(0.0)
        # Should not raise or exit for valid time
        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node
            with patch('solid_node.manager.snapshot.run'):
                self.snapshot.handle(args)

    def test_time_valid_one(self):
        """Time value 1.0 should be valid"""
        args = self._make_args(1.0)
        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node
            with patch('solid_node.manager.snapshot.run'):
                self.snapshot.handle(args)

    def test_time_valid_half(self):
        """Time value 0.5 should be valid"""
        args = self._make_args(0.5)
        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node
            with patch('solid_node.manager.snapshot.run'):
                self.snapshot.handle(args)

    def test_time_invalid_negative(self):
        """Negative time value should cause exit"""
        args = self._make_args(-0.1)
        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)
        self.assertEqual(cm.exception.code, 1)

    def test_time_invalid_above_one(self):
        """Time value > 1.0 should cause exit"""
        args = self._make_args(1.5)
        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)
        self.assertEqual(cm.exception.code, 1)

    def test_time_invalid_two(self):
        """Time value 2.0 should cause exit"""
        args = self._make_args(2.0)
        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)
        self.assertEqual(cm.exception.code, 1)


class SnapshotViewValidationTest(TestCase):
    """Test --view parameter validation"""

    def setUp(self):
        self.snapshot = Snapshot()

    def _make_args(self, view_value):
        """Create mock args with specified view value"""
        args = argparse.Namespace(
            path='dummy/path',
            output='snapshot.png',
            time=0.0,
            camera=None,
            autocenter=False,
            viewall=False,
            imgsize='1920x1080',
            projection='perspective',
            colorscheme='Cornfield',
            render=True,
            preview=False,
            view=view_value,
        )
        return args

    def test_view_valid_axes(self):
        """Valid view option 'axes'"""
        args = self._make_args('axes')
        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node
            with patch('solid_node.manager.snapshot.run'):
                self.snapshot.handle(args)

    def test_view_valid_multiple(self):
        """Valid multiple view options"""
        args = self._make_args('axes,edges,wireframe')
        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node
            with patch('solid_node.manager.snapshot.run'):
                self.snapshot.handle(args)

    def test_view_invalid_option(self):
        """Invalid view option should cause exit"""
        args = self._make_args('invalid_option')
        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)
        self.assertEqual(cm.exception.code, 1)

    def test_view_invalid_mixed(self):
        """Mix of valid and invalid options should cause exit"""
        args = self._make_args('axes,invalid')
        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)
        self.assertEqual(cm.exception.code, 1)


class SnapshotCommandBuildingTest(TestCase):
    """Test _build_openscad_command method"""

    def setUp(self):
        self.snapshot = Snapshot()
        self.snapshot.output = 'test_output.png'
        self.mock_node = Mock()
        self.mock_node.scad_file = '/tmp/test_node.scad'

    def _make_args(self, **kwargs):
        """Create args with defaults that can be overridden"""
        defaults = {
            'camera': None,
            'autocenter': False,
            'viewall': False,
            'imgsize': '1920x1080',
            'projection': 'perspective',
            'colorscheme': 'Cornfield',
            'preview': False,
            'view': None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_default_command(self):
        """Test default command generation"""
        args = self._make_args()
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertEqual(cmd[0], 'openscad')
        self.assertIn('-o', cmd)
        self.assertIn('test_output.png', cmd)
        self.assertIn('--imgsize', cmd)
        self.assertIn('1920,1080', cmd)
        self.assertIn('--projection', cmd)
        self.assertIn('p', cmd)
        self.assertIn('--colorscheme', cmd)
        self.assertIn('Cornfield', cmd)
        self.assertEqual(cmd[-1], '/tmp/test_node.scad')

    def test_projection_ortho(self):
        """Test ortho projection mapping"""
        args = self._make_args(projection='ortho')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        idx = cmd.index('--projection')
        self.assertEqual(cmd[idx + 1], 'o')

    def test_projection_perspective(self):
        """Test perspective projection mapping"""
        args = self._make_args(projection='perspective')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        idx = cmd.index('--projection')
        self.assertEqual(cmd[idx + 1], 'p')

    def test_camera_passthrough(self):
        """Test camera specification is passed through"""
        args = self._make_args(camera='0,0,100,0,0,0,500')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('--camera', cmd)
        self.assertIn('0,0,100,0,0,0,500', cmd)

    def test_autocenter_flag(self):
        """Test autocenter flag is added"""
        args = self._make_args(autocenter=True)
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('--autocenter', cmd)

    def test_viewall_flag(self):
        """Test viewall flag is added"""
        args = self._make_args(viewall=True)
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('--viewall', cmd)

    def test_preview_flag(self):
        """Test preview flag is added"""
        args = self._make_args(preview=True)
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('--preview', cmd)

    def test_view_options(self):
        """Test view options are passed through"""
        args = self._make_args(view='axes,edges')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('--view', cmd)
        self.assertIn('axes,edges', cmd)

    def test_colorscheme_metallic(self):
        """Test different colorscheme"""
        args = self._make_args(colorscheme='Metallic')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('Metallic', cmd)

    def test_imgsize_conversion(self):
        """Test imgsize WxH is converted to W,H"""
        args = self._make_args(imgsize='800x600')
        cmd = self.snapshot._build_openscad_command(self.mock_node, args)

        self.assertIn('800,600', cmd)
        self.assertNotIn('800x600', cmd)


class SnapshotNodePreparationTest(TestCase):
    """Test _load_and_prepare_node method"""

    def setUp(self):
        self.snapshot = Snapshot()
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def tearDown(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def test_load_node_is_called(self):
        """Test that load_node is called with correct path"""
        self.snapshot.path = '/test/path/node.py'
        self.snapshot.time = 0.5

        with patch('solid_node.manager.snapshot.load_node') as mock_load:
            mock_node = Mock()
            mock_load.return_value = mock_node

            self.snapshot._load_and_prepare_node()

            mock_load.assert_called_once_with('/test/path/node.py')

    def test_set_keyframe_is_called(self):
        """Test that set_keyframe is called with correct time"""
        self.snapshot.path = '/test/path/node.py'
        self.snapshot.time = 0.75

        with patch('solid_node.manager.snapshot.load_node') as mock_load:
            mock_node = Mock()
            mock_load.return_value = mock_node

            self.snapshot._load_and_prepare_node()

            mock_node.set_keyframe.assert_called_once_with(0.75)

    def test_assemble_is_called(self):
        """Test that assemble is called on the node"""
        self.snapshot.path = '/test/path/node.py'
        self.snapshot.time = 0.0

        with patch('solid_node.manager.snapshot.load_node') as mock_load:
            mock_node = Mock()
            mock_load.return_value = mock_node

            self.snapshot._load_and_prepare_node()

            mock_node.assemble.assert_called_once()


class SnapshotErrorHandlingTest(TestCase):
    """Test error handling scenarios"""

    def setUp(self):
        self.snapshot = Snapshot()
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def tearDown(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def _make_args(self, **kwargs):
        defaults = {
            'path': 'dummy/path',
            'output': 'snapshot.png',
            'time': 0.0,
            'camera': None,
            'autocenter': False,
            'viewall': False,
            'imgsize': '1920x1080',
            'projection': 'perspective',
            'colorscheme': 'Cornfield',
            'render': True,
            'preview': False,
            'view': None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_node_load_failure(self):
        """Test handling of node load failure"""
        args = self._make_args()

        with patch('solid_node.manager.snapshot.load_node') as mock_load:
            mock_load.side_effect = Exception("Failed to load node")

            with self.assertRaises(SystemExit) as cm:
                self.snapshot.handle(args)

            self.assertEqual(cm.exception.code, 1)

    def test_openscad_not_found(self):
        """Test handling when OpenSCAD is not found"""
        args = self._make_args()

        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node

            with patch('solid_node.manager.snapshot.run') as mock_run:
                mock_run.side_effect = FileNotFoundError()

                with self.assertRaises(SystemExit) as cm:
                    self.snapshot.handle(args)

                self.assertEqual(cm.exception.code, 1)

    def test_openscad_render_failure(self):
        """Test handling of OpenSCAD render failure"""
        from subprocess import CalledProcessError

        args = self._make_args()

        with patch.object(self.snapshot, '_load_and_prepare_node') as mock_load:
            mock_node = Mock()
            mock_node.scad_file = '/tmp/test.scad'
            mock_load.return_value = mock_node

            with patch('solid_node.manager.snapshot.run') as mock_run:
                error = CalledProcessError(1, 'openscad')
                error.stderr = "Render failed"
                mock_run.side_effect = error

                with self.assertRaises(SystemExit) as cm:
                    self.snapshot.handle(args)

                self.assertEqual(cm.exception.code, 1)

    def test_invalid_imgsize_exits(self):
        """Test that invalid imgsize causes exit"""
        args = self._make_args(imgsize='invalid')

        with self.assertRaises(SystemExit) as cm:
            self.snapshot.handle(args)

        self.assertEqual(cm.exception.code, 1)


class SnapshotArgumentParsingTest(TestCase):
    """Test add_arguments method"""

    def setUp(self):
        self.snapshot = Snapshot()
        self.parser = argparse.ArgumentParser()
        self.snapshot.add_arguments(self.parser)

    def test_default_output(self):
        """Test default output filename"""
        args = self.parser.parse_args([])
        self.assertEqual(args.output, 'snapshot.png')

    def test_custom_output(self):
        """Test custom output filename"""
        args = self.parser.parse_args(['-o', 'custom.png'])
        self.assertEqual(args.output, 'custom.png')

    def test_default_time(self):
        """Test default time value"""
        args = self.parser.parse_args([])
        self.assertEqual(args.time, 0.0)

    def test_custom_time(self):
        """Test custom time value"""
        args = self.parser.parse_args(['--time', '0.5'])
        self.assertEqual(args.time, 0.5)

    def test_default_imgsize(self):
        """Test default image size"""
        args = self.parser.parse_args([])
        self.assertEqual(args.imgsize, '1920x1080')

    def test_custom_imgsize(self):
        """Test custom image size"""
        args = self.parser.parse_args(['--imgsize', '800x600'])
        self.assertEqual(args.imgsize, '800x600')

    def test_default_projection(self):
        """Test default projection mode"""
        args = self.parser.parse_args([])
        self.assertEqual(args.projection, 'perspective')

    def test_ortho_projection(self):
        """Test ortho projection"""
        args = self.parser.parse_args(['--projection', 'ortho'])
        self.assertEqual(args.projection, 'ortho')

    def test_default_colorscheme(self):
        """Test default colorscheme"""
        args = self.parser.parse_args([])
        self.assertEqual(args.colorscheme, 'Cornfield')

    def test_custom_colorscheme(self):
        """Test custom colorscheme"""
        args = self.parser.parse_args(['--colorscheme', 'Metallic'])
        self.assertEqual(args.colorscheme, 'Metallic')

    def test_preview_flag(self):
        """Test preview flag"""
        args = self.parser.parse_args(['--preview'])
        self.assertTrue(args.preview)

    def test_default_render_is_false(self):
        """--render should default to False so --preview isn't a permanent no-op"""
        args = self.parser.parse_args([])
        self.assertFalse(args.render)

    def test_render_and_preview_are_mutually_exclusive(self):
        """Passing both --render and --preview should be rejected by argparse"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--render', '--preview'])

    def test_autocenter_flag(self):
        """Test autocenter flag"""
        args = self.parser.parse_args(['--autocenter'])
        self.assertTrue(args.autocenter)

    def test_viewall_flag(self):
        """Test viewall flag"""
        args = self.parser.parse_args(['--viewall'])
        self.assertTrue(args.viewall)

    def test_camera_option(self):
        """Test camera option"""
        args = self.parser.parse_args(['--camera', '0,0,100,0,0,0,500'])
        self.assertEqual(args.camera, '0,0,100,0,0,0,500')

    def test_view_option(self):
        """Test view option"""
        args = self.parser.parse_args(['--view', 'axes,edges'])
        self.assertEqual(args.view, 'axes,edges')


class SnapshotIntegrationTest(TestCase):
    """Integration tests using real nodes from flat_project"""

    def setUp(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
        os.makedirs(BUILD_DIR, exist_ok=True)
        self.snapshot = Snapshot()

    def tearDown(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    def test_load_and_prepare_simple_cylinder(self):
        """Test loading a real SimpleCylinder node"""
        from tests import flat_project

        node_path = os.path.join(
            BASEDIR, 'flat_project', 'simple_cylinder.py'
        )
        self.snapshot.path = node_path
        self.snapshot.time = 0.0

        node = self.snapshot._load_and_prepare_node()

        self.assertTrue(hasattr(node, 'scad_file'))
        self.assertTrue(os.path.exists(node.scad_file))

    def test_load_and_prepare_assembly_node(self):
        """Test loading a real AssemblyNode (TwoCylinders)"""
        node_path = os.path.join(
            BASEDIR, 'flat_project', 'two_cylinders.py'
        )
        self.snapshot.path = node_path
        self.snapshot.time = 0.0

        node = self.snapshot._load_and_prepare_node()

        self.assertTrue(hasattr(node, 'scad_file'))
        self.assertTrue(os.path.exists(node.scad_file))

    def test_assembly_node_with_time(self):
        """Test that set_keyframe works with AssemblyNode"""
        node_path = os.path.join(
            BASEDIR, 'flat_project', 'two_cylinders.py'
        )
        self.snapshot.path = node_path
        self.snapshot.time = 0.5

        node = self.snapshot._load_and_prepare_node()

        # AssemblyNode should have _time set
        self.assertEqual(node._time, 0.5)

    def test_command_building_with_real_node(self):
        """Test command building with a real node"""
        node_path = os.path.join(
            BASEDIR, 'flat_project', 'simple_cylinder.py'
        )
        self.snapshot.path = node_path
        self.snapshot.time = 0.0
        self.snapshot.output = 'test.png'

        node = self.snapshot._load_and_prepare_node()

        args = argparse.Namespace(
            camera=None,
            autocenter=True,
            viewall=True,
            imgsize='800x600',
            projection='ortho',
            colorscheme='Metallic',
            preview=False,
            view='axes',
        )

        cmd = self.snapshot._build_openscad_command(node, args)

        self.assertEqual(cmd[0], 'openscad')
        self.assertIn('-o', cmd)
        self.assertIn('test.png', cmd)
        self.assertIn('--autocenter', cmd)
        self.assertIn('--viewall', cmd)
        self.assertIn('800,600', cmd)
        self.assertIn('o', cmd)  # ortho projection
        self.assertIn('Metallic', cmd)
        self.assertIn('axes', cmd)
        self.assertTrue(cmd[-1].endswith('.scad'))


class SnapshotConstantsTest(TestCase):
    """Test module constants"""

    def test_colorschemes_list(self):
        """Test COLORSCHEMES contains expected values"""
        self.assertIn('Cornfield', COLORSCHEMES)
        self.assertIn('Metallic', COLORSCHEMES)
        self.assertIn('DeepOcean', COLORSCHEMES)
        self.assertGreater(len(COLORSCHEMES), 5)

    def test_view_options_list(self):
        """Test VIEW_OPTIONS contains expected values"""
        self.assertIn('axes', VIEW_OPTIONS)
        self.assertIn('edges', VIEW_OPTIONS)
        self.assertIn('wireframe', VIEW_OPTIONS)
        self.assertEqual(len(VIEW_OPTIONS), 5)
