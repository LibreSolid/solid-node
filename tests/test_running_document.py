# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Schema v5: a running root's document publishes the compiled program.

OpenSpec change ``publish-the-mechanical-program``, cycle 4 of the
open-run campaign. Cycles 1 to 3 built a machine that runs in Python and
nothing of it reached the browser: a running root's document was
BYTE-IDENTICAL to an untimed root's, so its pose expressions were the law
evaluated ABSOLUTELY at the driver values -- the reading the whole
campaign exists to replace.

Under version 5 the document carries two new things and one changed rule.
`program` is what COMPILE TIME decided about the machine: the coordinate
table with each bank id's kind, rest value, unit and domain, the
intermediates, the edges in program order with their expressions and jump
plans, the spans, the candidate table, the identity, the clock name and
the algorithm's limits. The poses name BANK IDS, because a committed bank
is what poses the geometry. And the instructions table publishes both
forms, which versions 2 to 4 may not.

An untimed or looping root's document is unchanged in every byte, which
`ByteIdentityTest` pins against documents captured from the cycle's base
commit rather than against a re-derivation.
"""

import json
import os
import shutil
import tempfile

from solid_node.core.builder import Builder
from solid_node.core.export import export_node
from solid_node.core.expressions import parse
from solid_node.core.serializer import (
    DOCUMENT_FORMAT, drivers_table, instructions_table, serialize_node,
    symbolic_document,
)
from solid_node.expression_graph import postorder
from solid_node.motion.ports import get_coordinate
from solid_node.simulation import Sim
from solid_node.simulation.enumeration import bind_declared_defaults
from solid_node.simulation.program import (_BISECTION_ROUNDS,
                                           _CROSSING_TOLERANCE,
                                           _MAX_CROSSINGS, _SUBDIVISIONS)
from solid_node.simulation.run import _TOLERANCE

from .base import BaseNodeTest
from .running_project.machine import (Clocked, ClockedBody, Derived, Gauged,
                                      Guarded, LoopingTrain, Ratchet,
                                      Remainder, Sixbound, Sixfree,
                                      StoppedDifferential, Swept, ThreeCarries,
                                      Train, TrainBody, Window, Wired)

BASE_DOCUMENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'base_documents')


def document(node):
    """The document a producer assembles for `node`, minus the two keys
    a producer owns: the model paths it resolves, and `pieces`.

    The sequence is `export_node`'s and `_write_viewer_snapshot`'s, called
    here directly so the schema can be read without building an artifact.
    """
    from solid_node.core.serializer import compiled_program, document_body

    program, initial = compiled_program(node)
    with symbolic_document(node) as (declarations, instructions):
        root = serialize_node(node, lambda rigid: rigid.name,
                              graph_values=True)
        drivers = drivers_table(declarations)
        events = instructions_table(instructions, running=program is not None)
    body = document_body(node, root, drivers, events, program, initial)
    body['root'] = root
    return body


def bound(node, prepared=None):
    """`node` with its declared defaults bound, ready to serialize."""
    bind_declared_defaults(node)
    return node


def operations_of(document, *path):
    node = document['root']
    for name in path:
        node = next(child for child in node['children']
                    if child['name'] == name)
    return node['operations']


def resolved(document, text):
    """`text` with every bindings entry substituted, so a test can read
    what an expression says without walking the table by hand."""
    table = {entry['name']: entry['expression']
             for entry in document.get('bindings', ())}
    changed = True
    while changed:
        changed = False
        rewritten = []
        for token in _tokens(text):
            if token in table:
                rewritten.append(f'({table[token]})')
                changed = True
            else:
                rewritten.append(token)
        text = ''.join(rewritten)
    return text


def _tokens(text):
    token = ''
    for character in text:
        if character.isalnum() or character in '_$.':
            token += character
        else:
            if token:
                yield token
                token = ''
            yield character
    if token:
        yield token


def free_names_of(text):
    """Every free name an expression reads, off the document's own
    parser."""
    return {item.text for item in postorder([parse(text)])
            if item.kind == 'name'}


def names_in(document):
    """Every free name every operation and `params` expression of the
    document's tree reads."""
    found = set()

    def visit(node):
        for operation in node['operations']:
            if operation[0] == 'r':
                found.update(free_names_of(operation[1]))
            else:
                for component in operation[1]:
                    found.update(free_names_of(component))
        if 'flexible' in node:
            for expression in node['flexible']['params'].values():
                found.update(free_names_of(expression))
        for child in node.get('children', ()):
            visit(child)

    visit(document['root'])
    return found


