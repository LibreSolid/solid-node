# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The test framework is imported by the paths that run tests.

Deferring `solid_node.node`'s backend exports was not enough: a real
`solid build` of a `Solid2Node`-only project still imported `cadquery`,
through two chains that never touch the node package's exports at all.

- `core/loader.py` imported `TestCase` at module scope, and
  `solid_node/test.py` imports `solid_node.exact`. Every node-scoped
  command goes through the loader, so this is the chain that matters
  most: it is the shop floor's hot path, where `solid build` runs on
  every project open.
- `core/serializer.py` imports `solid_node.simulation.enumeration` on
  every publication, and importing that submodule ran
  `simulation/__init__.py`, whose `.scenario` re-export imports
  `solid_node.test` and lands in the same place.

Neither deferral makes the test framework optional -- it is a required
part of the framework and stays one. What is asserted here is WHEN it
loads: not when a node is loaded or a document is published, and still
exactly as before the moment a test is discovered or run. So each
absence assertion is paired with the presence assertion that would
catch a deferral that had quietly become a removal.

Import cost is only observable in a process that has not already
imported the framework, so these run through `tests/import_probe.py`.
The headline case runs the real CLI: `solid build` of a `Solid2Node`-only
fixture must import no `cadquery`, and `solid build` of a CadQuery
fixture must still import it -- the second half is what proves the first
is discrimination rather than an accident.
"""

import importlib
import os
import tempfile
from unittest import TestCase

from .import_probe import probe

import solid_node.simulation


BASEDIR = os.path.dirname(os.path.abspath(__file__))

# The names `solid_node/simulation/__init__.py` exported eagerly before
# this change, each with the submodule that defines it. Written out here
# rather than read from the package under test: a table that agreed with
# itself would prove nothing about what consumers used to import.
EXPECTED_EXPORTS = {
    'Driver': 'solid_node.simulation.driver',
    'RampProgram': 'solid_node.simulation.driver',
    'qualified_drivers': 'solid_node.simulation.enumeration',
    'qualified_instructions': 'solid_node.simulation.enumeration',
    'Instruction': 'solid_node.simulation.instruction',
    'ScenarioTest': 'solid_node.simulation.scenario',
    'Sim': 'solid_node.simulation.sim',
    # The running mode's error kinds, added with the running time base
    # (OpenSpec change ``run-owns-the-coordinates``), and the entry its
    # crossing record is made of, added with ``integrate-jumps``. Lazy
    # like the rest, and for one more reason: naming any of them imports
    # the running engine, which a model declaring no running time never
    # pays for.
    'RunConflict': 'solid_node.simulation.run',
    'UnsupportedLaw': 'solid_node.simulation.program',
    'TooManyCrossings': 'solid_node.simulation.program',
    'Crossing': 'solid_node.simulation.program',
}

# Refuse `cadquery` the way an interpreter without the wheel does: a
# `sys.meta_path` finder that raises, rather than a stub, so a deferred
# import fails for the real reason a broken install fails.
CADQUERY_ABSENT = '''
import sys


class _CadQueryAbsent:

    def find_spec(self, name, target=None, path=None):
        if name == 'cadquery' or name.startswith('cadquery.'):
            raise ModuleNotFoundError(
                "No module named 'cadquery'", name='cadquery')
        return None


sys.meta_path.insert(0, _CadQueryAbsent())
sys.modules.pop('cadquery', None)
'''


def ran(snippet, **kwargs):
    """Probe `snippet`, insisting it reached the end.

    The probe reports whichever modules were loaded before the child
    died, so a snippet that raised would satisfy "cadquery is absent"
    for entirely the wrong reason.
    """
    return probe(snippet, **kwargs).check()


def build(reference):
    """Run a real `solid build` of a fixture, in a throwaway build tree.

    `SOLID_BUILD_DIR` is absolute and outside the repository, so the
    fixture projects under `tests/` are never written into -- and the
    build lock, which is derived from that directory, goes with it.
    """
    with tempfile.TemporaryDirectory(prefix='solid-lazy-build-') as build_dir:
        return ran('from solid_node.cli import manage\nmanage()\n',
                   argv=['build', reference],
                   env={'SOLID_BUILD_DIR': build_dir},
                   cwd=BASEDIR)


# `solid build` forks a `Builder` per generation, so the parent the probe
# watches never runs the publication itself -- and a forked child inherits
# `sys.modules` rather than reporting its own. Driving the same builder
# loop in one process is what makes the imports of an actual serialization
# observable; it runs exactly the code `Build.handle` runs, minus the fork.
PUBLISH = '''
import os

from solid_node.core.builder import Builder, BuildOutcome

while True:
    try:
        Builder(os.environ['SOLID_PROBE_NODE'], watch=False,
                lifecycle=True).start()
        outcome = 0
    except SystemExit as stop:
        outcome = stop.code
    if outcome not in (BuildOutcome.RENDERED.value,
                       BuildOutcome.SOURCE_CHANGED.value):
        break
assert outcome == BuildOutcome.CURRENT.value, outcome
document = os.path.join(os.environ['SOLID_BUILD_DIR'], 'viewer.json')
print('PUBLISHED', os.path.isfile(document))
'''


def publish(reference):
    """Build and serialize a fixture's viewer document, in this process."""
    with tempfile.TemporaryDirectory(prefix='solid-lazy-build-') as build_dir:
        return ran(PUBLISH,
                   env={'SOLID_BUILD_DIR': build_dir,
                        'SOLID_PROBE_NODE': reference},
                   cwd=BASEDIR)


