# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""What resolving a node's source closure is allowed to cost.

test_source_set.py pins *what* a node tracks. This file pins the cost
of arriving at it, and the correctness the cheaper route must not
trade away.

The defect these tests were written against: the package-of-a-file
lookup rescanned every entry in sys.modules and called
os.path.realpath on each one's __file__, on every call. On
Metamaquina2 that was 135 lookups x ~1800 modules = 341 169 realpath
calls, 3.46 million lstat syscalls, and 15.3 s of a 22 s load. The
answer it computed depended on neither loop bound.

The cost tests below count os.path.realpath calls rather than seconds:
a call count is deterministic and says the same thing on a fast
machine as on a slow one. The correctness tests are the other half --
an index over a mutable sys.modules can be wrong in ways a linear
rescan never was, so first-wins ordering, a module imported after the
index was built, and a path belonging to no module are each asserted
directly.
"""

import os
import sys
import tempfile
from contextlib import chdir, contextmanager
from types import ModuleType
from unittest import TestCase, mock

from .base import BaseNodeTest
from .source_set_project.block import Block
from .source_set_project.cyl import Cyl
from .source_set_project.jsblock import JsBlock
from .source_set_project.lonely import Lonely
from solid_node.core.loader import import_module_from_path
from solid_node.node import sources
from solid_node.node.sources import source_closure


FIXTURE_CLASSES = (Cyl, Block, Lonely, JsBlock)
CYL = os.path.realpath(sys.modules[Cyl.__module__].__file__)
DIMENSIONS = os.path.realpath(
    os.path.join(os.path.dirname(CYL), 'dimensions.py'))


class RealpathCounter:

    def __init__(self):
        self.calls = 0
        self.enabled = True


@contextmanager
def counting_realpath():
    """Count os.path.realpath calls, with the counter switchable.

    The oracle test needs to charge the lookup under test for its path
    resolution while explicitly *not* charging the reference scan it is
    compared against, so the counter can be turned off around code that
    is measuring rather than measured.
    """
    counter = RealpathCounter()
    original = os.path.realpath

    def counting(path, *args, **kwargs):
        if counter.enabled:
            counter.calls += 1
        return original(path, *args, **kwargs)

    with mock.patch('os.path.realpath', counting):
        yield counter


def linear_package_of(path, resolved):
    """The lookup as it was before the index: first match wins.

    `resolved` memoises realpath per module file. That is faithful to
    the original scan -- realpath is a pure function of the filesystem,
    which does not move during one test -- and it is what makes an
    oracle over every loaded module affordable. The synthetic
    first-wins case below uses the original, unmemoised form, so the
    memo is never the only thing standing behind the answer.
    """
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        real = resolved.get(filename)
        if real is None:
            real = resolved[filename] = os.path.realpath(filename)
        if real == path:
            return getattr(module, '__package__', None) or None
    return None


def unmemoised_linear_package_of(path):
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and os.path.realpath(filename) == path:
            return getattr(module, '__package__', None) or None
    return None


class ResolutionCostTest(BaseNodeTest):
    """The lookup may not scale with the loaded module set."""

    def setUp(self):
        super().setUp()
        self.addCleanup(sources._import_cache.clear)

    def bulk_modules(self, count):
        """Put `count` unrelated modules in sys.modules, as importing a
        larger dependency stack would. Their files need not exist:
        realpath walks the path it is given either way, which is
        exactly the work being counted."""
        names = []
        for index in range(count):
            name = f'solid_node_cost_fixture_{index}'
            module = ModuleType(name)
            module.__file__ = f'/nonexistent/bulk/{index}/pkg/mod{index}.py'
            module.__package__ = f'bulk{index}'
            sys.modules[name] = module
            names.append(name)

        def remove():
            for name in names:
                sys.modules.pop(name, None)

        self.addCleanup(remove)

    def fixture_modules_last(self):
        """Move the fixture's own modules to the end of sys.modules.

        That is where a project's modules really sit: the interpreter
        imports the framework and the CAD stack first and the project
        last. It matters because the scan being replaced stopped at its
        first match, so a file's position decided how much of
        sys.modules a lookup for it walked -- and for a project file,
        which is what source closures are made of, it walked all of it.
        Appending unrelated modules *after* the fixture would measure
        nothing.
        """
        for name, module in list(sys.modules.items()):
            filename = getattr(module, '__file__', None)
            if filename and os.path.realpath(filename) in (CYL, DIMENSIONS):
                del sys.modules[name]
                sys.modules[name] = module

    def closure_realpath_calls(self):
        """Path resolution spent building one node's source closure,
        with the parse cache cleared so the packages really are looked
        up again."""
        sources._import_cache.clear()
        with counting_realpath() as counter:
            source_closure(CYL)
        return counter.calls

    def test_more_loaded_modules_do_not_cost_more_path_resolution(self):
        # The first closure after the module set moves is discarded on
        # both sides. Taking account of a changed sys.modules is allowed
        # to cost something once; what may not grow with the module
        # count is the steady-state cost of every closure after it, and
        # a load computes hundreds of those against one such change.
        self.fixture_modules_last()
        self.closure_realpath_calls()
        small = self.closure_realpath_calls()

        self.bulk_modules(4000)
        self.fixture_modules_last()
        self.closure_realpath_calls()
        grown = self.closure_realpath_calls()

        self.assertLessEqual(
            grown, small,
            f'{len(sys.modules)} loaded modules cost {grown} realpath calls '
            f'against {small} for the same closure with 4000 fewer')

    def test_resolving_project_files_does_not_rescan_the_module_set(self):
        # Construct every fixture node once first: whatever each one
        # imports is then already imported, so sys.modules does not
        # move during the measured block and the count cannot be
        # explained away by the index legitimately rebuilding.
        for NodeClass in FIXTURE_CLASSES:
            NodeClass()

        modules = len(sys.modules)
        sources._import_cache.clear()

        with counting_realpath() as counter:
            for NodeClass in FIXTURE_CLASSES:
                NodeClass()

        self.assertLess(
            counter.calls, modules,
            f'constructing {len(FIXTURE_CLASSES)} nodes spent {counter.calls} '
            f'realpath calls, more than one pass over {modules} modules')


class LookupAgreementTest(TestCase):
    """The cheaper lookup must answer exactly what the scan answered."""

    def test_every_loaded_module_file_resolves_as_a_linear_scan_does(self):
        resolved = {}
        files = []
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                files.append(os.path.realpath(filename))

        self.assertGreater(len(files), 100, 'not a meaningful sample')

        with counting_realpath() as counter:
            for path in files:
                counter.enabled = True
                answer = sources._package_of(path)
                counter.enabled = False
                self.assertEqual(answer, linear_package_of(path, resolved),
                                 f'disagreed for {path}')

        # Same requirement as ResolutionCostTest, stated over the widest
        # possible set of lookups: answering for every loaded module
        # file must not cost a pass per lookup.
        self.assertLess(
            counter.calls, len(sys.modules),
            f'{len(files)} lookups spent {counter.calls} realpath calls')

    def test_two_modules_sharing_a_file_resolve_to_the_first(self):
        """The ordering the scan had for free and an index can lose:
        two module objects, one real path, and the answer is the one
        that appears first in sys.modules -- setdefault, not
        assignment."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.realpath(os.path.join(tmp, 'shared.py'))
            open(path, 'w').close()

            first = ModuleType('solid_node_shared_first')
            first.__file__ = path
            first.__package__ = 'first_package'
            second = ModuleType('solid_node_shared_second')
            second.__file__ = path
            second.__package__ = 'second_package'

            sys.modules[first.__name__] = first
            sys.modules[second.__name__] = second
            try:
                self.assertEqual(sources._package_of(path), 'first_package')
                self.assertEqual(sources._package_of(path),
                                 unmemoised_linear_package_of(path))
            finally:
                del sys.modules[first.__name__]
                del sys.modules[second.__name__]