class VersionTest(BaseNodeTest):
    """(1) The version is a property of the ROOT'S DECLARATION."""

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.mkdtemp(prefix='solid-running-document-')
        self.addCleanup(shutil.rmtree, self.temporary, ignore_errors=True)

    def exported(self, node):
        bind_declared_defaults(node)
        output = os.path.join(self.temporary, 'export')
        export_node(node, output, widget=False)
        with open(os.path.join(output, 'manifest.json')) as handle:
            return json.load(handle)

    def built(self, node):
        bind_declared_defaults(node)
        build_dir = os.path.join(self.temporary, 'build')
        os.makedirs(build_dir, exist_ok=True)
        node.assemble()
        node.build_stls()
        builder = Builder('model.py', build_dir=build_dir, watch=False)
        builder.node = node
        builder._write_viewer_snapshot()
        with open(os.path.join(build_dir, 'viewer.json')) as handle:
            return json.load(handle)

    def test_a_running_export_declares_version_five(self):
        manifest = self.exported(Train())
        self.assertEqual(manifest['version'], 5)
        self.assertIn('program', manifest)

    def test_a_running_build_declares_version_five(self):
        published = self.built(Train())
        self.assertEqual(published['version'], 5)
        self.assertIn('program', published)

    def test_an_untimed_document_carries_no_program(self):
        self.assertNotIn('program', document(bound(TrainBody())))
        self.assertNotIn('program', document(bound(LoopingTrain())))

    def test_a_running_root_with_nothing_shared_is_still_version_five(self):
        """The ladder below 5 is content-derived; 5 is not."""
        published = document(bound(Window()))
        self.assertEqual(published['version'], 5)


class InstructionTableTest(BaseNodeTest):
    """(1.3, 1.4, 6.2) Both forms under 5, and neither change under 4."""

    def test_a_running_document_publishes_both_forms(self):
        table = document(bound(Train()))['instructions']
        self.assertEqual(sorted(table), ['Advance', 'Park', 'Wind'])
        self.assertEqual(table['Park'], {'targets': {'crank': 40.0},
                                         'duration': 0.5})
        self.assertEqual(table['Advance'], {'by': {'crank': 10.0},
                                            'duration': 0.5})
        self.assertEqual(table['Wind'], {'by': {'crank': 10.0, 'lever': 5.0},
                                         'duration': 0.5})
        for name, entry in table.items():
            self.assertEqual(('targets' in entry) + ('by' in entry), 1, name)

    def test_an_untimed_document_still_omits_a_relative_instruction(self):
        table = document(bound(TrainBody()))['instructions']
        self.assertEqual(sorted(table), ['Park'])
        self.assertEqual(table['Park'], {'targets': {'crank': 40.0},
                                         'duration': 0.5})


