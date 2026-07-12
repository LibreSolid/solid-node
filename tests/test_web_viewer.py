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

import asyncio
import os
import tempfile
from unittest import TestCase
from fastapi.testclient import TestClient
from solid_node.viewers.web.viewer import NodeAPI


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
