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
    lookup, like the name simply not being there. `ScenarioTest` reaches
    `solid_node.test` -> `solid_node.exact` -> `cadquery`, so a broken
    install of the exact stack is exactly the case that must not be
    reported as a missing attribute.
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

    def test_the_package_still_imports_without_the_exact_stack(self):
        # Not a claim that cadquery is optional -- it is a required
        # dependency and stays one. It is a claim about WHEN the failure
        # is allowed to happen: at first use of a name that needs it.
        result = ran(CADQUERY_ABSENT +
                     'import solid_node.simulation\n'
                     "print('IMPORTED')\n")
        self.assertEqual(result.stdout.strip(), 'IMPORTED', result.stderr)

    def test_a_broken_export_raises_the_underlying_import_error(self):
        result = self._access('solid_node.simulation.ScenarioTest')
        reported = result.stdout.strip()
        self.assertTrue(reported.startswith('IMPORT_ERROR'), reported)
        self.assertIn('cadquery', reported)

    def test_the_reported_failure_names_the_requested_export(self):
        result = self._access('solid_node.simulation.ScenarioTest')
        self.assertIn('ScenarioTest', result.stdout)

    def test_hasattr_does_not_turn_a_broken_export_into_a_missing_name(self):
        result = ran(
            CADQUERY_ABSENT +
            'import solid_node.simulation\n'
            'try:\n'
            "    present = hasattr(solid_node.simulation, 'ScenarioTest')\n"
            'except ImportError as failure:\n'
            "    print('IMPORT_ERROR', failure)\n"
            'else:\n'
            "    print('SWALLOWED', present)\n")
        reported = result.stdout.strip()
        self.assertTrue(reported.startswith('IMPORT_ERROR'), reported)
        self.assertIn('ScenarioTest', reported)


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