class ByteIdentityTest(BaseNodeTest):
    """(1.2, 10.2) Every document but a running one is unchanged.

    Compared against files captured from the cycle's base commit
    (`tests/base_documents/`), not against a second derivation of the
    same code. One field is normalized on both sides: each node's
    `mtime`, which is its SOURCE FILE's modification time and therefore a
    property of the checkout rather than of the document.
    """

    trees = {
        'driverless': 'tests.deep_project.third_level:ThirdLevel',
        'drivers': 'tests.meta_project.machine:Machine',
        'flexible': 'tests.flexible_project.spring:Engine',
        'sharing': 'tests.expression_project.sharing:SharedValueTree',
        'looping': 'tests.running_project.machine:LoopingTrain',
        'untimed_train': 'tests.running_project.machine:TrainBody',
    }

    def factory(self, reference):
        from importlib import import_module
        module, _colon, name = reference.partition(':')
        return getattr(import_module(module), name)

    def normalized(self, root):
        root['mtime'] = None
        for child in root.get('children', ()):
            self.normalized(child)
        return root

    def test_every_untimed_document_is_unchanged_in_every_byte(self):
        for name, reference in sorted(self.trees.items()):
            with self.subTest(tree=name):
                node = self.factory(reference)()
                bind_declared_defaults(node)
                published = document(node)
                self.normalized(published['root'])
                with open(os.path.join(BASE_DOCUMENTS,
                                       f'{name}.json')) as handle:
                    expected = handle.read()
                self.assertEqual(json.dumps(published, indent=2) + '\n',
                                 expected)


class PoseTest(BaseNodeTest):
    """(2) A committed bank poses the geometry."""

    def test_a_joints_placement_is_its_coordinates_name(self):
        published = document(bound(Train()))
        self.assertEqual(operations_of(published, 'first'),
                         [['r', 'first.turn', [0, 0, 1]]])

    def test_a_plain_port_follows_the_bank(self):
        published = document(bound(Gauged()))
        rotation = operations_of(published, 'gauge', 'hand')[0]
        self.assertEqual(rotation[0], 'r')
        self.assertEqual(free_names_of(resolved(published, rotation[1])),
                         {'first.turn'})

    def test_a_guarded_rest_default_is_published_as_its_own_id(self):
        published = document(bound(Guarded()))
        self.assertEqual(operations_of(published, 'slide')[0],
                         ['t', ['slide.travel', '0', '0']])

    def test_a_free_joint_reads_its_six_coordinate_ids(self):
        published = document(bound(Sixbound()))
        operations = operations_of(published, 'chassis')
        names = set()
        for operation in operations:
            if operation[0] == 'r':
                names |= free_names_of(operation[1])
            else:
                for component in operation[1]:
                    names |= free_names_of(component)
        self.assertTrue({'chassis.pose.yaw', 'chassis.pose.pitch',
                         'chassis.pose.roll', 'chassis.pose.x',
                         'chassis.pose.y', 'chassis.pose.z'} <= names,
                        sorted(names))

    def test_a_flexible_part_follows_the_bank(self):
        from .running_project.flexible import Valvegear

        published = document(bound(Valvegear()))

        def find(node, name):
            if node['name'] == name:
                return node
            for child in node.get('children', ()):
                found = find(child, name)
                if found is not None:
                    return found
            return None

        spring = find(published['root'], 'spring')
        self.assertIsNotNone(spring)
        self.assertIn('flexible', spring)
        self.assertEqual(spring['flexible']['tech'], 'molejo')
        height = spring['flexible']['params']['height']
        self.assertEqual(free_names_of(resolved(published, height)),
                         {'lifter.travel'})

    def test_every_free_name_the_document_reads_is_declared(self):
        for factory in (Train, ThreeCarries, Sixbound, Guarded, Gauged):
            with self.subTest(machine=factory.__name__):
                published = document(bound(factory()))
                declared = (set(published['drivers'])
                            | set(published['program']['coordinates'])
                            | set(published['program']['intermediates'])
                            | {published['program']['clock']})
                table = {entry['name']
                         for entry in published.get('bindings', ())}
                names = names_in(published)
                self.assertTrue(names <= declared | table, sorted(names))
                # And once the table is resolved away, nothing but the
                # declared ids is left.
                left = set()
                for name in names:
                    left |= free_names_of(resolved(published, name))
                self.assertTrue(left <= declared, sorted(left - declared))

    def test_the_tree_is_left_as_it_was_found(self):
        node = Train()
        bind_declared_defaults(node)
        node.set_state(crank=10.0, lever=110.0, time=0.0)
        before = {name: get_coordinate(owner, coordinate)._value
                  for name, (owner, coordinate)
                  in _coordinates(node).items()}
        binders = {name: get_coordinate(owner, coordinate).binder
                   for name, (owner, coordinate) in _coordinates(node).items()}

        document(node)

        after = {name: get_coordinate(owner, coordinate)._value
                 for name, (owner, coordinate) in _coordinates(node).items()}
        self.assertEqual(after, before)
        self.assertEqual({name: get_coordinate(owner, coordinate).binder
                          for name, (owner, coordinate)
                          in _coordinates(node).items()}, binders)
        self.assertEqual(operations_of(document(node), 'first'),
                         [['r', 'first.turn', [0, 0, 1]]])


