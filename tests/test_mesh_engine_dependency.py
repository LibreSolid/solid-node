# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The mesh engine (`manifold3d`) is a conditional dependency of the
faceted path, not a blanket requirement of the assertion module.

These tests run the framework in a subprocess where `manifold3d` is
genuinely unimportable (see tests/mesh_engine_absent.py). They pin the
two halves of the contract: what must keep working without the mesh
engine, and what must fail naming it.

Originating evidence: the browser-engine spike, "Upstream findings for
the framework" item 4 and evidence/fixture-host-verification.md run F.
"""

from unittest import TestCase, skipUnless

from .mesh_engine_absent import (mesh_engine_is_installed, run_python,
                                 run_solid_test)


HAVE_ENGINE = mesh_engine_is_installed()


@skipUnless(HAVE_ENGINE,
            'the absent-engine subprocess is only meaningful when this '
            'interpreter genuinely has the mesh engine to withhold')
class AssertionModuleImportTest(TestCase):
    """Importing the assertions must not require the mesh engine: an
    all-exact project's assertions live in the same module and are
    decided entirely by the boundary-representation kernel."""

    def test_assertion_module_imports_without_the_mesh_engine(self):
        result = run_python(
            'import solid_node.test\n'
            'print("IMPORTED", hasattr(solid_node.test, "TestCase"))\n')

        self.assertIn('IMPORTED True', result.stdout, result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_importing_does_not_resolve_the_mesh_engine(self):
        """Import must not merely succeed -- it must not have reached
        for the engine at all, or the dependency is still eager and only
        the error moved."""
        result = run_python(
            'import solid_node.test, sys\n'
            'print("RESOLVED", "manifold3d" in sys.modules)\n')

        self.assertIn('RESOLVED False', result.stdout, result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)


@skipUnless(HAVE_ENGINE,
            'the absent-engine subprocess is only meaningful when this '
            'interpreter genuinely has the mesh engine to withhold')
class ExactPathWithoutMeshEngineTest(TestCase):
    """An all-exact assembly is verified by the kernel, so it must reach
    the same verdict with no mesh engine installed at all."""

    def test_exact_assembly_asserts_without_the_mesh_engine(self):
        result = run_solid_test('tests/meta_project/exact_tight_fit.py')

        self.assertIn('Ran 1 tests in', result.stdout, result.stderr)
        self.assertIn('1 passed, 0 failed', result.stdout, result.stderr)
        self.assertNotIn('manifold3d', result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_connectivity_asserts_without_the_mesh_engine(self):
        """`assertNoDisconnectedSolids` reads connected components from
        the cached base mesh for a faceted solid and from `solid_count`
        for an exact one -- neither needs the mesh engine. It was lost
        only because the module would not import."""
        result = run_solid_test('tests/meta_project/solid_integrity_green.py')

        self.assertIn('0 failed', result.stdout, result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)


@skipUnless(HAVE_ENGINE,
            'the absent-engine subprocess is only meaningful when this '
            'interpreter genuinely has the mesh engine to withhold')
class MissingMeshEngineIsActionableTest(TestCase):
    """A path that genuinely needs the engine fails naming it, the
    operation, and the reason -- never a bare import error and never a
    silently weaker verdict."""

    def test_faceted_interference_names_the_missing_mesh_engine(self):
        result = run_solid_test(
            'tests/meta_project/assembly_integrity_contact.py')

        self.assertIn('manifold3d', result.stdout, result.stderr)
        self.assertIn('assertNoSolidInterference', result.stdout)
        self.assertIn('0 passed, 1 failed', result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def test_gravity_support_names_the_missing_mesh_engine(self):
        """ADR-049 extracts contact patches from meshed intersections
        for every body, exact solids included, so this assertion is a
        requiring path even for an all-exact assembly. It must say so
        rather than pass or fail obscurely."""
        result = run_solid_test(
            'tests/meta_project/assembly_supported_exact.py')

        self.assertIn('manifold3d', result.stdout, result.stderr)
        self.assertIn('assertAssemblySupported', result.stdout)
        self.assertIn('0 passed, 1 failed', result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def test_the_failure_is_not_a_bare_import_error(self):
        result = run_solid_test(
            'tests/meta_project/assembly_integrity_contact.py')

        self.assertNotIn('ModuleNotFoundError', result.stdout)
        self.assertNotIn('ModuleNotFoundError', result.stderr)
