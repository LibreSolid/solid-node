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

import re
import os
import shutil
from unittest import TestCase
from solid_node.node import StlRenderStart
from .utils import format_codes


BASEDIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASEDIR, '_build')

os.environ['SOLID_BUILD_DIR'] = BUILD_DIR

class BaseNodeTest(TestCase):

    def setUp(self):
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
        self.basedir = BASEDIR
        self.build_dir = BUILD_DIR
        self.preserve_result = None

    def tearDown(self):
        if not os.path.exists(BUILD_DIR):
            return
        if not self.preserve_result:
            shutil.rmtree(BUILD_DIR)
            return
        dirs = BUILD_DIR.split('/')
        dirs[-1] = f'_build_{self.preserve_result}'
        new_dir = '/'.join(dirs)
        if os.path.exists(new_dir):
            shutil.rmtree(new_dir)
        os.rename(BUILD_DIR, new_dir)

    def get_scad(self, NodeClass, *args, **kwargs):
        solid = NodeClass(*args, **kwargs)
        solid.assemble()
        return solid.scad_code.strip()

    def load_solid(self, index, stl_level=0):
        self.solid = self.models[index]()
        self.solid.assemble()

        if not stl_level:
            return self.solid

        for _ in range(stl_level):
            try:
                self.solid.trigger_stl()
            except StlRenderStart as job:
                job.wait()

        self.solid._assembled = False
        self.solid.assemble()

        return self.solid

    def assertCode(self, code):
        scad_code, code = format_codes(self.solid.scad_code, code)

        expected = re.sub(r'\s+', ' ', code.strip())
        generated = re.sub(r'\s+', ' ', scad_code.strip())

        if expected == generated:
            return

        print('EXPECTED:')
        print(code.strip())
        print('GOT:')
        print(scad_code.strip())

        # Compare the full token sequences (not just as far as the
        # shorter one reaches): a strict-prefix generated used to pass
        # silently here, and a shorter expected used to raise a raw
        # IndexError instead of a clean assertion failure.
        self.assertEqual(generated.split(), expected.split())



def preserve(test):
    def new_test(self, *args):
        self.preserve_result = test.__qualname__
        test(self, *args)

    return new_test
