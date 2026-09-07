# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Schema v3: the flexible node shape, and the version that admits it.

A flexible part's viewer representation is its SPEC, not a mesh. There
is no per-frame artifact to publish and none to cache, so the document
carries the shape's own serialization plus one expression string per
parameter, and the consumer evaluates geometry the way it already
evaluates pose.

The version rule is the other half. A new tree shape is a breaking
change (ADR-034), but a document containing no flexible node is
bit-identical to the version 2 it was before this existed -- so the
producer emits the LOWEST version its content needs, exactly as the
drivers table did, and an old consumer refuses only documents it
genuinely cannot render.

Both producers are covered here, because both serialize the same tree
through the same walk: the build's published `viewer.json` and the
export's `manifest.json`.
"""

import json
import os

from solid_node.core.builder import Builder, project_build_lock
from solid_node.core.export import export_node
from solid_node.core.serializer import (
    BINDINGS_DOCUMENT_VERSION, DOCUMENT_VERSION, FLEXIBLE_DOCUMENT_VERSION,
    document_version, serialize_node, symbolic_document,
)
from solid_node.simulation.enumeration import bind_declared_defaults

from .base import BaseNodeTest
from .flexible_project import spring as fixture
from .meta_project.machine import Machine


#: The expression the fixture's `connect(FREE_HEIGHT - self.lift, ...)`
#: produces once the driver is bound to its qualified token.
LIFT_EXPRESSION = '(46.8 - valvetrain.lift)'


def resolved(document, expression_or_name):
    """`expression_or_name` as the flat expression it stands for: itself,
    unless it is exactly one document `bindings` entry's name (schema
    v4, ADR-080) -- `Valvetrain.render()` builds `FREE_HEIGHT - self.lift`
    twice (once for the retainer's placement, once for the spring's
    port), so this fixture's own LIFT_EXPRESSION is exactly the kind of
    repeat this cycle publishes once and references."""
    for entry in document.get('bindings', ()):
        if entry['name'] == expression_or_name:
            return entry['expression']
    return expression_or_name

#: Every key a node of a flexible-free document has ever carried.
VERSION_2_NODE_KEYS = {'name', 'type', 'color', 'mtime', 'operations',
                       'model', 'piece', 'children'}


def find(node, name):
    """The first node called `name` in a serialized tree."""
    if node['name'] == name:
        return node
    for child in node.get('children', ()):
        found = find(child, name)
        if found is not None:
            return found
    return None


def bound_engine(**snapshot):
    engine = fixture.Engine()
    bind_declared_defaults(engine)
    if snapshot:
        engine.set_state(**snapshot)
    return engine


class FlexibleNodeShapeTest(BaseNodeTest):
    """What a flexible leaf serializes as."""

    def serialized(self, node):
        with symbolic_document(node) as (declarations, _):
            return serialize_node(node, lambda rigid: rigid.name), declarations

    def spring(self, node):
        root, declarations = self.serialized(node)
        return find(root, 'spring'), root, declarations

    def test_a_flexible_leaf_carries_tech_spec_and_params(self):
        spring, _, _ = self.spring(bound_engine())

        self.assertEqual(spring['flexible']['tech'], 'molejo')
        self.assertEqual(spring['flexible']['spec'],
                         fixture.Spring().render().to_dict())
        self.assertEqual(spring['flexible']['params'],
                         {'height': LIFT_EXPRESSION})

    def test_the_embedded_spec_is_the_adapters_own_serialization(self):
        spring, _, _ = self.spring(bound_engine())

        self.assertEqual(spring['flexible']['spec']['molejo'],
                         fixture.Spring().render().to_dict()['molejo'])
        self.assertEqual(json.loads(json.dumps(spring['flexible'])),
                         spring['flexible'])

    def test_a_flexible_leaf_stops_the_recursion(self):
        """Its geometry travels as the spec: no model reference, no
        piece, and nothing below it to walk into."""
        spring, _, _ = self.spring(bound_engine())

        self.assertNotIn('model', spring)
        self.assertNotIn('children', spring)
        self.assertNotIn('piece', spring)

    def test_it_keeps_the_shared_node_fields(self):
        spring, _, _ = self.spring(bound_engine())

        self.assertEqual(spring['name'], 'spring')
        self.assertEqual(spring['color'], None)
        self.assertIn('mtime', spring)
        self.assertEqual(spring['operations'], [])

    def test_the_type_field_follows_the_established_convention(self):
        """`type` publishes the framework's node KIND, declared once per
        kind and never overridden by an adapter or a project class -- the
        rigid sibling beside it is a `CadQueryNode` and publishes
        `LeafNode` too."""
        spring, root, _ = self.spring(bound_engine())

        self.assertEqual(spring['type'], 'LeafNode')
        self.assertEqual(find(root, 'retainer')['type'], 'LeafNode')

    def test_an_unbound_port_fails_naming_the_node_and_the_port(self):
        with self.assertRaises(Exception) as raised:
            serialize_node(fixture.Spring(), lambda rigid: rigid.name)

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)


class FlexibleParamsExpressionTest(BaseNodeTest):
    """`params` obeys the guarantee operation expressions obey."""

    def document(self, node):
        with symbolic_document(node) as (declarations, _):
            root = serialize_node(node, lambda rigid: rigid.name)
        return root, declarations

    def test_a_snapshot_bound_tree_still_serializes_expressions(self):
        """The producer's obligation, not the caller's: a simulation that
        stepped the machine must not bake its instant into `params`."""
        engine = bound_engine(**{'valvetrain.lift': 6.0})

        root, _ = self.document(engine)

        self.assertEqual(find(root, 'spring')['flexible']['params'],
                         {'height': LIFT_EXPRESSION})

    def test_the_prior_binding_is_restored_afterwards(self):
        engine = bound_engine(**{'valvetrain.lift': 6.0})

        self.document(engine)

        self.assertEqual(engine.valvetrain.lift, 6.0)
        self.assertEqual(engine.valvetrain.spring.height.value,
                         fixture.FREE_HEIGHT - 6.0)

    def test_every_id_a_params_expression_names_is_a_declared_driver(self):
        """The two tables are one contract, and `params` joins it: an id
        a client cannot resolve to a declared driver is a shape it cannot
        evaluate."""
        root, declarations = self.document(bound_engine())

        expressions = find(root, 'spring')['flexible']['params'].values()
        referenced = {identifier for identifier in declarations
                      for expression in expressions
                      if identifier in expression}
        self.assertEqual(referenced, {'valvetrain.lift'})
        self.assertLessEqual(referenced, set(declarations))


class DocumentVersionRuleTest(BaseNodeTest):
    """The lowest version the content needs."""

    def test_the_flexible_schema_version_is_three(self):
        self.assertEqual(DOCUMENT_VERSION, 2)
        self.assertEqual(FLEXIBLE_DOCUMENT_VERSION, 3)

    def test_a_tree_holding_a_flexible_leaf_declares_three(self):
        engine = bound_engine()
        with symbolic_document(engine) as (_, _instructions):
            root = serialize_node(engine, lambda rigid: rigid.name)

        self.assertEqual(document_version(root), FLEXIBLE_DOCUMENT_VERSION)

    def test_a_flexible_free_tree_declares_two(self):
        machine = Machine()
        bind_declared_defaults(machine)
        with symbolic_document(machine) as (_, _instructions):
            root = serialize_node(machine, lambda rigid: rigid.name)

        self.assertEqual(document_version(root), DOCUMENT_VERSION)


class FlexiblePublishedBuildTest(BaseNodeTest):
    """The build's `viewer.json`."""

    def publish(self, node):
        builder = Builder('model.py', build_dir=self.build_dir)
        builder.node = node
        builder._write_viewer_snapshot()
        with open(os.path.join(self.build_dir, 'viewer.json')) as document:
            return json.load(document)

    def test_the_published_document_declares_version_three(self):
        """The fixture's `retainer.translate` and `spring.params.height`
        both build `FREE_HEIGHT - self.lift`, so this document also has a
        shared subexpression to publish once (schema v4, ADR-080) and
        declares 4 rather than the 3 flexible content alone would need."""
        engine = bound_engine()
        engine.assemble()

        document = self.publish(engine)

        self.assertEqual(document['version'], BINDINGS_DOCUMENT_VERSION)
        self.assertEqual(find(document['root'], 'spring')['flexible']['tech'],
                         'molejo')

    def test_the_published_flexible_leaf_is_no_piece(self):
        engine = bound_engine()
        engine.assemble()

        document = self.publish(engine)

        self.assertEqual([piece['name'] for piece in document['pieces']],
                         ['Retainer'])

    def test_a_flexible_free_publication_is_unchanged(self):
        """`Axis.render()` builds `self.position.value` once for the
        carriage and again, nested, in the cover's expression, and the
        two axes' covers both build `5.0 * cos(360.0 * $t)` -- so this
        fixture, too, has genuine sharing to publish (ADR-080) and
        declares 4 rather than the flexible-free 2 it declared before
        this cycle. Version aside, the tree remains flexible-free: no
        node grows the `flexible` key."""
        machine = Machine()
        bind_declared_defaults(machine)
        with project_build_lock():
            machine.build_stls()

        document = self.publish(machine)

        self.assertEqual(document['version'], BINDINGS_DOCUMENT_VERSION)
        self.assertNotIn('flexible', json.dumps(document))

        def keys(node):
            self.assertLessEqual(set(node), VERSION_2_NODE_KEYS)
            for child in node.get('children', ()):
                keys(child)

        keys(document['root'])


