# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`solid_node.node` resolves its backend exports on first access.

The package used to re-export every backend class eagerly, so importing
ANY module under it -- `from solid_node.node.base import AbstractBaseNode`,
which the loader, the builder, the piece inventory, the test manager and
the simulation enumerator all do -- ran that whole list and dragged in
`solid_node.exact` -> `cadquery`, 1.84 s on every `solid` invocation.

Two things have to stay true at once, so both are pinned here: nothing
is imported until it is named, and what comes back when it IS named is
the identical class object callers got before. `CadQueryNode` carries
the `CheckCQEditor` metaclass and consumers test it with `issubclass`,
so a lazy proxy would be a silent behaviour change, not an optimisation.

The laziness itself is only observable in a process that has not already
imported the framework, so those assertions run through
`tests/import_probe.py` in a fresh interpreter. The identity assertions
run in-process, where they are cheaper and just as conclusive.
"""

import importlib
from unittest import TestCase

from .import_probe import probe

import solid_node.node


# The names `solid_node/node/__init__.py` exported eagerly before this
# change, each with the submodule that defines it. Written out here
# rather than read from the package under test: a table that agreed with
# itself would prove nothing about what consumers used to import.
EXPECTED_EXPORTS = {
    'StlRenderStart': 'solid_node.node.base',
    'AssemblyNode': 'solid_node.node.assembly',
    'Port': 'solid_node.node.ports',
    'RotationalPort': 'solid_node.node.ports',
    'TranslationalPort': 'solid_node.node.ports',
    'SignalPort': 'solid_node.node.ports',
    'declared_ports': 'solid_node.node.ports',
    'Time': 'solid_node.node.timebase',
    'FusionNode': 'solid_node.node.fusion',
    'CadQueryNode': 'solid_node.node.adapters.cadquery',
    'Build123dNode': 'solid_node.node.adapters.build123d',
    'SheetLeafNode': 'solid_node.node.sheet_leaf',
    'Build123dSheetNode': 'solid_node.node.adapters.build123d_sheet',
    'FlexibleNode': 'solid_node.node.flexible',
    'MolejoNode': 'solid_node.node.adapters.molejo',
    'Solid2Node': 'solid_node.node.adapters.solid2',
    'OpenScadNode': 'solid_node.node.adapters.openscad',
    'JScadNode': 'solid_node.node.adapters.jscad',
    'StlNode': 'solid_node.node.adapters.stl',
    'StepNode': 'solid_node.node.adapters.step',
    'property_as_number': 'solid_node.node.decorators',
    # Added by the declarative node API, lazily like the rest. Only the
    # STRUCTURE half: the parameter kinds this package also exported for
    # one unreleased cycle now live in `solid_node.parameters` and are
    # pinned out of here by ParameterModuleSurface below.
    'declared_children': 'solid_node.node.declarative',
}

# What the node package must NOT answer for. A build parameter is imported
# from `solid_node.parameters`, and one import line saying which of its
# names is a node kind and which is a knob is the whole point of the split;
# a re-export here would quietly restore the ambiguity.
PARAMETER_NAMES = ('Quantity', 'Length', 'Angle', 'Count', 'Ratio', 'Scalar',
                   'Flag', 'declared_parameters')

# The exports whose submodule reaches `solid_node.exact` -> `cadquery`.
EXACT_EXPORTS = ('FusionNode', 'CadQueryNode', 'Build123dNode',
                 'Build123dSheetNode', 'StepNode')

# Refuse `cadquery` the way an interpreter without the wheel does, in the
# shape of tests/mesh_engine_absent.py: a `sys.meta_path` finder that
# raises, rather than a stub, so the deferred import fails for the real
# reason a broken install fails.
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


class NodePackageImportCost(TestCase):
    """What importing the package, and only the package, costs."""

    def _ran(self, snippet):
        """Probe `snippet`, insisting it reached the end.

        The probe reports whichever modules were loaded before the child
        died, so a snippet that raised would satisfy "cadquery is
        absent" for entirely the wrong reason. The marker makes the run
        prove it completed.
        """
        result = probe(snippet + "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        return result

    def test_importing_the_node_package_does_not_import_cadquery(self):
        result = self._ran('import solid_node.node\n')
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.node imported cadquery')
        self.assertFalse(result.imported('solid_node.exact'),
                         'importing solid_node.node imported the exact stack')

    def test_importing_the_node_base_does_not_import_cadquery(self):
        # The path that actually hurts: every core consumer imports
        # `solid_node.node.base`, which runs the package __init__ first.
        result = self._ran(
            'from solid_node.node.base import AbstractBaseNode\n')
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.node.base imported cadquery')

    def test_importing_a_faceted_backend_does_not_import_cadquery(self):
        # An OpenSCAD/solid2-only project names Solid2Node and nothing
        # else; it must not pay for the exact stack.
        result = self._ran('from solid_node.node import Solid2Node\n')
        self.assertFalse(result.imported('cadquery'),
                         'resolving Solid2Node imported cadquery')

    def test_naming_an_exact_backend_imports_cadquery(self):
        # The other half of the contract: deferral must not mean absent.
        for name in EXACT_EXPORTS:
            with self.subTest(name=name):
                result = self._ran(
                    f'from solid_node.node import {name}\n'
                    f'assert isinstance({name}, type), {name!r}\n')
                self.assertTrue(result.imported('cadquery'),
                                f'resolving {name} did not import cadquery')

    def test_importing_the_node_package_does_not_import_the_step_reader(self):
        # design D10 / ADR-078: OCP is the boundary-representation
        # kernel's own package, and StepNode's reader lives inside it;
        # a bare package import must not pull it in.
        result = self._ran('import solid_node.node\n')
        self.assertFalse(result.imported('OCP'),
                         'importing solid_node.node imported OCP')

    def test_naming_step_node_imports_the_step_reader(self):
        result = self._ran(
            'from solid_node.node import StepNode\n'
            'assert isinstance(StepNode, type), StepNode\n')
        self.assertTrue(result.imported('OCP'),
                        'resolving StepNode did not import OCP')


class NodePackageExports(TestCase):
    """Every name the package used to export still resolves, unchanged."""

    def test_all_lists_exactly_the_names_exported_before(self):
        self.assertEqual(sorted(solid_node.node.__all__),
                         sorted(EXPECTED_EXPORTS))

    def test_every_export_is_the_object_its_submodule_defines(self):
        for name, module_name in EXPECTED_EXPORTS.items():
            with self.subTest(name=name):
                module = importlib.import_module(module_name)
                self.assertIs(getattr(solid_node.node, name),
                              getattr(module, name))

    def test_a_resolved_export_is_a_real_class_not_a_proxy(self):
        # CadQueryNode is built by the CheckCQEditor metaclass and
        # consumers test it with issubclass, so a proxy would break them
        # in ways an attribute-forwarding test would not notice.
        from solid_node.node import CadQueryNode
        from solid_node.node.adapters.cadquery import CheckCQEditor
        from solid_node.node.exact_leaf import ExactLeafNode

        self.assertIsInstance(CadQueryNode, type)
        self.assertIs(type(CadQueryNode), CheckCQEditor)
        self.assertTrue(issubclass(CadQueryNode, ExactLeafNode))

    def test_star_import_binds_every_exported_name(self):
        result = probe(
            'from solid_node.node import *\n'
            f'missing = [n for n in {sorted(EXPECTED_EXPORTS)!r} '
            'if n not in dir()]\n'
            'print(missing)\n')
        self.assertEqual(result.status, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '[]')

    def test_dir_offers_the_exported_names(self):
        listed = dir(solid_node.node)
        for name in EXPECTED_EXPORTS:
            with self.subTest(name=name):
                self.assertIn(name, listed)

    def test_resolving_a_name_caches_it_in_module_globals(self):
        # The cache is what keeps the second access a plain dict lookup,
        # and it is also what stops a submodule that reads a lazy name
        # during its own import from re-entering the accessor forever.
        # It has to be observed in a fresh interpreter: by the time this
        # suite runs, the names are long since resolved.
        result = probe(
            'import solid_node.node as node\n'
            "print('BEFORE', 'StlNode' in vars(node))\n"
            'first = node.StlNode\n'
            "print('AFTER', vars(node).get('StlNode') is first)\n"
            "print('AGAIN', node.StlNode is first)\n")
        self.assertEqual(result.stdout.split(),
                         ['BEFORE', 'False', 'AFTER', 'True',
                          'AGAIN', 'True'], result.stderr)

    def test_an_unknown_name_still_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            solid_node.node.NoSuchNode

    def test_an_unknown_name_is_not_reported_as_an_import_failure(self):
        result = probe(
            'import solid_node.node\n'
            'try:\n'
            '    solid_node.node.NoSuchNode\n'
            'except AttributeError:\n'
            "    print('ATTRIBUTE_ERROR')\n"
            'except Exception as other:\n'
            "    print('OTHER', type(other).__name__, other)\n"
            'else:\n'
            "    print('NO_ERROR')\n")
        self.assertEqual(result.status, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'ATTRIBUTE_ERROR')


class NodePackageSubmodules(TestCase):
    """Submodule attributes survive losing the eager imports.

    `from .assembly import AssemblyNode` used to bind
    `solid_node.node.assembly` as a side effect of the import machinery,
    so a consumer could read it after importing only the package. The
    accessor has to resolve submodule names too, or that quietly breaks.
    """

    def test_a_submodule_is_reachable_after_a_bare_package_import(self):
        for submodule in ('assembly', 'ports', 'operations', 'adapters'):
            with self.subTest(submodule=submodule):
                result = probe(
                    'import solid_node.node\n'
                    f'module = solid_node.node.{submodule}\n'
                    'print(module.__name__)\n')
                self.assertEqual(result.status, 0, result.stderr)
                self.assertEqual(result.stdout.strip(),
                                 f'solid_node.node.{submodule}')

    def test_a_submodule_attribute_is_the_imported_module(self):
        module = importlib.import_module('solid_node.node.assembly')
        self.assertIs(solid_node.node.assembly, module)

    def test_reading_a_submodule_does_not_import_its_siblings(self):
        result = probe('import solid_node.node\n'
                       'solid_node.node.assembly\n'
                       "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        self.assertFalse(result.imported('cadquery'),
                         'reading one submodule imported the exact stack')


class NodePackageBrokenBackend(TestCase):
    """A deferred import that fails reports its own failure.

    This is the classic PEP 562 trap: an `ImportError` raised inside
    `__getattr__` looks, to anything that treats the accessor as a
    lookup, like the name simply not being there. A broken install must
    not be reported as a missing attribute.
    """

    def _access(self, expression):
        return probe(
            CADQUERY_ABSENT +
            'import solid_node.node\n'
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
        result = probe(CADQUERY_ABSENT +
                       'import solid_node.node\n'
                       "print('IMPORTED')\n")
        self.assertEqual(result.stdout.strip(), 'IMPORTED', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_a_broken_backend_raises_the_underlying_import_error(self):
        result = self._access('solid_node.node.CadQueryNode')
        self.assertEqual(result.status, 0, result.stderr)
        reported = result.stdout.strip()
        self.assertTrue(reported.startswith('IMPORT_ERROR'), reported)
        self.assertIn('cadquery', reported)

    def test_the_reported_failure_names_the_requested_export(self):
        result = self._access('solid_node.node.CadQueryNode')
        self.assertEqual(result.status, 0, result.stderr)
        self.assertIn('CadQueryNode', result.stdout)

    def test_hasattr_does_not_turn_a_broken_backend_into_a_missing_name(self):
        result = probe(
            CADQUERY_ABSENT +
            'import solid_node.node\n'
            'try:\n'
            "    present = hasattr(solid_node.node, 'CadQueryNode')\n"
            'except ImportError as failure:\n'
            "    print('IMPORT_ERROR', failure)\n"
            'else:\n'
            "    print('SWALLOWED', present)\n")
        self.assertEqual(result.status, 0, result.stderr)
        reported = result.stdout.strip()
        self.assertTrue(reported.startswith('IMPORT_ERROR'), reported)
        self.assertIn('CadQueryNode', reported)


class ParameterModuleSurface(TestCase):
    """Build parameters come from `solid_node.parameters`, and only there.

    Two properties, and the second is the one that decays: a module can
    be created without anyone noticing that the old path still works, and
    then every import line is ambiguous again for no reason a reader can
    see. So the absence is pinned as hard as the presence.

    The import cost is pinned too. This module sits at the top of every
    node module in every project, and it holds nothing but declarations
    and arithmetic over exponents, so it must reach no framework module
    and no CAD backend at all -- which is also why it needs no lazy
    accessor of its own.
    """

    # Everything a project or the framework may name. The kinds and the
    # `Quantity` base a project subclasses to extend the ontology, the
    # algebra types a formula is built from, the enumerator, and the two
    # errors a bad declaration raises.
    EXPECTED = ('Quantity', 'Length', 'Angle', 'Count', 'Ratio', 'Scalar',
                'Flag', 'Expression', 'Formula', 'declared_parameters',
                'DimensionError', 'ParameterError')

    def test_the_module_exports_the_parameter_vocabulary(self):
        import solid_node.parameters as parameters

        self.assertEqual(sorted(parameters.__all__), sorted(self.EXPECTED))

    def test_the_node_package_does_not_export_a_parameter(self):
        for name in PARAMETER_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, solid_node.node.__all__)
                with self.assertRaises(AttributeError) as raised:
                    getattr(solid_node.node, name)
                self.assertIn(name, str(raised.exception))

    def test_importing_parameters_imports_nothing_else(self):
        result = probe('import solid_node.parameters\n'
                       "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.parameters imported cadquery')
        self.assertEqual(
            result.imported_under('solid_node'),
            {'solid_node', 'solid_node.parameters'},
            'importing solid_node.parameters reached another framework '
            'module')

    def test_the_names_are_bound_eagerly(self):
        # No `__getattr__` accessor here: there is nothing expensive to
        # defer, and deferral would be indirection a reader has to unpick
        # for no gain. Read out of the module dict, which an accessor
        # would not have populated.
        import solid_node.parameters as parameters

        for name in self.EXPECTED:
            with self.subTest(name=name):
                self.assertIn(name, vars(parameters))

    def test_a_declaration_module_defines_no_parameter_kind(self):
        # The other half of the cut. `declarative` keeps the structure
        # declarations, so no kind is DEFINED there any more and a
        # caller reaching for one is reaching into the wrong module. It
        # does borrow three names -- the declaration base the declaring
        # namespace tests against, the operand evaluator a child
        # declaration resolves its arguments with, and the enumerator
        # construction reads -- and those are imports, pinned here to
        # come from the parameter module and nowhere else.
        from solid_node.node import declarative

        for name in ('Length', 'Angle', 'Count', 'Ratio', 'Scalar',
                     'Quantity', 'Flag', 'Expression', 'Formula'):
            with self.subTest(name=name):
                self.assertNotIn(name, vars(declarative))

        for name in ('Declaration', 'evaluate', 'declared_parameters'):
            with self.subTest(name=name):
                self.assertEqual(getattr(declarative, name).__module__,
                                 'solid_node.parameters')
