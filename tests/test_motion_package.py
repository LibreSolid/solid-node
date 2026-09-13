# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`solid_node.motion` -- what moves, and what drives what.

One package, three submodules, each answering to an import line: `ports`
for a value that flows between nodes (and the root's own time channel),
`joints` for a pair that places a body, `couplings` for a law between two
coordinates. This cycle (OpenSpec change ``motion-package``) moves ports
and the declared time base here from `solid_node.node`, verbatim, and
leaves `joints` and `couplings` empty for the two cycles that follow.

The move is deliberately unshimmed: `solid_node.node` stops answering for
any of the six moved names, and the old path fails loudly with a message
naming the new one. These tests pin the new home, the two empty
submodules, the refusal, both import orders, and the import cost -- all
of it failing on the current tree before the move (task 1.10), and green
after.
"""

from unittest import TestCase

from solid2 import cube

from .base import BaseNodeTest
from .import_probe import probe


class MotionPortsExportsTest(BaseNodeTest):
    """`solid_node.motion.ports` is the one home for ports and the time
    base, and what it exports is the class the framework actually uses."""

    def test_the_module_exports_ports_and_the_time_base(self):
        from solid_node.motion import ports

        for name in ('Port', 'BoundPort', 'RotationalPort',
                     'TranslationalPort', 'SignalPort', 'bind',
                     'declared_ports', 'Time', 'declared_time'):
            with self.subTest(name=name):
                self.assertTrue(hasattr(ports, name), name)

    def test_a_node_declares_binds_and_reads_through_the_moved_port(self):
        from solid_node.motion.ports import RotationalPort
        from solid_node.node import Solid2Node

        class Shaft(Solid2Node):
            angle = RotationalPort(out=True, unit='deg')

            def render(self):
                return cube(1, center=True)

        shaft = Shaft()
        shaft.angle.value = 30
        self.assertEqual(shaft.angle.value, 30)

    def test_a_root_declares_and_reads_the_moved_time_base(self):
        from solid_node.motion.ports import Time
        from solid_node.node import AssemblyNode

        class Root(AssemblyNode):
            time = Time(loop=60)

            def render(self):
                return []

        self.assertEqual(Root.time.loop, 60.0)
        root = Root()
        root.assemble()
        self.assertIn('$t', str(root.time))
        self.assertIn('60', str(root.time))


class MotionSubmodulesTest(TestCase):
    """`joints` and `couplings` exist and are documented. Both are
    filled now -- cycle 2 put the lower pairs in one and cycle 3 the
    relation in the other -- so what this pins is the module's own
    named surface, not its emptiness."""

    def test_the_couplings_module_names_the_relation(self):
        import solid_node.motion.couplings as couplings

        self.assertTrue(couplings.__doc__ and couplings.__doc__.strip())
        for name in ('Affine', 'Relation', 'DerivedCoordinate',
                     'UnreachedCoordinate', 'DoublyBound', 'NotInvertible',
                     'declared_relations'):
            with self.subTest(name=name):
                self.assertIn(name, couplings.__all__)
                self.assertTrue(hasattr(couplings, name))


class MotionPackageExportsNothingTest(TestCase):
    """The package `__init__` names no name: the submodule is the only
    import path, so an import line always says which kind is in use."""

    def test_the_package_itself_exports_no_name(self):
        import solid_node.motion as motion

        for name in ('RotationalPort', 'TranslationalPort', 'SignalPort',
                     'Port', 'BoundPort', 'declared_ports', 'Time',
                     'declared_time', 'bind'):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError):
                    getattr(motion, name)


class OldPathRefusedTest(TestCase):
    """`solid_node.node` no longer answers for a port or the time base --
    no re-export, no alias, no shim."""

    MOVED = ('Port', 'RotationalPort', 'TranslationalPort', 'SignalPort',
             'declared_ports', 'Time')

    def test_importing_a_moved_name_from_node_raises_import_error(self):
        for name in self.MOVED:
            with self.subTest(name=name):
                with self.assertRaises(ImportError) as raised:
                    exec(f'from solid_node.node import {name}\n', {})
                self.assertIn('solid_node.motion.ports',
                              str(raised.exception))

    def test_reading_the_removed_submodules_gives_the_same_redirect(self):
        # ImportError, not AttributeError: only an exception outside
        # AttributeError's own hierarchy survives CPython's `hasattr()`
        # probe inside the import machinery unclipped, which is what lets
        # `from solid_node.node import RotationalPort` (above) carry this
        # same message instead of the generic "cannot import name".
        import solid_node.node as node

        for name in ('ports', 'timebase'):
            with self.subTest(name=name):
                with self.assertRaises(ImportError) as raised:
                    getattr(node, name)
                self.assertIn('solid_node.motion.ports',
                              str(raised.exception))

    def test_a_node_class_is_still_a_node_export(self):
        from solid_node.node import AssemblyNode

        self.assertTrue(issubclass(AssemblyNode, object))


PORT_SNIPPET = '''
from solid2 import cube
from solid_node.motion.ports import RotationalPort
from solid_node.node import Solid2Node


class Shaft(Solid2Node):
    angle = RotationalPort(out=True, unit='deg')

    def render(self):
        return cube(1, center=True)



# Bind and read the port off the class descriptor without building the
# node: `Shaft()` would run the CAD lifecycle's `get_source_file()`,
# which has no real file to find in a probed snippet compiled from a
# string -- a limitation of the probe, not of the port. `__new__`
# skips `__init__` and reaches the same descriptor either way.
shaft = Shaft.__new__(Shaft)
shaft.angle.value = 30
assert shaft.angle.value == 30
'''


class ImportOrderTest(TestCase):
    """Either import order completes, and a port bound afterwards
    behaves identically -- design.md decision 2's load-order check, run
    for real rather than argued from the source."""

    def test_motion_ports_imported_first(self):
        result = probe(PORT_SNIPPET + "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)

    def test_node_internal_imported_first(self):
        result = probe('import solid_node.node.internal\n' +
                       PORT_SNIPPET + "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)


class MotionImportCostTest(TestCase):
    """`solid_node.motion` and its submodules stay as cheap to import as
    `solid_node.node` -- no CAD backend, no exact-geometry stack."""

    def test_the_empty_package_pulls_in_no_other_solid_node_module(self):
        """The package itself is still free. Neither submodule is:
        cycle 2 filled `joints` and cycle 3 filled `couplings`, and both
        cost what `solid_node.motion.ports` costs, because a joint owns
        a port and a relation relates two of them (see
        tests/test_joints.py and tests/test_couplings.py, which pin that
        equality)."""
        result = probe(
            'import solid_node.motion\n'
            'import sys\n'
            "solid_modules = sorted(\n"
            "    m for m in sys.modules\n"
            "    if m == 'solid_node' or m.startswith('solid_node.'))\n"
            'print(solid_modules)\n')
        self.assertEqual(result.status, 0, result.stderr)
        modules = eval(result.stdout.strip())
        self.assertEqual(modules, [
            'solid_node',
            'solid_node.motion',
        ])
        self.assertFalse(result.imported('cadquery'))
        self.assertFalse(result.imported('OCP'))

    def test_ports_pulls_no_cad_backend(self):
        result = probe('import solid_node.motion.ports\n' + "print('DONE')\n")
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        self.assertFalse(result.imported('cadquery'),
                         'importing solid_node.motion.ports imported cadquery')
        self.assertFalse(result.imported('OCP'),
                         'importing solid_node.motion.ports imported the '
                         'boundary-representation kernel')


class RunningEngineImportCostTest(TestCase):
    """The running engine costs nothing to a model that declares no
    running time (OpenSpec change ``run-owns-the-coordinates``).

    The compile step and the engine live under `solid_node.simulation`
    and are imported by `Sim.__init__` only when the root declares
    `Time.running()`; the running time base and the run-binder marker
    live in `solid_node.motion.ports`, which imports nothing new for
    them.
    """

    def test_a_looping_roots_simulation_imports_no_running_engine(self):
        result = probe(
            'from tests.running_project.machine import LoopingTrain\n'
            'from solid_node.simulation import Sim\n'
            'sim = Sim(LoopingTrain(), 0.1)\n'
            'sim.run(1.0)\n'
            "print('DONE')\n").check()
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        self.assertFalse(result.imported('solid_node.simulation.run'),
                         'a looping simulation imported the running engine')
        self.assertFalse(result.imported('solid_node.simulation.program'),
                         'a looping simulation imported the compile step')

    def test_ports_and_couplings_import_nothing_from_the_simulation_layer(self):
        for module in ('solid_node.motion.ports', 'solid_node.motion.couplings'):
            with self.subTest(module=module):
                result = probe(f'import {module}\n' + "print('DONE')\n").check()
                self.assertFalse(result.imported('solid_node.simulation'),
                                 f'{module} imported the simulation layer')

    def test_a_running_roots_simulation_imports_the_engine(self):
        result = probe(
            'from tests.running_project.machine import Train\n'
            'from solid_node.simulation import Sim\n'
            'sim = Sim(Train(), 0.1)\n'
            "print('DONE')\n").check()
        self.assertEqual(result.stdout.strip(), 'DONE', result.stderr)
        self.assertTrue(result.imported('solid_node.simulation.run'))
        self.assertTrue(result.imported('solid_node.simulation.program'))
        self.assertFalse(result.imported('cadquery'))
        self.assertFalse(result.imported('OCP'))
