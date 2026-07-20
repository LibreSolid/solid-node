# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import tempfile
import json
from unittest import TestCase
from unittest.mock import patch
from fastapi.testclient import TestClient
from solid_node.viewers.web.viewer import NodeAPI, WebViewer


class FakeRigidNode:
    """Minimal stand-in for a real Node instance, providing only what
    NodeAPI.__init__ touches for a rigid (leaf) node: `name`, `rigid`,
    `operations` and `stl` -- avoids pulling in the real node/build stack.
    """
    rigid = True
    operations = ()

    def __init__(self, name, stl, stl_file=None):
        self.name = name
        self.stl = stl
        self.stl_file = stl_file or f'{name}.stl'


def make_api(node):
    return NodeAPI(node, prefix=f'/{node.name}')


class WaitForFileTest(TestCase):
    """Regression tests for B7: `wait_for_file` returned `None` (bare
    `return`) instead of the file path once the file appeared, so the
    caller `stl()` did `os.path.getmtime(None)` -> TypeError -> HTTP 500,
    exactly when a client requested an STL still being generated.
    """

    def test_returns_the_path_when_file_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'existing.stl')
            with open(path, 'w') as f:
                f.write('solid')

            api = make_api(FakeRigidNode('existing', stl=path))

            result = asyncio.run(api.wait_for_file(path))

            self.assertEqual(result, path)

    def test_returns_the_path_once_file_appears(self):
        # Exercises the polling branch (file not there yet, then created),
        # not just the immediate-hit case above.
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'delayed.stl')
            api = make_api(FakeRigidNode('delayed', stl=None, stl_file=path))

            async def create_after_delay():
                await asyncio.sleep(0.05)
                with open(path, 'w') as f:
                    f.write('solid')

            async def run_both():
                _, result = await asyncio.gather(
                    create_after_delay(),
                    api.wait_for_file(path),
                )
                return result

            result = asyncio.run(run_both())

            self.assertEqual(result, path)


class StlEndpointTest(TestCase):
    """Straightforward TestClient coverage for the common case: the STL
    is already available, so `stl()` never needs to wait at all.
    """

    def test_stl_endpoint_serves_available_file_with_last_modified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'available.stl')
            with open(path, 'w') as f:
                f.write('solid')

            node = FakeRigidNode('available', stl=path)
            api = make_api(node)
            client = TestClient(api.app)

            response = client.get('/available.stl')

            self.assertEqual(response.status_code, 200)
            self.assertIn('last-modified', response.headers)

    def test_snapshot_node_api_serves_without_loading_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'part.stl'), 'w') as stl:
                stl.write('solid part')
            with open(os.path.join(tmpdir, 'viewer.json'), 'w') as snapshot:
                json.dump({'version': 1, 'root': {
                    'name': 'part', 'type': 'SolidNode', 'color': None,
                    'operations': [], 'model': 'part.stl'}}, snapshot)

            api = NodeAPI.from_build(tmpdir)
            client = TestClient(api.app)
            self.assertEqual(client.get('/').json()['name'], 'part')
            self.assertEqual(client.get('/part.stl').status_code, 200)


class WebViewerSurvivesBrokenNodeTest(TestCase):
    """Regression for improvements.md #7: Develop.handle() restarts the
    web viewer on every builder reload cycle ("Restarting WEB"), and
    WebViewer.__init__ calls load_node(path) itself to mount the node
    routes. That call used to be unguarded, so a project broken at the
    exact moment of restart crashed the whole webserver subprocess --
    taking down the reload websocket and the /_build_error endpoint
    with it, exactly when the browser most needed this server to stay
    reachable to show the build error.
    """

    def test_construction_does_not_raise_when_node_fails_to_load(self):
        with patch('solid_node.viewers.web.viewer.load_node',
                   side_effect=NameError('boom')):
            viewer = WebViewer('broken/project.py', dev=True)

        self.assertIsNone(viewer.node)

    def test_build_error_endpoint_still_reachable(self):
        with patch('solid_node.viewers.web.viewer.load_node',
                   side_effect=NameError('boom')):
            viewer = WebViewer('broken/project.py', dev=True)

        client = TestClient(viewer.app)
        response = client.get('/_build_error')

        self.assertEqual(response.status_code, 200)

    def test_reload_websocket_still_connects(self):
        with patch('solid_node.viewers.web.viewer.load_node',
                   side_effect=NameError('boom')):
            viewer = WebViewer('broken/project.py', dev=True)

        client = TestClient(viewer.app)
        with client.websocket_connect('/ws/reload') as websocket:
            self.assertEqual(websocket.receive_text(), 'reload')