class LoaderImportCost(TestCase):
    """Loading a node is not a reason to load the test framework."""

    def test_importing_the_loader_does_not_import_the_test_framework(self):
        result = ran('import solid_node.core.loader\n')
        self.assertFalse(
            result.imported('solid_node.test'),
            'importing solid_node.core.loader imported solid_node.test')

    def test_importing_the_loader_does_not_import_cadquery(self):
        # The consequence that pays for the change: solid_node.test
        # imports solid_node.exact, which is 1.84 s of cadquery on every
        # node-scoped command.
        result = ran('import solid_node.core.loader\n')
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.core.loader imported cadquery')
        self.assertFalse(
            result.imported('solid_node.exact'),
            'importing solid_node.core.loader imported the exact stack')

    def test_loading_a_node_does_not_import_the_test_framework(self):
        result = ran('from solid_node.core.loader import load_node\n'
                     "node = load_node('flat_project/simple_cylinder.py')\n"
                     'print(type(node).__name__)\n',
                     cwd=BASEDIR)
        self.assertEqual(result.stdout.strip(), 'SimpleCylinder',
                         result.stderr)
        self.assertFalse(result.imported('solid_node.test'),
                         'loading a node imported solid_node.test')
        self.assertFalse(result.imported('cadquery'),
                         'loading a Solid2Node imported cadquery')


class CompanionTestDiscovery(TestCase):
    """Discovery still finds the same cases, and still loads the framework.

    This is the other half of the deferral's contract. `TestCase` moved
    to its one use site, `load_tests()`; if it had moved out of reach,
    discovery would return nothing and every meta-test would go quiet
    rather than red.
    """

    def test_discovering_companion_tests_returns_the_same_test_cases(self):
        result = ran(
            'from solid_node.core.loader import load_tests\n'
            "cases = load_tests('meta_project/apart.py')\n"
            'from solid_node.test import TestCase\n'
            "print('NAMES', ' '.join(k.__name__ for k in cases))\n"
            "print('MODULES', ' '.join(k.__module__ for k in cases))\n"
            "print('SUBCLASSES', all(issubclass(k, TestCase) "
            'for k in cases))\n'
            "print('METHODS', ' '.join(sorted(name for name in dir(cases[0]) "
            "if name.startswith('test_'))))\n",
            cwd=BASEDIR)
        self.assertEqual(
            result.stdout.splitlines(),
            ['NAMES ApartTest',
             'MODULES meta_project.test_apart',
             'SUBCLASSES True',
             'METHODS test_cubes_do_not_intersect '
             'test_placed_cube_is_where_placed'],
            result.stderr)

    def test_discovering_companion_tests_imports_the_test_framework(self):
        # Deferred, not optional: the framework is absent until discovery
        # asks for it and present the moment discovery has run.
        result = ran(
            'import sys\n'
            'from solid_node.core.loader import load_tests\n'
            "print('BEFORE', 'solid_node.test' in sys.modules)\n"
            "load_tests('meta_project/apart.py')\n"
            "print('AFTER', 'solid_node.test' in sys.modules)\n",
            cwd=BASEDIR)
        self.assertEqual(result.stdout.split(),
                         ['BEFORE', 'False', 'AFTER', 'True'], result.stderr)

    def test_a_node_without_companion_tests_still_reports_none(self):
        result = ran('from solid_node.core.loader import load_tests\n'
                     "print(load_tests('flat_project/simple_pipe.py'))\n",
                     cwd=BASEDIR)
        self.assertEqual(result.stdout.strip(), '[]', result.stderr)


