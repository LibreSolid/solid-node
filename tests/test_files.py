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