def _coordinates(node):
    from solid_node.simulation.program import qualified_coordinates

    return qualified_coordinates(node)


class LiveRunTest(BaseNodeTest):
    """(2.0c) Publication over a tree a live run owns leaves no trace."""

    def test_publishing_mid_move_does_not_disturb_the_run(self):
        node = Train()
        sim = Sim(node, 0.1)
        command = sim.move('crank', by=20.0, duration=1.0)
        sim.run(0.5)
        state = sim.state
        tick = sim.tick
        admitted = command.admitted
        binders = {name: get_coordinate(owner, coordinate).binder
                   for name, (owner, coordinate) in _coordinates(node).items()}

        published = document(node)

        self.assertEqual(published['version'], 5)
        self.assertEqual(sim.state, state)
        self.assertEqual(sim.tick, tick)
        self.assertEqual(command.admitted, admitted)
        self.assertEqual(command.status, 'active')
        self.assertEqual({name: get_coordinate(owner, coordinate).binder
                          for name, (owner, coordinate)
                          in _coordinates(node).items()}, binders)

        sim.run(0.5)
        self.assertEqual(command.status, 'completed')
        self.assertAlmostEqual(sim.state['crank'], 20.0)
        self.assertAlmostEqual(sim.state['first.turn'], 40.0)


class CoordinateTableTest(BaseNodeTest):
    """(3.1, 3.2, 2.0b) The bank, published."""

    def test_the_table_is_the_bank_with_kinds_units_and_rest_values(self):
        node = Train()
        bind_declared_defaults(node)
        published = document(node)
        table = published['program']['coordinates']
        initial = dict(Sim(Train(), 0.1).initial.bank)
        self.assertEqual(sorted(table), sorted(initial))
        self.assertEqual([name for name, entry in table.items()
                          if entry['kind'] == 'input'],
                         ['crank', 'lever'])
        self.assertEqual(list(table)[:2], ['crank', 'lever'])
        for name, entry in table.items():
            with self.subTest(coordinate=name):
                self.assertEqual(entry['initial'], initial[name])
        self.assertEqual(table['first.turn']['unit'], 'deg')
        self.assertEqual(table['slide.travel']['unit'], 'mm')
        self.assertNotIn('unit', table['crank'])

    def test_the_intermediates_are_the_plain_ports_and_nothing_else(self):
        published = document(bound(Train()))
        self.assertEqual(published['program']['intermediates'],
                         ['wheel.turn'])

    def test_the_drivers_table_is_the_one_declaration(self):
        published = document(bound(Train()))
        inputs = {name for name, entry
                  in published['program']['coordinates'].items()
                  if entry['kind'] == 'input'}
        self.assertEqual(inputs, set(published['drivers']))
        for name in inputs:
            entry = published['program']['coordinates'][name]
            self.assertEqual(set(entry) & {'unit', 'dtype', 'scale',
                                           'range', 'default'}, set())

    def test_every_entry_carries_its_domain(self):
        published = document(bound(Train()))
        table = published['program']['coordinates']
        self.assertEqual(table['first.turn']['domain'], 'rotational')
        self.assertEqual(table['spindle']['domain'], 'rotational')
        self.assertEqual(table['slide.travel']['domain'], 'translational')
        for name, entry in table.items():
            self.assertIn('domain', entry, name)

    def test_a_prismatic_fixture_reads_translational(self):
        published = document(bound(Swept()))
        table = published['program']['coordinates']
        self.assertEqual(table['rack.travel']['domain'], 'translational')
        self.assertEqual(table['wheel.turn']['domain'], 'rotational')

    def test_no_dt_is_published(self):
        published = document(bound(Train()))
        self.assertNotIn('dt', published['program'])
        self.assertNotIn('dt', published)