class StaleIndexTest(TestCase):
    """sys.modules grows while a project loads. A cached view of it
    that misses the growth would answer None for a module that is
    plainly imported, and a node would silently stop tracking a file
    its geometry depends on."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        package = os.path.join(self.root, 'kite')
        os.mkdir(package)
        open(os.path.join(package, '__init__.py'), 'w').close()
        with open(os.path.join(package, 'spars.py'), 'w') as stream:
            stream.write('SPAN = 1.2\n')
        # sail.py deliberately does not import spars: the point is a
        # module that enters sys.modules *after* the lookup has already
        # been used once.
        with open(os.path.join(package, 'sail.py'), 'w') as stream:
            stream.write('AREA = 0.8\n')
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\nmodel = "kite.sail:Sail"\n')
        self.sail = os.path.realpath(os.path.join(package, 'sail.py'))
        self.spars = os.path.realpath(os.path.join(package, 'spars.py'))

        def unimport():
            for name in [n for n in sys.modules if n.split('.')[0] == 'kite']:
                del sys.modules[name]
            while self.root in sys.path:
                sys.path.remove(self.root)

        self.addCleanup(unimport)

    def test_a_module_imported_after_a_lookup_still_resolves(self):
        with chdir(self.root):
            import_module_from_path(self.sail, self.root)

            # Not vacuous: nothing has been imported from spars.py at
            # this point, so the second answer below differs from the
            # first for a reason the test itself established.
            self.assertIsNone(sources._package_of(self.spars))
            self.assertEqual(sources._package_of(self.sail), 'kite')

            import_module_from_path(self.spars, self.root)

            self.assertEqual(sources._package_of(self.spars), 'kite')

    def test_a_path_no_module_was_imported_from_resolves_to_none(self):
        self.assertIsNone(sources._package_of('/nonexistent/no/module.py'))
        # A real file, inside a real project, that no module was
        # imported from: the answer is still None and nothing raises.
        never_imported = os.path.realpath(
            os.path.join(self.root, 'kite', 'spars.py'))
        self.assertIsNone(sources._package_of(never_imported))