class SerializerImportCost(TestCase):
    """Publishing needs the driver enumeration, not the scenario base."""

    def test_importing_the_serializer_does_not_import_the_scenario_module(self):
        result = ran('import solid_node.core.serializer\n')
        self.assertFalse(
            result.imported('solid_node.simulation.scenario'),
            'importing the serializer imported the scenario module')
        self.assertFalse(result.imported('solid_node.test'),
                         'importing the serializer imported solid_node.test')
        self.assertFalse(result.imported('cadquery'),
                         'importing the serializer imported cadquery')

    def test_the_serializer_still_reaches_the_driver_enumeration(self):
        # The absence above must come from deferral, not from the
        # serializer having stopped needing what it needs.
        result = ran('import solid_node.core.serializer as serializer\n'
                     'print(serializer.tree_declares_drivers.__module__)\n')
        self.assertEqual(result.stdout.strip(),
                         'solid_node.simulation.enumeration', result.stderr)

    def test_a_build_serializes_without_importing_the_scenario_module(self):
        result = publish('flat_project/simple_cylinder.py')
        self.assertEqual(result.stdout.strip(), 'PUBLISHED True',
                         result.stderr)
        self.assertFalse(
            result.imported('solid_node.simulation.scenario'),
            'publishing a viewer document imported the scenario module')
        self.assertFalse(result.imported('solid_node.test'),
                         'publishing a viewer document imported the test '
                         'framework')
        self.assertFalse(result.imported('cadquery'),
                         'publishing a Solid2Node document imported cadquery')

    def test_a_published_document_still_carries_its_driver_table(self):
        # The enumeration the serializer defers to `.scenario` for is the
        # one thing the deferral could plausibly have taken away.
        result = publish('spinner_project/spinner.py')
        self.assertEqual(result.stdout.strip(), 'PUBLISHED True',
                         result.stderr)
        self.assertTrue(
            result.imported('solid_node.simulation.enumeration'),
            'publishing never reached the driver enumeration')
        self.assertFalse(
            result.imported('solid_node.simulation.scenario'),
            'publishing a viewer document imported the scenario module')