class FlexibleExportTest(BaseNodeTest):
    """The export's `manifest.json`, self-contained as ever."""

    def export(self, node):
        out_dir = os.path.join(self.build_dir, 'export_out')
        return export_node(node, out_dir, widget=False), out_dir

    def test_the_manifest_carries_the_spec_and_declares_version_three(self):
        """As `FlexiblePublishedBuildTest` above: the shared lift
        expression makes this document version 4, and the spring's
        `params.height` is now that binding's name rather than the
        expression's own text (design.md D3 -- "a reference is the
        binding's name written where an expression would be")."""
        manifest, _ = self.export(bound_engine())

        spring = find(manifest['root'], 'spring')
        self.assertEqual(manifest['version'], BINDINGS_DOCUMENT_VERSION)
        self.assertEqual(spring['flexible']['tech'], 'molejo')
        self.assertEqual(spring['flexible']['spec'],
                         fixture.Spring().render().to_dict())
        self.assertEqual(
            resolved(manifest, spring['flexible']['params']['height']),
            LIFT_EXPRESSION)
        self.assertIn('valvetrain.lift', manifest['drivers'])

    def test_the_export_stays_self_contained_with_no_model_for_it(self):
        manifest, out_dir = self.export(bound_engine())

        spring = find(manifest['root'], 'spring')
        self.assertNotIn('model', spring)
        self.assertNotIn('piece', spring)
        models = [name for _, _, files in os.walk(os.path.join(out_dir,
                                                               'models'))
                  for name in files]
        self.assertEqual(len(models), 1)
        self.assertEqual([piece['name'] for piece in manifest['pieces']],
                         ['Retainer'])

    def test_a_snapshot_bound_export_still_publishes_expressions(self):
        manifest, _ = self.export(bound_engine(**{'valvetrain.lift': 6.0}))

        spring = find(manifest['root'], 'spring')
        self.assertEqual(
            resolved(manifest, spring['flexible']['params']['height']),
            LIFT_EXPRESSION)

    def test_a_flexible_free_export_keeps_version_two(self):
        """Named for the flexible-free content it tests, but this fixture
        also has the sharing `FlexiblePublishedBuildTest` above documents,
        so it now declares 4 (ADR-080), not the flexible-free 2 alone."""
        machine = Machine()
        bind_declared_defaults(machine)

        manifest, _ = self.export(machine)

        self.assertEqual(manifest['version'], BINDINGS_DOCUMENT_VERSION)
        self.assertNotIn('flexible', json.dumps(manifest))
