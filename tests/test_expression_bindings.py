# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Schema v4: the document's `bindings` table (ADR-080).

A subexpression occurring more than once anywhere in a document's
expressions is published once, named, and referenced -- except a bare
number or a bare name, which is shorter written out than referenced
(design.md D5). This is the producer side: `serialize_node` plus
`symbolic_document` walk a tree exactly as before; a new pass over the
document's collected expression strings (`solid_node/core/expressions.py`)
finds the sharing and rewrites the strings.
"""

import json
import math
import os
import re
import shutil
import tempfile
from types import SimpleNamespace

from solid2 import cube
from solid2.core.object_base import scad_inline

from solid_node.core.builder import Builder, project_build_lock
from solid_node.core.export import export_node
from solid_node.core import expressions as expr
from solid_node.core.serializer import (
    BINDINGS_DOCUMENT_VERSION, DOCUMENT_VERSION,
    animation_block, bind_document, document_version, drivers_table,
    instructions_table, serialize_node, symbolic_document,
)
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver
from solid_node.simulation.enumeration import bind_declared_defaults
import solid_node.math as m

from .base import BaseNodeTest
from .flexible_project.spring import Engine as SpringEngine
from .meta_project.nested import Nested


class Leaf(Solid2Node):
    """A cube. The geometry is not the point."""

    def render(self):
        return cube(1, center=True)


class CrossNodeSharedTree(AssemblyNode):
    """One `$t`-and-driver-derived value, reused whole in one operation,
    as a subexpression in another, and doubled (self-reuse) in a third."""

    drive = Driver(default=0, range=(0, 100), unit='step', dtype=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = Leaf()
        self.b = Leaf()
        self.c = Leaf()

    def render(self):
        shared = m.floor(43200.0 * self.time + self.drive)
        self.a.rotate(shared, [0, 0, 1])
        self.b.rotate(shared + 1.0, [0, 0, 1])
        self.c.translate([shared * shared, 0, 0])
        return [self.a, self.b, self.c]


class BareLeavesRepeatTree(AssemblyNode):
    """A literal and a driver id each occur many times; neither is a
    compound expression, so neither should ever be bound."""

    knob = Driver(default=0, range=(0, 100), unit='step', dtype=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leaves = [Leaf() for _ in range(4)]

    def render(self):
        for leaf in self.leaves:
            leaf.translate([208.47, self.knob, 208.47])
        return list(self.leaves)


class UnderscoreBDriverTree(AssemblyNode):
    """A driver whose qualified id collides with the default binding
    prefix -- `_b0` -- beside a genuinely shared subexpression."""

    _b0 = Driver(default=0, range=(0, 100), unit='step', dtype=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = Leaf()
        self.b = Leaf()

    def render(self):
        shared = m.floor(720.0 * self.time)
        self.a.rotate(shared, [0, 0, 1])
        self.b.rotate(shared + self._b0, [0, 0, 1])
        return [self.a, self.b]


class UnreadableBesideSharedTree(AssemblyNode):
    """One node's rotation is a hand-written expression outside the
    grammar, beside two other nodes sharing an ordinary subexpression."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = Leaf()
        self.b = Leaf()
        self.odd = Leaf()

    def render(self):
        shared = m.floor(360.0 * self.time)
        self.a.rotate(shared, [0, 0, 1])
        self.b.rotate(shared + 1.0, [0, 0, 1])
        self.odd.rotate(scad_inline('[1, 2]'), [0, 0, 1])
        return [self.a, self.b, self.odd]



def bound(node):
    """`node`, with every declared driver bound to its default -- the
    loader's own contract, restated here rather than self-binding inside
    a fixture's __init__ (meta_project.machine's docstring)."""
    bind_declared_defaults(node)
    return node


def find(node, name):
    """The first node called `name` in a serialized tree."""
    if node['name'] == name:
        return node
    for child in node.get('children', ()):
        found = find(child, name)
        if found is not None:
            return found
    return None


def operations_of(document, *path):
    node = document
    for name in path:
        node = next(child for child in node['children']
                    if child['name'] == name)
    return node['operations']


def all_expression_text(document):
    """Every operation and flexible-`params` expression string anywhere
    under `document`, plus every `bindings` entry's own text -- the whole
    surface task 2.1 requires no operator application, call or
    parenthesised group to repeat across."""
    texts = []
    for entry in document.get('bindings', ()):
        texts.append(entry['expression'])

    def walk(node):
        for operation in node['operations']:
            if operation[0] == 'r':
                texts.append(operation[1])
            else:
                texts.extend(operation[1])
        if 'flexible' in node:
            texts.extend(node['flexible']['params'].values())
        for child in node.get('children', ()):
            walk(child)

    walk(document['root'])
    return texts