class SimulationPackageExports(TestCase):
    """Every name the package exported still resolves, unchanged.

    `from solid_node.simulation import Driver` is a public surface. The
    accessor may change when these load; it may not change what they are.
    """

    def test_all_lists_exactly_the_names_exported_before(self):
        self.assertEqual(sorted(solid_node.simulation.__all__),
                         sorted(EXPECTED_EXPORTS))

    def test_every_export_is_the_object_its_submodule_defines(self):
        for name, module_name in EXPECTED_EXPORTS.items():
            with self.subTest(name=name):
                module = importlib.import_module(module_name)
                self.assertIs(getattr(solid_node.simulation, name),
                              getattr(module, name))

    def test_star_import_binds_every_exported_name(self):
        result = ran(
            'from solid_node.simulation import *\n'
            f'missing = [n for n in {sorted(EXPECTED_EXPORTS)!r} '
            'if n not in dir()]\n'
            'print(missing)\n')
        self.assertEqual(result.stdout.strip(), '[]', result.stderr)

    def test_dir_offers_the_exported_names(self):
        listed = dir(solid_node.simulation)
        for name in EXPECTED_EXPORTS:
            with self.subTest(name=name):
                self.assertIn(name, listed)

    def test_importing_the_package_imports_no_submodule(self):
        result = ran('import solid_node.simulation\n')
        for name in ('driver', 'enumeration', 'instruction', 'scenario',
                     'sim'):
            with self.subTest(submodule=name):
                self.assertFalse(
                    result.imported(f'solid_node.simulation.{name}'),
                    f'importing the package imported .{name}')

    def test_reaching_the_enumeration_does_not_import_the_scenario(self):
        # The chain the serializer walks on every publication.
        result = ran(
            'from solid_node.simulation.enumeration import '
            'tree_declares_drivers\n')
        self.assertFalse(
            result.imported('solid_node.simulation.scenario'),
            'reaching .enumeration imported .scenario')
        self.assertFalse(result.imported('solid_node.test'),
                         'reaching .enumeration imported solid_node.test')

    def test_naming_the_scenario_export_imports_the_test_framework(self):
        result = ran('from solid_node.simulation import ScenarioTest\n'
                     'assert isinstance(ScenarioTest, type)\n')
        self.assertTrue(result.imported('solid_node.test'),
                        'resolving ScenarioTest did not import the framework')

    def test_resolving_a_name_caches_it_in_module_globals(self):
        # The cache keeps a second access a plain dict lookup, and stops
        # a submodule that reads a lazy name during its own import from
        # re-entering the accessor forever.
        result = ran(
            'import solid_node.simulation as simulation\n'
            "print('BEFORE', 'Sim' in vars(simulation))\n"
            'first = simulation.Sim\n'
            "print('AFTER', vars(simulation).get('Sim') is first)\n"
            "print('AGAIN', simulation.Sim is first)\n")
        self.assertEqual(result.stdout.split(),
                         ['BEFORE', 'False', 'AFTER', 'True',
                          'AGAIN', 'True'], result.stderr)

    def test_an_unknown_name_still_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            solid_node.simulation.NoSuchSimulationName

    def test_a_submodule_is_reachable_after_a_bare_package_import(self):
        # The eager re-exports used to bind every submodule as a side
        # effect of the import machinery.
        for submodule in EXPECTED_EXPORTS.values():
            name = submodule.rsplit('.', 1)[1]
            with self.subTest(submodule=name):
                result = ran('import solid_node.simulation\n'
                             f'print(solid_node.simulation.{name}.__name__)\n')
                self.assertEqual(result.stdout.strip(), submodule,
                                 result.stderr)

    def test_a_submodule_attribute_is_the_imported_module(self):
        module = importlib.import_module('solid_node.simulation.driver')
        self.assertIs(solid_node.simulation.driver, module)