class EdgeTableTest(BaseNodeTest):
    """(3.3, 3.4, 3.5) The edges, in program order, with their plans."""

    def edges(self, factory):
        node = factory()
        bind_declared_defaults(node)
        published = document(node)
        return published, Sim(factory(), 0.1).program

    def test_the_edges_match_the_compiled_program_one_for_one(self):
        published, program = self.edges(Train)
        edges = published['program']['edges']
        self.assertEqual(len(edges), len(program.edges))
        for entry, edge in zip(edges, program.edges):
            with self.subTest(edge=edge.description):
                self.assertEqual(entry['kind'], edge.kind)
                self.assertEqual(entry['needs'],
                                 [program.nodes[key].name
                                  for key in edge.needs])
                self.assertEqual(entry['gives'],
                                 [program.nodes[key].name
                                  for key in edge.gives])
                self.assertEqual(entry['description'], edge.description)
                self.assertEqual(entry['stated_by'], edge.stated_by)
                if edge.kind == 'law':
                    self.assertEqual(entry['affine'], list(edge.affine))
                    self.assertEqual(len(entry['expressions']),
                                     len(edge.gives))
                    self.assertEqual(len(entry['plans']), len(edge.gives))

    def test_a_wiring_publishes_its_factor(self):
        published, program = self.edges(Wired)
        wirings = [entry for entry in published['program']['edges']
                   if entry['kind'] == 'wiring']
        self.assertEqual(len(wirings), 1)
        self.assertEqual(wirings[0]['needs'], ['relay'])
        self.assertEqual(wirings[0]['gives'], ['first.turn'])
        self.assertEqual(wirings[0]['factor'], 1.0)

    def test_a_formula_publishes_its_coefficients(self):
        published, program = self.edges(Derived)
        formulas = [entry for entry in published['program']['edges']
                    if entry['kind'] == 'formula']
        self.assertEqual(len(formulas), 1)
        self.assertEqual(formulas[0]['needs'], ['wrist', 'tool'])
        self.assertEqual(formulas[0]['gives'], ['left'])
        self.assertEqual(formulas[0]['factors'], [1.0, 2.0])
        self.assertEqual(formulas[0]['constant'], 0.0)
        self.assertEqual(formulas[0]['slot'], 'left')

    def test_a_check_publishes_what_it_predicts(self):
        published, program = self.edges(StoppedDifferential)
        checks = [entry for entry in published['program']['edges']
                  if entry['kind'] == 'check']
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]['gives'], [])
        self.assertEqual(checks[0]['needs'], ['left', 'wrist', 'tool'])
        self.assertEqual(checks[0]['factors'], [0.0, 1.0, 2.0])
        self.assertEqual(checks[0]['slot'], 'left')

    def test_a_jump_publishes_its_plan(self):
        published, program = self.edges(Window)
        edge = published['program']['edges'][0]
        self.assertEqual(edge['affine'], [False])
        plan = edge['plans'][0]
        self.assertEqual(len(plan['jumps']), 1)
        jump = plan['jumps'][0]
        self.assertEqual(jump['primitive'], 'floor')
        self.assertTrue(jump['affine'])
        self.assertIn(jump['name'], plan['skeleton'])
        self.assertEqual(free_names_of(resolved(published, jump['level'])),
                         {'crank'})

    def test_a_remainder_is_written_out_in_the_skeleton(self):
        published, program = self.edges(Remainder)
        plan = published['program']['edges'][0]['plans'][0]
        jump = plan['jumps'][0]
        self.assertEqual(jump['primitive'], '%')
        skeleton = resolved(published, plan['skeleton'])
        self.assertIn(jump['name'], skeleton)
        self.assertIn('-', skeleton)

    def test_three_laws_mint_three_distinct_placeholders(self):
        published, program = self.edges(ThreeCarries)
        plans = [plan for entry in published['program']['edges']
                 if entry['kind'] == 'law'
                 for plan in entry.get('plans', ()) if plan is not None]
        self.assertEqual(len(plans), 3)
        names = [jump['name'] for plan in plans for jump in plan['jumps']]
        self.assertEqual(len(names), 3)
        self.assertEqual(len(set(names)), 3)
        table = {entry['name']: entry['expression']
                 for entry in published.get('bindings', ())}
        for name, expression in table.items():
            with self.subTest(binding=name):
                reads = free_names_of(expression) & set(names)
                self.assertLessEqual(len(reads), 1, expression)
        for plan, expected in zip(plans, names):
            self.assertEqual(
                free_names_of(resolved(published, plan['skeleton']))
                & set(names), {expected})