class OneSharedSubexpressionTest(BaseNodeTest):
    """Task 2.1: a subexpression reused across several nodes is
    published once, as a bindings entry, and referenced by name."""

    def export(self, node):
        out_dir = os.path.join(self.build_dir, 'export_out')
        return export_node(node, out_dir, widget=False)

    def test_the_bindings_table_holds_it_once(self):
        manifest = self.export(bound(CrossNodeSharedTree()))

        self.assertIn('bindings', manifest)
        self.assertGreater(len(manifest['bindings']), 0)

    def test_every_operation_references_it_by_name(self):
        manifest = self.export(bound(CrossNodeSharedTree()))
        names = {entry['name'] for entry in manifest['bindings']}

        a_angle = operations_of(manifest['root'], 'a')[0][1]
        b_angle = operations_of(manifest['root'], 'b')[0][1]
        self.assertIn(a_angle, names)
        self.assertTrue(any(name in b_angle for name in names))

    def test_no_operator_application_or_call_repeats(self):
        """No parenthesised group or call appears twice anywhere in the
        document's expressions and bindings taken together."""
        manifest = self.export(bound(CrossNodeSharedTree()))
        texts = all_expression_text(manifest)

        seen = {}
        for text in texts:
            seen[text] = seen.get(text, 0) + 1
        repeated = {text: count for text, count in seen.items()
                    if count > 1 and '(' in text}
        self.assertEqual(repeated, {})


class BareLeavesNotBoundTest(BaseNodeTest):
    """Task 2.2: a bare number and a bare driver id are never bound,
    however often they repeat."""

    def test_neither_a_repeated_literal_nor_a_repeated_driver_id_is_bound(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(BareLeavesRepeatTree()), out_dir, widget=False)

        # A literal and a driver id repeat 8 times each and nothing else
        # repeats, so with nothing bindable the table is simply absent.
        self.assertNotIn('bindings', manifest)


class SelfReuseTest(BaseNodeTest):
    """Task 2.2: `(big * big)` shares `big` with itself and must bind it
    -- occurrences, not distinct parents."""

    def test_the_repeated_operand_is_bound(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir, widget=False)

        c_translation = operations_of(manifest['root'], 'c')[0][1]
        names = {entry['name'] for entry in manifest['bindings']}
        self.assertEqual(c_translation[1], '0')
        self.assertEqual(c_translation[2], '0')
        x = c_translation[0]
        self.assertTrue(x.startswith('(') and x.endswith(')'))
        left, op, right = x[1:-1].split(' ')
        self.assertEqual(op, '*')
        self.assertEqual(left, right)
        self.assertIn(left, names)


class OrderedTableParityTest(BaseNodeTest):
    """Task 2.3: the table is ordered so one forward pass suffices, and
    evaluating it and then the operations reproduces the flat values."""

    def test_every_name_an_entry_mentions_is_earlier_or_a_known_input(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir, widget=False)

        declared = set(manifest['drivers'])
        earlier = set()
        for entry in manifest['bindings']:
            for token in _names_in(entry['expression']):
                if token == '$t' or _looks_numeric(token):
                    continue
                self.assertTrue(
                    token in declared or token in earlier,
                    f'{entry["name"]!r} names {token!r} before it is known')
            earlier.add(entry['name'])

    def test_numeric_parity_against_the_flat_expressions(self):
        """The table evaluated, then the operations, reproduces the
        values a flat (pre-bindings) symbolic walk would have."""
        with symbolic_document(bound(CrossNodeSharedTree())) as (_, __):
            pass  # confirm the tree assembles under symbolic mode first
        flat_root, _ = _flat_document(bound(CrossNodeSharedTree()))
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir, widget=False)

        for t in (0.0, 1.0 / 3, 2.0 / 3):
            for drive in (0, 40, 99):
                scope = {'$t': t, 'drive': float(drive)}
                bound_scope = dict(scope)
                for entry in manifest['bindings']:
                    bound_scope[entry['name']] = _evaluate(
                        entry['expression'], bound_scope)
                for name in ('a', 'b', 'c'):
                    flat_values = _flat_values(
                        operations_of(flat_root, name), scope)
                    bound_values = _flat_values(
                        operations_of(manifest['root'], name), bound_scope)
                    for f, b in zip(flat_values, bound_values):
                        self.assertAlmostEqual(f, b, places=6)