class SimulationBrokenExport(TestCase):
    """A deferred import that fails reports its own failure.

    The classic PEP 562 trap: an `ImportError` raised inside
    `__getattr__` looks, to anything that treats the accessor as a
    lookup, like the name simply not being there.

    `ScenarioTest` used to reach `solid_node.test` -> `solid_node.exact`
    -> `cadquery`, and these tests read a broken exact stack through it.
    Now that the test framework defers the exact stack too, that chain
    stops one step earlier: reading `ScenarioTest` no longer needs
    cadquery at all, so the guard follows the dependency to where it
    actually lives -- the kernel names on `solid_node.test`, whose first
    USE is now the first thing that can fail. The trap is unchanged and
    so is what it must not do; only the name that springs it moved.
    """

    def _access(self, expression):
        return ran(
            CADQUERY_ABSENT +
            'import solid_node.simulation\n'
            'try:\n'
            f'    {expression}\n'
            'except AttributeError as wrong:\n'
            "    print('ATTRIBUTE_ERROR', wrong)\n"
            'except ImportError as failure:\n'
            "    print('IMPORT_ERROR', failure)\n"
            'except Exception as other:\n'
            "    print('OTHER', type(other).__name__, other)\n"
            'else:\n'
            "    print('NO_ERROR')\n")

    def _use_kernel_name(self):
        """Call a deferred kernel name on `solid_node.test`, exact stack
        absent. Reading the name is not enough -- the deferred binding
        resolves on USE, which is the point the failure must surface."""
        return ran(
            CADQUERY_ABSENT +
            'import solid_node.test\n'
            'try:\n'
            "    solid_node.test.intersect_shapes(None, None, 'a', 'b')\n"
            'except AttributeError as wrong:\n'
            "    print('ATTRIBUTE_ERROR', wrong)\n"
            'except ImportError as failure:\n'
            "    print('IMPORT_ERROR', failure)\n"
            'except Exception as other:\n'
            "    print('OTHER', type(other).__name__, other)\n"
            'else:\n'
            "    print('NO_ERROR')\n")

    def test_the_package_still_imports_without_the_exact_stack(self):
        # Not a claim that cadquery is optional -- it is a required
        # dependency and stays one. It is a claim about WHEN the failure
        # is allowed to happen: at first use of a name that needs it.
        result = ran(CADQUERY_ABSENT +
                     'import solid_node.simulation\n'
                     "print('IMPORTED')\n")
        self.assertEqual(result.stdout.strip(), 'IMPORTED', result.stderr)

    def test_the_scenario_export_no_longer_needs_the_stack(self):
        # The deferral went one step deeper than this class used to
        # assert: the scenario export reaches the test framework, and the
        # test framework no longer reaches cadquery.
        result = self._access('solid_node.simulation.ScenarioTest')
        self.assertEqual(result.stdout.strip(), 'NO_ERROR', result.stderr)

    def test_using_a_kernel_name_raises_the_underlying_import_error(self):
        result = self._use_kernel_name()
        reported = result.stdout.strip()
        self.assertTrue(reported.startswith('IMPORT_ERROR'), reported)
        self.assertIn('cadquery', reported)

    def test_reading_a_kernel_name_is_not_a_missing_attribute(self):
        # The trap itself: whatever a broken install does, it must not
        # look like `solid_node.test` never had the name.
        result = ran(
            CADQUERY_ABSENT +
            'import solid_node.test\n'
            'try:\n'
            "    present = hasattr(solid_node.test, 'intersect_shapes')\n"
            'except ImportError as failure:\n'
            "    print('IMPORT_ERROR', failure)\n"
            'else:\n'
            "    print('PRESENT', present)\n")
        reported = result.stdout.strip()
        self.assertIn(reported.split()[0], ('IMPORT_ERROR', 'PRESENT'),
                      reported)
        self.assertNotIn('False', reported)


class BuildImportCost(TestCase):
    """The headline: what a real `solid build` actually costs.

    Every assertion above is about one import site. This one is the
    claim the change is for, made against the CLI a maker and the shop
    floor actually run.
    """

    def test_a_solid2_only_build_imports_no_cadquery(self):
        result = build('flat_project/simple_cylinder.py')
        self.assertFalse(result.imported('cadquery'),
                         'building a Solid2Node project imported cadquery')
        self.assertFalse(result.imported('solid_node.exact'),
                         'building a Solid2Node project imported the '
                         'exact stack')
        self.assertFalse(result.imported('solid_node.test'),
                         'building a project imported the test framework')

    def test_a_solid2_only_assembly_build_imports_no_cadquery(self):
        # An assembly walks the linked tree, the piece inventory and the
        # serializer -- more of the framework than a single leaf does.
        result = build('pieces_project/assembly.py')
        self.assertFalse(result.imported('cadquery'),
                         'building a Solid2Node assembly imported cadquery')
        self.assertFalse(result.imported('solid_node.test'),
                         'building an assembly imported the test framework')

    def test_a_cadquery_build_still_imports_cadquery(self):
        # The half that makes the half above mean something: absence has
        # to be discrimination, not the exact stack having gone missing.
        result = build('stl_project/originals.py:OriginalBracket')
        self.assertTrue(result.imported('cadquery'),
                        'building a CadQueryNode project did not import '
                        'cadquery')


def run_tests(reference):
    """Run a real `solid test` of a fixture, in a throwaway build tree."""
    with tempfile.TemporaryDirectory(prefix='solid-lazy-test-') as build_dir:
        return ran('from solid_node.cli import manage\nmanage()\n',
                   argv=['test', reference],
                   env={'SOLID_BUILD_DIR': build_dir},
                   cwd=BASEDIR)