class SpansAndLimitsTest(BaseNodeTest):
    """(3.6) Spans, sources, identity and limits."""

    def test_an_expression_bound_travels_as_an_expression(self):
        published = document(bound(Ratchet()))
        spans = published['program']['spans']
        self.assertEqual(sorted(spans), ['wheel.turn'])
        self.assertIsNone(spans['wheel.turn']['high'])
        self.assertEqual(
            free_names_of(resolved(published,
                                   spans['wheel.turn']['low']['expression'])),
            {'wheel.turn'})

    def test_a_numeric_bound_travels_as_a_number(self):
        published = document(bound(Swept()))
        spans = published['program']['spans']
        self.assertEqual(spans['rack.travel']['high'], 50.0)
        self.assertIsNone(spans['rack.travel']['low'])

    def test_the_candidate_table_and_the_identity_are_the_programs(self):
        published = document(bound(Train()))
        program = Sim(Train(), 0.1).program
        self.assertEqual(
            published['program']['sources'],
            {program.nodes[key].name: sorted(names)
             for key, names in program.sources.items()})
        self.assertEqual(published['program']['identity'], program.identity)

    def test_the_limits_are_the_constants_the_algorithm_declares(self):
        published = document(bound(Train()))
        self.assertEqual(published['program']['limits'], {
            'crossing_tolerance': _CROSSING_TOLERANCE,
            'subdivisions': _SUBDIVISIONS,
            'bisection_rounds': _BISECTION_ROUNDS,
            'max_crossings': _MAX_CROSSINGS,
            'agreement': _TOLERANCE,
        })


class SharingTest(BaseNodeTest):
    """(3.7, 3.8) One bindings table, one order, twice the same bytes."""

    def test_no_program_expression_carries_producer_local_sharing(self):
        for factory in (Train, Window, ThreeCarries, Ratchet):
            with self.subTest(machine=factory.__name__):
                published = document(bound(factory()))
                text = json.dumps(published['program'])
                self.assertNotIn('let(', text)
                for entry in published.get('bindings', ()):
                    self.assertNotIn('let(', entry['expression'])

    def test_a_law_and_its_plan_share_one_binding(self):
        published = document(bound(Window()))
        edge = published['program']['edges'][0]
        level = edge['plans'][0]['jumps'][0]['level']
        self.assertIn(level, [entry['name']
                              for entry in published['bindings']])
        self.assertIn(level, edge['expressions'][0])

    def test_publishing_twice_is_byte_identical(self):
        first = json.dumps(document(bound(ThreeCarries())), indent=2)
        second = json.dumps(document(bound(ThreeCarries())), indent=2)
        self.assertEqual(first, second)


class ClockTest(BaseNodeTest):
    """(4.1) `time` under a running root leaves the document."""

    def test_a_running_document_carries_no_animation_variable(self):
        published = document(bound(Clocked()))
        self.assertEqual(published['program']['clock'], 'time')
        self.assertNotIn('$t', json.dumps(published))
        self.assertIn('time', names_in(published))

    def test_an_untimed_document_still_carries_the_animation_variable(self):
        published = document(bound(ClockedBody()))
        self.assertIn('$t', json.dumps(published))

    def test_a_running_document_publishes_no_loop(self):
        published = document(bound(Train()))
        self.assertEqual(published['animation'], {'fps': 30, 'frames': 360})


