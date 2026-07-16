# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Sphinx extension (solid_node.sphinx): the
``.. solid-node::`` directive embeds a `solid export` directory in the
built HTML as an <iframe> onto the widget's index.html.

The tests build tiny Sphinx projects in a temp dir against a fake
export directory -- no OpenSCAD or npm artifacts are needed."""

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from sphinx.testing.util import SphinxTestApp
    HAS_SPHINX = True
except ImportError:
    HAS_SPHINX = False


CONF_PY = """
extensions = ['solid_node.sphinx']
"""


@unittest.skipUnless(HAS_SPHINX, 'sphinx not installed')
class SphinxExtBaseTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.srcdir = os.path.join(self.root, 'source')
        self.builddir = os.path.join(self.root, 'build')
        os.makedirs(self.srcdir)
        with open(os.path.join(self.srcdir, 'conf.py'), 'w') as fh:
            fh.write(CONF_PY)

    def write_doc(self, name, content):
        path = os.path.join(self.srcdir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as fh:
            fh.write(content)

    def make_export(self, relpath, widget=True):
        """A fake `solid export` output directory under srcdir."""
        export_dir = os.path.join(self.srcdir, relpath)
        models = os.path.join(export_dir, 'models')
        os.makedirs(models, exist_ok=True)
        manifest = {
            'format': 'solid-node-export',
            'version': 1,
            'animation': {'fps': 30, 'frames': 360},
            'root': {'name': 'part', 'type': 'SolidNode',
                     'color': None, 'operations': [],
                     'model': 'models/part.stl'},
        }
        with open(os.path.join(export_dir, 'manifest.json'), 'w') as fh:
            json.dump(manifest, fh)
        with open(os.path.join(models, 'part.stl'), 'w') as fh:
            fh.write('solid part\nendsolid part\n')
        if widget:
            with open(os.path.join(export_dir, 'index.html'), 'w') as fh:
                fh.write('<html>widget page</html>')
            with open(os.path.join(export_dir, 'solid-widget.js'),
                      'w') as fh:
                fh.write('// bundle')
        return export_dir

    def build(self):
        """Runs a full HTML build, returning accumulated warnings.
        SphinxTestApp (rather than plain Sphinx) restores docutils'
        global node registrations on cleanup, so several builds can
        run in one test process without cross-talk warnings."""
        warnings = io.StringIO()
        app = SphinxTestApp(
            srcdir=Path(self.srcdir), builddir=Path(self.builddir),
            status=io.StringIO(), warning=warnings,
        )
        try:
            app.build()
        finally:
            app.cleanup()
        self.outdir = str(app.outdir)
        return warnings.getvalue()

    def html(self, name='index.html'):
        with open(os.path.join(self.outdir, name)) as fh:
            return fh.read()


@unittest.skipUnless(HAS_SPHINX, 'sphinx not installed')
class ManifestFormatSyncTest(unittest.TestCase):

    def test_extension_constant_matches_core(self):
        # solid_node.sphinx duplicates the constant so it imports
        # without the CAD stack -- they must never drift apart
        from solid_node import sphinx as ext
        from solid_node.core import export as core
        self.assertEqual(ext.MANIFEST_FORMAT, core.MANIFEST_FORMAT)


class DirectiveTest(SphinxExtBaseTest):

    def test_emits_iframe_and_copies_export(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
        ))

        warnings = self.build()

        self.assertEqual(warnings, '')
        html = self.html()
        self.assertIn('<iframe', html)
        self.assertIn('src="_solid_node/spinner_export/index.html"',
                      html)

        copied = os.path.join(self.outdir, '_solid_node',
                              'spinner_export')
        for name in ('manifest.json', 'index.html', 'solid-widget.js',
                     os.path.join('models', 'part.stl')):
            self.assertTrue(
                os.path.exists(os.path.join(copied, name)),
                f'{name} not copied to output',
            )

    def test_default_height_is_applied(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
        ))

        self.build()

        self.assertIn('height: 480px', self.html())

    def test_height_option(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
            '   :height: 300px\n'
        ))

        self.build()

        self.assertIn('height: 300px', self.html())

    def test_time_and_autoplay_options(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
            '   :t: 0.25\n'
            '   :autoplay: no\n'
        ))

        self.build()

        self.assertIn(
            'src="_solid_node/spinner_export/index.html'
            '?t=0.25&amp;autoplay=0"',
            self.html(),
        )

    def test_document_in_subdirectory_gets_relative_src(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. toctree::\n\n'
            '   sub/page\n'
        ))
        self.write_doc('sub/page.rst', (
            'Page\n====\n\n'
            '.. solid-node:: /spinner_export\n'
        ))

        warnings = self.build()

        self.assertEqual(warnings, '')
        self.assertIn(
            'src="../_solid_node/spinner_export/index.html"',
            self.html(os.path.join('sub', 'page.html')),
        )

    def test_two_directives_share_one_copy(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n\n'
            '.. solid-node:: spinner_export\n'
            '   :t: 0.5\n'
        ))

        warnings = self.build()

        self.assertEqual(warnings, '')
        self.assertEqual(self.html().count('<iframe'), 2)
        exports = os.listdir(os.path.join(self.outdir, '_solid_node'))
        self.assertEqual(exports, ['spinner_export'])


class DirectiveErrorTest(SphinxExtBaseTest):

    def test_missing_export_dir_warns_with_hint(self):
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: not_there\n'
        ))

        warnings = self.build()

        self.assertIn('not_there', warnings)
        self.assertIn('solid export', warnings)

    def test_directory_without_manifest_warns(self):
        os.makedirs(os.path.join(self.srcdir, 'not_an_export'))
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: not_an_export\n'
        ))

        warnings = self.build()

        self.assertIn('manifest.json', warnings)

    def test_invalid_time_option_warns(self):
        self.make_export('spinner_export')
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
            '   :t: 1.5\n'
        ))

        warnings = self.build()

        self.assertIn('t', warnings)


class WidgetlessExportTest(SphinxExtBaseTest):
    """Exports made with --no-widget: the extension completes them
    from the installed package's widget files at build time."""

    def fake_widget(self):
        widget_dir = os.path.join(self.root, 'widget')
        os.makedirs(widget_dir)
        bundle = os.path.join(widget_dir, 'solid-widget.js')
        index = os.path.join(widget_dir, 'index.html')
        with open(bundle, 'w') as fh:
            fh.write('// package bundle')
        with open(index, 'w') as fh:
            fh.write('<html>package page</html>')
        return bundle, index

    def test_completed_from_package(self):
        self.make_export('spinner_export', widget=False)
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
        ))
        bundle, index = self.fake_widget()

        with patch('solid_node.core.export.WIDGET_BUNDLE', bundle), \
             patch('solid_node.core.export.WIDGET_INDEX', index):
            warnings = self.build()

        self.assertEqual(warnings, '')
        copied = os.path.join(self.outdir, '_solid_node',
                              'spinner_export')
        with open(os.path.join(copied, 'solid-widget.js')) as fh:
            self.assertEqual(fh.read(), '// package bundle')
        with open(os.path.join(copied, 'index.html')) as fh:
            self.assertEqual(fh.read(), '<html>package page</html>')

    def test_export_widget_wins_over_package(self):
        self.make_export('spinner_export', widget=True)
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
        ))
        bundle, index = self.fake_widget()

        with patch('solid_node.core.export.WIDGET_BUNDLE', bundle), \
             patch('solid_node.core.export.WIDGET_INDEX', index):
            self.build()

        copied = os.path.join(self.outdir, '_solid_node',
                              'spinner_export')
        with open(os.path.join(copied, 'solid-widget.js')) as fh:
            self.assertEqual(fh.read(), '// bundle')

    def test_no_widget_anywhere_warns_with_npm_hint(self):
        self.make_export('spinner_export', widget=False)
        self.write_doc('index.rst', (
            'Test\n====\n\n'
            '.. solid-node:: spinner_export\n'
        ))
        missing = os.path.join(self.root, 'nowhere', 'solid-widget.js')

        with patch('solid_node.core.export.WIDGET_BUNDLE', missing):
            warnings = self.build()

        self.assertIn('npm', warnings)
