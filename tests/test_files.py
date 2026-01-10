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
import re
import sys
import shutil
from .base import BaseNodeTest, preserve

from .deep_project.one.two.three.simple_cylinder import SimpleCylinder
from .deep_project.one.two.two_cylinders import TwoCylinders
from .deep_project.one.two_cylinders_twice import TwoCylindersTwice
from .deep_project.third_level import ThirdLevel

class FilesTest(BaseNodeTest):

    def setUp(self):
        super().setUp()
        self.zero = SimpleCylinder()
        self.one = TwoCylinders()
        self.two = TwoCylindersTwice()
        self.three = ThirdLevel()

    def test_level_zero(self):
        self.zero.assemble()
        self.assertTrue(self.zero.src in self.zero.files)

    def test_level_one(self):
        self.one.assemble()
        self.assertTrue(self.zero.src in self.one.files)
        self.assertTrue(self.one.src in self.one.files)

    def test_level_two(self):
        self.two.assemble()
        self.assertTrue(self.zero.src in self.two.files)
        self.assertTrue(self.one.src in self.two.files)
        self.assertTrue(self.two.src in self.two.files)

    def test_level_three(self):
        self.three.assemble()
        self.assertTrue(self.zero.src in self.three.files)
        self.assertTrue(self.one.src in self.three.files)
        self.assertTrue(self.two.src in self.three.files)
        self.assertTrue(self.three.src in self.three.files)