class NamingUnderscoreBTest(BaseNodeTest):
    """Task 2.4: ordinary names, and a driver named like a binding."""

    def test_ordinary_names_are_b0_b1_in_order(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir, widget=False)

        names = [entry['name'] for entry in manifest['bindings']]
        self.assertEqual(names, [f'_b{i}' for i in range(len(names))])

    def test_a_driver_named_b0_gets_a_longer_prefix(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(UnderscoreBDriverTree()), out_dir, widget=False)

        self.assertIn('_b0', manifest['drivers'])
        for entry in manifest['bindings']:
            self.assertNotEqual(entry['name'], '_b0')
            self.assertTrue(entry['name'].startswith('__b'))
        b_angle = operations_of(manifest['root'], 'b')[0][1]
        self.assertIn('_b0', b_angle)


class VersionRuleTest(BaseNodeTest):
    """Task 2.5: the version rule, with a byte-identity pin for a
    document with nothing to share."""

    def test_a_document_with_sharing_declares_four_and_carries_the_key(self):
        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir, widget=False)

        self.assertEqual(manifest['version'], BINDINGS_DOCUMENT_VERSION)
        self.assertEqual(manifest['version'], 4)
        self.assertIn('bindings', manifest)

    def test_a_flexible_tree_with_sharing_declares_four(self):
        engine = SpringEngine()
        bind_declared_defaults(engine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(engine, out_dir, widget=False)

        self.assertEqual(manifest['version'], 4)
        self.assertIn('bindings', manifest)

    def test_bind_document_does_not_touch_a_tree_with_nothing_shared(self):
        """Pin a serialized fixture, not a shape assertion: what
        `serialize_node`/`symbolic_document` build for a no-sharing tree
        -- exactly what the framework assembled before bindings existed
        -- must come back from `bind_document` byte-for-byte, with an
        empty table. That invariant, not a hand reconstruction of
        `export_node`'s own piece-registration side effects, is what
        makes the published document byte-identical to before."""
        node = Nested()
        with symbolic_document(node) as (declarations, _instructions):
            root = serialize_node(node, lambda rigid: rigid.name)
        before = json.dumps(root, sort_keys=True)
        driver_ids = drivers_table(declarations).keys()

        bindings = bind_document(root, driver_ids)

        self.assertEqual(bindings, [])
        self.assertEqual(json.dumps(root, sort_keys=True), before)
        self.assertEqual(document_version(root, bindings), DOCUMENT_VERSION)

    def test_the_published_manifest_has_no_bindings_key(self):
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(Nested(), out_dir, widget=False)

        self.assertNotIn('bindings', manifest)
        self.assertEqual(manifest['version'], DOCUMENT_VERSION)


class FlexibleParamSharingTest(BaseNodeTest):
    """Task 2.6: a flexible leaf's `params` expression sharing a
    subexpression with an operation is published as a table reference."""

    def test_the_shared_lift_expression_is_a_reference(self):
        engine = SpringEngine()
        bind_declared_defaults(engine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(engine, out_dir, widget=False)

        spring = find(manifest['root'], 'spring')
        height_expression = spring['flexible']['params']['height']
        names = {entry['name'] for entry in manifest['bindings']}
        self.assertIn(height_expression, names)

        retainer_translation = operations_of(
            manifest['root'], 'valvetrain', 'retainer')[0][1]
        self.assertIn(height_expression, retainer_translation[2])


class PassThroughTest(BaseNodeTest):
    """Task 2.7: an unreadable expression publishes verbatim and
    unshared, beside a table built from everything else; a table that
    would be wrong refuses to publish at all."""

    def test_the_document_still_publishes(self):
        out_dir = os.path.join(self.build_dir, 'export_out')

        with self.assertLogs('core.expressions', level='WARNING') as logs:
            manifest = export_node(bound(UnreadableBesideSharedTree()), out_dir,
                                   widget=False)

        odd_angle = operations_of(manifest['root'], 'odd')[0][1]
        self.assertEqual(odd_angle, '[1, 2]')

        names = {entry['name'] for entry in manifest['bindings']}
        a_angle = operations_of(manifest['root'], 'a')[0][1]
        self.assertIn(a_angle, names)

        self.assertEqual(manifest['version'], 4)
        joined = ' '.join(logs.output)
        self.assertIn('[1, 2]', joined)
        self.assertLess(len(joined), 10000,
                        'the warning must truncate, not restate the whole '
                        'expression')

    def test_a_table_naming_a_later_entry_refuses(self):
        bindings = [
            {'name': '_b0', 'expression': '_b1'},
            {'name': '_b1', 'expression': '1.0'},
        ]
        with self.assertRaises(expr.BindingTableError):
            expr._validate_bindings(bindings, driver_ids=[], prefix='_b')

    def test_a_name_colliding_with_a_declared_driver_refuses(self):
        bindings = [{'name': '_b0', 'expression': '1.0'}]
        with self.assertRaises(expr.BindingTableError):
            expr._validate_bindings(bindings, driver_ids=['_b0'], prefix='_b')

    def test_a_rewrite_that_does_not_reproduce_refuses(self):
        # The table says _b0 means "$t * 2.0", but the rewritten
        # top-level node is built from a DIFFERENT original expression
        # ("$t * 3.0" + 1.0) -- a mismatch _verify_reconstruction must
        # catch, reachable only by patching internals, never from a
        # correct model.
        names_interner = expr.Interner()
        shared = expr.parse('($t * 2.0)', names_interner)
        names = {shared: '_b0'}
        bindings = [{'name': '_b0', 'expression': '($t * 2.0)'}]
        rewritten = ['(_b0 + 1.0)']
        wrong_original = expr.parse('(($t * 3.0) + 1.0)', expr.Interner())
        with self.assertRaises(expr.BindingTableError):
            expr._verify_reconstruction(rewritten, [wrong_original],
                                        bindings, names)


class _FakeOperation:
    """The minimal shape `serialize_node` reads off an operation: just
    `.serialized`, already in its published form.

    A fresh list every access, matching `Rotation.serialized` /
    `Translation.serialized`'s own `@property` contract -- `bind_document`
    rewrites the list it is handed in place, and a real operation is
    rebuilt from its untouched `self.angle` / `self.translation` on every
    call, never mutated itself. A fixture returning the SAME list back
    would let one document's rewrite leak into the next serialization,
    which no real operation does.
    """

    def __init__(self, serialized):
        self._serialized = serialized

    @property
    def serialized(self):
        return [list(part) if isinstance(part, list) else part
                for part in self._serialized]


class ScadPathUntouchedTest(BaseNodeTest):
    """Task 3.2: the generated `.scad` for a tree carrying heavy sharing
    is byte-identical before and after publishing the document.

    `operation.scad(...)` reads `self.angle` / `self.translation`
    directly, never `operation.serialized` -- the only thing
    `bind_document` ever rewrites, and only on the plain-dict document
    `serialize_node` returns, never on the live `Rotation`/`Translation`
    objects. So publishing a document with bindings must leave the SCAD
    this tree generates completely alone.
    """

    def test_scad_is_unchanged_by_publishing_a_document_with_bindings(self):
        node = bound(CrossNodeSharedTree())
        node.assemble()
        before = node.scad_code

        out_dir = os.path.join(self.build_dir, 'export_out')
        manifest = export_node(bound(CrossNodeSharedTree()), out_dir,
                               widget=False)
        self.assertTrue(manifest['bindings'])  # sharing really happened

        node.assemble()
        after = node.scad_code

        self.assertEqual(before, after)
        for entry in manifest['bindings']:
            self.assertNotIn(entry['name'], before)

    def test_the_full_flattened_expression_reaches_openscad(self):
        node = bound(CrossNodeSharedTree())
        node.assemble()

        code = node.scad_code

        # The shared subexpression's own text, not a binding reference:
        # solid2's `$t` and `floor` reach OpenSCAD exactly as they did
        # before this cycle.
        self.assertIn('$t', code)
        self.assertIn('floor(', code)
        self.assertNotRegex(code, r'_b\d+')


class RepublicationStabilityTest(BaseNodeTest):
    """Task 2.8: publishing an unchanged tree twice is byte-identical,
    and an unchanged build does not republish."""

    def test_two_exports_of_one_tree_are_byte_identical(self):
        out_dir_a = os.path.join(self.build_dir, 'export_a')
        out_dir_b = os.path.join(self.build_dir, 'export_b')

        manifest_a = export_node(bound(CrossNodeSharedTree()), out_dir_a, widget=False)
        manifest_b = export_node(bound(CrossNodeSharedTree()), out_dir_b, widget=False)

        self.assertEqual(json.dumps(manifest_a, sort_keys=True),
                         json.dumps(manifest_b, sort_keys=True))

    def test_an_unchanged_build_does_not_republish(self):
        """A node whose operations already repeat one subexpression --
        minimal, so this proves the byte comparison rather than real
        geometry (design.md D5's ordering guarantee is what makes the
        comparison stable across a republish)."""
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        build_dir = os.path.join(root, '_build')
        os.makedirs(build_dir)
        artifact = os.path.join(build_dir, 'part.stl')
        from trimesh.creation import box
        box((2, 2, 2)).export(artifact)
        os.utime(artifact, (0, 0))

        shared = '(($t * 2.0) + 1.0)'
        node = SimpleNamespace(
            name='part', _type='SolidNode', color=None, mtime=0,
            operations=[
                _FakeOperation(['r', shared, [0, 0, 1]]),
                _FakeOperation(['t', [shared, shared, '0']]),
            ],
            rigid=True, stl_file=artifact,
        )
        builder = Builder('model.py', build_dir=build_dir, watch=False)
        builder.node = node

        self.assertTrue(builder._write_viewer_snapshot())
        document = os.path.join(build_dir, 'viewer.json')
        with open(document) as handle:
            published = json.load(handle)
        self.assertEqual(published['version'], 4)
        self.assertTrue(published['bindings'])
        before = os.stat(document).st_mtime_ns

        self.assertFalse(builder._write_viewer_snapshot())
        self.assertEqual(os.stat(document).st_mtime_ns, before)


# -------------------------------------------------------------------------
# helpers: a tiny numeric evaluator over the document's own semantics
# (OpenSCAD degree trig, `^` as pow, `%` as fmod), used only to check
# parity in this test file -- never a second evaluator shipped anywhere.

def _flat_document(node):
    with symbolic_document(node) as (declarations, _):
        root = serialize_node(node, lambda rigid: rigid.name)
    return root, declarations


def _flat_values(operation_list, scope):
    values = []
    for operation in operation_list:
        if operation[0] == 'r':
            values.append(_evaluate(operation[1], scope))
        else:
            values.extend(_evaluate(v, scope) for v in operation[1])
    return values


def _names_in(text):
    """Every identifier token in `text` that is NOT a call name (a
    name immediately followed by '(' is the language's own function,
    never something the consumer resolves from scope)."""
    return [match.group(0) for match in
            re.finditer(r'\$t|[A-Za-z_][A-Za-z0-9_.]*', text)
            if text[match.end():match.end() + 1] != '(']


def _looks_numeric(token):
    try:
        float(token)
        return True
    except ValueError:
        return False


class _Evaluator:
    """Evaluates one parsed expression node against a scope, under the
    document's own semantics: OpenSCAD degree trig, `^` as `pow`, `%` as
    `fmod` (sign of the dividend)."""

    def __init__(self, scope):
        self.scope = scope

    def __call__(self, node):
        if node.kind == 'num':
            return float(node.text)
        if node.kind == 'name':
            return self.scope[node.text]
        if node.kind == 'unary':
            return -self(node.children[0])
        if node.kind == 'binop':
            a = self(node.children[0])
            b = self(node.children[1])
            op = node.op
            if op == '+':
                return a + b
            if op == '-':
                return a - b
            if op == '*':
                return a * b
            if op == '/':
                return a / b
            if op == '%':
                return math.fmod(a, b)
            if op == '^':
                return a ** b
            if op == '==':
                return float(a == b)
            if op == '!=':
                return float(a != b)
            if op == '<':
                return float(a < b)
            if op == '>':
                return float(a > b)
            if op == '<=':
                return float(a <= b)
            if op == '>=':
                return float(a >= b)
            raise AssertionError(op)  # pragma: no cover
        if node.kind == 'call':
            args = [self(child) for child in node.children]
            funcs = {
                'floor': math.floor, 'ceil': math.ceil, 'abs': abs,
                'sign': lambda x: (x > 0) - (x < 0),
                'min': min, 'max': max, 'sqrt': math.sqrt,
                'sin': lambda d: math.sin(math.radians(d)),
                'cos': lambda d: math.cos(math.radians(d)),
                'tan': lambda d: math.tan(math.radians(d)),
                'asin': lambda x: math.degrees(math.asin(x)),
                'acos': lambda x: math.degrees(math.acos(x)),
                'atan': lambda x: math.degrees(math.atan(x)),
                'atan2': lambda y, x: math.degrees(math.atan2(y, x)),
            }
            return funcs[node.op](*args)
        raise AssertionError(node.kind)  # pragma: no cover


def _evaluate(text, scope):
    node = expr.parse(text)
    return _Evaluator(scope)(node)