class TestFrameworkImportCost(TestCase):
    """Running tests is not a reason to load the exact-geometry stack.

    `LoaderImportCost` above asserts this from the outside: loading a node
    imports neither the test framework nor cadquery. That left the inside
    unasserted -- the moment a test IS discovered, `solid_node.test`
    imports `solid_node.exact` at module scope and every test process pays
    2.84 s for cadquery, whether or not a single node in the project is
    exact.

    As always the absence assertions are paired with the presence ones
    that would catch a deferral quietly becoming a removal: an exact
    comparison must still import the stack and return the same verdict.
    """

    def test_importing_the_test_framework_does_not_import_cadquery(self):
        result = ran('import solid_node.test\n')
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.test imported cadquery')
        self.assertFalse(result.imported('solid_node.exact'),
                         'importing solid_node.test imported the exact stack')

    def test_a_faceted_test_run_imports_no_cadquery(self):
        # The consequence that pays for the change, against the real CLI:
        # a project modelling in solid2 and asserting over meshes runs its
        # tests without ever loading the boundary-representation kernel.
        result = run_tests('meta_project/separated.py')
        self.assertIn('test_no_pairwise_intersections', result.stdout,
                      result.stderr)
        self.assertFalse(result.imported('cadquery'),
                         'a faceted test run imported cadquery')

    def test_an_exact_test_run_still_imports_cadquery(self):
        # The half that makes the half above mean something.
        result = run_tests('meta_project/exact_tight_fit.py')
        self.assertTrue(result.imported('cadquery'),
                        'an exact test run did not import cadquery')


class ExactNamesStayPatchable(TestCase):
    """The deferred exact names remain module globals of `solid_node.test`.

    Deferring the import moves WHEN the kernel loads, not where its names
    live. A caller that patches one keeps working -- before the exact path
    has ever run, and after it has already resolved the name -- because
    the deferred binding is an ordinary module global that resolution
    replaces and a patch replaces in turn.
    """

    EXACT_NAMES = ('fuse_shapes', 'intersect_shapes', 'placed_shape',
                   'solid_count', 'solid_volume')

    def test_every_deferred_name_is_readable(self):
        import solid_node.test as test_module
        for name in self.EXACT_NAMES:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(test_module, name)),
                                f'{name} is not readable on solid_node.test')

    def test_a_patch_applied_before_first_use_is_used(self):
        result = ran(PATCH_BEFORE_USE, cwd=BASEDIR)
        self.assertEqual(result.stdout.strip(), 'PATCHED', result.stderr)

    def test_a_patch_applied_after_resolution_is_used(self):
        result = ran(PATCH_AFTER_USE, cwd=BASEDIR)
        self.assertEqual(result.stdout.strip(), 'RESOLVED PATCHED',
                         result.stderr)


# Both snippets drive the exact branch of `_placed_intersection` with every
# kernel name patched, so they exercise the real internal call sites without
# needing real geometry -- what is under test is whose function those sites
# call, not what it computes. `FakeShape.Faces()` returns none, which is
# enough for the face-box tier (ADR-092) inside that branch to decline
# immediately -- a faceless shape always falls through -- so the record
# still reaches the patched `intersect_shapes` exactly as before that tier
# existed.
_PATCH = '''
import numpy as np


class FakeShape:

    def Solids(self):
        return []

    def Faces(self):
        return []


class FakeSolid:
    name = 'fake'


def patched_verdict():
    t.intersect_shapes = lambda first, second, one, two: 'RESULT'
    t.solid_count = lambda result: 0
    t.solid_volume = lambda result: 0.0
    shape = FakeShape()
    # A real `_place_solid` record's width, so the tier ahead of the
    # boolean can read the matrix (index 6) and local shape (index 8)
    # it needs; index 5 (exact identity) stays None, so `_record_key`
    # still declines to memoize this fake comparison, as it always has.
    record = (FakeSolid(), None, None, shape, None, None, np.eye(4),
              None, shape)
    stats = t._placed_intersection(record, record)
    return 'PATCHED' if (stats.exact and stats.is_empty) else 'NOT PATCHED'
'''

PATCH_BEFORE_USE = 'import solid_node.test as t\n' + _PATCH + '''
print(patched_verdict())
'''

# `solid_count` is called for real first -- on a duck-typed shape, so the
# resolution is genuine without building geometry -- which is what makes the
# second half an assertion about a name that has ALREADY been replaced by the
# resolved kernel function rather than one still holding its deferred binding.
PATCH_AFTER_USE = 'import solid_node.test as t\n' + _PATCH + '''
resolved = 'RESOLVED' if t.solid_count(FakeShape()) == 0 else 'UNRESOLVED'
print(resolved, patched_verdict())
'''
