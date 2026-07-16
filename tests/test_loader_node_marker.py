# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the NODE marker (skill-repo improvements.md #14).

Today the loader returns the FIRST AbstractBaseNode subclass defined
in a file -- an unenforced "main class first" convention that, when
violated, silently loads the WRONG node. These fixtures
(tests/loader_fixtures/) are tiny, never-instantiated classes that
exercise solid_node.core.loader.find_class directly, without the CAD
machinery real node fixtures need.
"""

import os
from unittest import TestCase
from solid_node.core.loader import (
    import_module_from_path, find_class, AmbiguousNodeError,
)
from solid_node.node.base import AbstractBaseNode
from solid_node.test import TestCase as SolidTestCase

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'loader_fixtures')


def load(name):
    path = os.path.realpath(os.path.join(FIXTURES, f'{name}.py'))
    module = import_module_from_path(path)
    return path, module


class SingleClassUnchangedTest(TestCase):
    """A file defining exactly one node class needs no marker: it
    loads unchanged, same as before this feature existed."""

    def test_loads_the_only_class(self):
        path, module = load('single_class')
        klass = find_class(path, module, AbstractBaseNode)
        self.assertEqual(klass.__name__, 'Solo')


class MultiClassNoMarkerTest(TestCase):
    """A file defining SEVERAL node classes with no NODE marker must
    fail loudly -- never silently pick one -- naming the file, the
    candidate classes, and the remedy."""

    def test_raises_actionable_error(self):
        path, module = load('multi_no_marker')
        with self.assertRaises(AmbiguousNodeError) as ctx:
            find_class(path, module, AbstractBaseNode)
        message = str(ctx.exception)
        self.assertIn(path, message)
        self.assertIn('Main', message)
        self.assertIn('Helper', message)
        self.assertIn('NODE = ', message)


class MultiClassWithMarkerTest(TestCase):
    """NODE = MyClass names the node class explicitly; the loader
    must use it instead of guessing."""

    def test_loads_the_marked_class(self):
        path, module = load('multi_with_marker')
        klass = find_class(path, module, AbstractBaseNode)
        self.assertEqual(klass.__name__, 'Main')


class TrapOrderingWithMarkerTest(TestCase):
    """The exact trap from the recent session: a helper class defined
    BEFORE the main class. Old first-defined-wins loading would
    silently return the helper. With NODE naming the main class, the
    right class must load regardless of definition order."""

    def test_loads_main_despite_helper_defined_first(self):
        path, module = load('trap_ordering')
        klass = find_class(path, module, AbstractBaseNode)
        self.assertEqual(klass.__name__, 'Main')


class MarkerWrongTypeTest(TestCase):
    """NODE naming something that isn't an AbstractBaseNode subclass
    at all must fail with a clear error, not a bare AttributeError or
    a silent wrong pick."""

    def test_raises_clear_error(self):
        path, module = load('marker_wrong_type')
        with self.assertRaises(AmbiguousNodeError) as ctx:
            find_class(path, module, AbstractBaseNode)
        message = str(ctx.exception)
        self.assertIn(path, message)
        self.assertIn('NotANode', message)


class MarkerNotDefinedHereTest(TestCase):
    """NODE naming a class that is a real AbstractBaseNode subclass
    but defined in a DIFFERENT file (imported here) must fail with a
    clear error -- the same inspect.getfile check that already
    excludes imported classes from candidacy must reject the marker
    too."""

    def test_raises_clear_error(self):
        path, module = load('marker_not_defined_here')
        with self.assertRaises(AmbiguousNodeError) as ctx:
            find_class(path, module, AbstractBaseNode)
        message = str(ctx.exception)
        self.assertIn(path, message)
        self.assertIn('Imported', message)


class TestCaseResolutionUnaffectedTest(TestCase):
    """The marker rule is for NODE classes only: load_test's
    TestCase resolution (BaseClass=TestCase) keeps its old
    first-defined-wins behavior even for a file defining several
    AbstractBaseNode subclasses and no NODE -- find_class must not
    raise when BaseClass is TestCase."""

    def test_multi_node_file_does_not_raise_for_testcase_lookup(self):
        path, module = load('multi_no_marker')
        # No TestCase subclass is defined in this fixture, so the
        # lookup returns None -- the point is that it does NOT raise
        # AmbiguousNodeError, which is an AbstractBaseNode-only concern.
        klass = find_class(path, module, SolidTestCase)
        self.assertIsNone(klass)
