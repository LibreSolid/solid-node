# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""HTTP coverage for the snapshot-backed development viewer."""

import json
import os
import shutil
import socket
import tempfile
import threading
from pathlib import Path
from subprocess import run
from unittest import TestCase, skipUnless
from unittest.mock import patch

from fastapi.testclient import TestClient
import uvicorn

from solid_node.core.export import export_node
from solid_node.viewers.bundle import bundle_path
from solid_node.viewers.web.viewer import WebViewer

from . import spinner_project
from .test_widget_e2e import CHROME, HAS_PIL

if HAS_PIL:
    from PIL import Image


class WebViewerSnapshotTest(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.build_dir = Path(self.tempdir.name) / 'published-build'
        self.build_dir.mkdir()
        (self.build_dir / 'models').mkdir()
        (self.build_dir / 'models' / 'part.stl').write_text('solid part')
        (self.build_dir / 'viewer.json').write_text(json.dumps({
            'format': 'solid-node-viewer',
            'version': 1,
            'animation': {'fps': 30, 'frames': 360},
            'root': {'name': 'part', 'model': 'models/part.stl'},
        }))
        self.env = patch.dict(os.environ, {
            'SOLID_BUILD_DIR': str(self.build_dir),
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def viewer(self):
        return WebViewer('project-that-must-not-be-imported.py', dev=True)

    def test_serves_the_published_snapshot_and_models(self):
        client = TestClient(self.viewer().app)

        snapshot = client.get('/build/viewer.json')
        model = client.get('/build/models/part.stl')

        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json()['root']['model'], 'models/part.stl')
        self.assertEqual(model.status_code, 200)
        self.assertEqual(model.text, 'solid part')

    def test_reports_an_absent_snapshot_without_failing_the_server(self):
        (self.build_dir / 'viewer.json').unlink()

        client = TestClient(self.viewer().app)

        self.assertEqual(client.get('/build/viewer.json').status_code, 404)
        self.assertEqual(client.get('/_build_error').status_code, 200)

    def test_serving_a_snapshot_never_imports_project_source(self):
        with patch('solid_node.core.loader.load_node',
                   side_effect=AssertionError('project source was imported')) as load_node:
            client = TestClient(self.viewer().app)
            response = client.get('/build/viewer.json')

        self.assertEqual(response.status_code, 200)
        load_node.assert_not_called()


class WebViewerBundleTest(TestCase):
    def test_reports_available_bundle_and_api_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / 'solid-widget.js'
            bundle.write_text('window.SolidNodeWidget = {};')
            with patch('solid_node.viewers.web.viewer.bundle_path', return_value=bundle), \
                 patch('solid_node.viewers.web.viewer.has_bundle', return_value=True), \
                 patch('solid_node.viewers.web.viewer.api_version', return_value=1):
                client = TestClient(WebViewer('ignored.py', dev=True).app)
                status = client.get('/_viewer')
                script = client.get('/_viewer/bundle.js')

        self.assertEqual(status.json(), {
            'available': True, 'apiVersion': 1, 'remedy': None,
        })
        self.assertEqual(script.status_code, 200)
        self.assertIn('SolidNodeWidget', script.text)

    def test_reports_the_remedy_when_the_bundle_is_missing(self):
        with patch('solid_node.viewers.web.viewer.has_bundle', return_value=False), \
             patch('solid_node.viewers.web.viewer.api_version', return_value=1), \
             patch('solid_node.viewers.web.viewer.missing_bundle_remedy',
                   return_value='run npm run build'):
            client = TestClient(WebViewer('ignored.py', dev=True).app)
            status = client.get('/_viewer')
            script = client.get('/_viewer/bundle.js')

        self.assertEqual(status.json(), {
            'available': False, 'apiVersion': 1, 'remedy': 'run npm run build',
        })
        self.assertEqual(script.status_code, 503)
        self.assertEqual(script.json()['remedy'], 'run npm run build')


@skipUnless(os.path.exists(bundle_path()), 'widget bundle not built (npm run build)')
@skipUnless(CHROME, 'no headless chromium available')
@skipUnless(HAS_PIL, 'Pillow not installed')
class DevelopmentViewerBrowserTest(TestCase):
    """The development shell must render through the shared bundle."""
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.build_dir = Path(self.tempdir.name) / '_build'
        export_dir = Path(self.tempdir.name) / 'export'
        export_node(spinner_project.Spinner(), export_dir)
        shutil.copytree(export_dir, self.build_dir)
        (self.build_dir / 'manifest.json').rename(self.build_dir / 'viewer.json')

        self.env = patch.dict(os.environ, {
            'SOLID_BUILD_DIR': str(self.build_dir),
        })
        self.env.start()
        self.addCleanup(self.env.stop)

        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            port = reserved.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(
            WebViewer('fixture.py', dev=False).app,
            host='127.0.0.1', port=port, log_level='error',
        ))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = f'http://127.0.0.1:{port}/'
        for _ in range(50):
            if self.server.started:
                break
            threading.Event().wait(0.1)
        self.assertTrue(self.server.started, 'development viewer did not start')

    def stop_server(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)

    def test_built_spinner_renders_with_declared_colour(self):
        image_path = Path(self.tempdir.name) / 'development-viewer.png'
        result = run([
            CHROME, '--headless', '--no-sandbox', '--disable-gpu',
            '--use-angle=swiftshader', '--window-size=800,600',
            '--virtual-time-budget=4000', f'--screenshot={image_path}', self.url,
        ], capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr.decode()[-500:])

        image = Image.open(image_path).convert('RGB')
        red = sum(1 for r, g, b in image.getdata()
                  if r > 100 and r > 1.4 * g and r > 1.4 * b)
        blue = sum(1 for r, g, b in image.getdata()
                   if b > 100 and b > 1.4 * r and b > 1.4 * g)
        self.assertGreater(red, 500, 'red hub not visible')
        self.assertGreater(blue, 2000, 'blue blades not visible')