class RefusalTest(BaseNodeTest):
    """(3.9) What publication refuses."""

    def test_a_root_the_run_refuses_cannot_be_published(self):
        """The program a document publishes is the program the run
        executes, so a root the run cannot be constructed over has none
        to publish, and publication says exactly what the run says."""
        node = Sixfree()
        bind_declared_defaults(node)
        with self.assertRaises(ValueError) as raised:
            document(node)
        self.assertIn('chassis.pose.pitch', str(raised.exception))
        self.assertIn('rest render leaves', str(raised.exception))

    def test_an_id_that_cannot_be_qualified_is_refused(self):
        """A node the walk could not qualify carries the
        `<ClassName>.<name>` FALLBACK and says so; publication refuses
        it, because that name is not unique across two instances of one
        class. Reached at the seam: nothing in the framework's suite or
        in any surveyed project produces an unlinked end today, which is
        what the refusal keeps true.
        """
        from solid_node.core.serializer import compiled_program
        from solid_node.simulation import program as program_module

        node = Train()
        bind_declared_defaults(node)
        program, initial = compiled_program(node)
        for entry in program.nodes.values():
            if entry.kind == 'intermediate':
                entry.name = 'Wheel.turn'
                entry.qualified = False
                break
        else:
            self.fail('the fixture has no intermediate to unqualify')
        with self.assertRaises(program_module.UnsupportedLaw) as raised:
            program.published(initial)
        self.assertIn('Wheel.turn', str(raised.exception))
        self.assertIn('class name', str(raised.exception))


class AcceptanceShapeTest(BaseNodeTest):
    """(3.10) The acceptance project's own shape, pinned HERE.

    The Pascaline module lives in another repository, and the framework's
    suite may not depend on it -- so what the module's own document is
    asserted to be is a PROBE, run against the module and pasted into the
    change's `evidence.md`. What is pinned here is the same shape, built
    from the framework's own fixtures: a chain of registers, one carry law
    per column each carrying a single `floor`, every register's angle
    published as its own coordinate's name, and every coordinate
    rotational.
    """

    def setUp(self):
        super().setUp()
        self.published = document(bound(ThreeCarries()))

    def test_every_register_is_posed_by_its_own_coordinate(self):
        for column in ('units', 'tens', 'hundreds', 'trail'):
            with self.subTest(column=column):
                self.assertEqual(operations_of(self.published, column)[0],
                                 ['r', f'{column}.turn', [0, 0, 1]])

    def test_the_carry_laws_are_in_the_program_and_nowhere_else(self):
        text = json.dumps(self.published['root'])
        self.assertNotIn('floor', text)
        plans = [plan for edge in self.published['program']['edges']
                 for plan in edge.get('plans', ()) if plan is not None]
        self.assertEqual([jump['primitive'] for plan in plans
                          for jump in plan['jumps']],
                         ['floor', 'floor', 'floor'])

    def test_every_coordinate_is_rotational_at_its_rest_value(self):
        table = self.published['program']['coordinates']
        initial = dict(Sim(ThreeCarries(), 0.1).initial.bank)
        for name, entry in table.items():
            with self.subTest(coordinate=name):
                self.assertEqual(entry['initial'], initial[name])
                if entry['kind'] == 'coordinate':
                    self.assertEqual(entry['domain'], 'rotational')
                    self.assertEqual(entry['unit'], 'deg')

    def test_the_dials_reach_the_registers_through_the_program(self):
        sources = self.published['program']['sources']
        self.assertEqual(sources['units.turn'], ['units_entry'])
        self.assertEqual(sources['tens.turn'],
                         ['tens_entry', 'units_entry'])
        self.assertEqual(sources['hundreds.turn'],
                         ['hundreds_entry', 'tens_entry', 'units_entry'])
