# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The parity corpus covers every name `solid_node.math` can emit.

ADR-022's enforcement is only as wide as the corpus behind it, so a
symbolic function added to the module without a case is a name no
runtime is checked on. `tools/generate_parity_fixture.py` refuses to
regenerate when one is uncovered; this says the same thing in the
framework's own suite, where it is seen without running the generator
and without the CAD stack the spike's corpus needs.

Both read `solid_node.math.SYMBOLIC_BUILTINS`. Neither keeps a list.

ADR-080 adds a second surface: a call can live entirely inside a
`bindings` entry and appear in no operation's own expression text, so the
scan below reads the table as well as the document (tasks.md 4.4) -- the
same widening `uncovered_builtins` needed in `tools/generate_parity_fixture.py`.
"""

import re
from unittest import TestCase

import solid_node.math as snmath
from solid_node.core.serializer import (
    bind_document, drivers_table, serialize_node, symbolic_document,
)

from tests.expression_project.sharing import SharedValueTree
from tests.expression_project.vocabulary import Vocabulary


def _called_names(*documents):
    called = set()
    for document in documents:
        called |= set(re.findall(r'([A-Za-z_]\w*)\(', str(document)))
    return called


class CorpusCoverageTest(TestCase):

    def setUp(self):
        tree = Vocabulary()
        with symbolic_document(tree) as (self.declarations, _):
            self.document = serialize_node(tree, lambda rigid: rigid.name)

        sharing = SharedValueTree()
        with symbolic_document(sharing) as (sharing_declarations, _):
            sharing_root = serialize_node(sharing, lambda rigid: rigid.name)
        driver_ids = drivers_table(sharing_declarations).keys()
        self.sharing_bindings = bind_document(sharing_root, driver_ids)
        self.sharing_document = sharing_root

    def test_every_emitted_builtin_is_exercised(self):
        called = _called_names(self.document, self.sharing_document,
                               self.sharing_bindings)
        missing = sorted(set(snmath.SYMBOLIC_BUILTINS) - called)
        self.assertEqual(
            missing, [],
            f'{", ".join(missing)} can be emitted by solid_node.math but no '
            f'operation in tests/expression_project/vocabulary.py puts it on '
            f'the wire, so the parity fixture would not pin it')

    def test_the_corpus_emits_nothing_it_cannot_name(self):
        called = _called_names(self.document, self.sharing_document,
                               self.sharing_bindings)
        self.assertEqual(sorted(called - set(snmath.SYMBOLIC_BUILTINS)), [])

    def test_the_corpus_is_driven(self):
        """Every call must reach a symbolic argument, or it folds to a
        number and puts no name on the wire at all."""
        self.assertIn('drive', self.declarations)
        rendered = str(self.document)
        self.assertIn('$t', rendered)
        self.assertIn('drive', rendered)

    def test_a_name_inside_a_binding_is_covered(self):
        """The sharing corpus's own `floor` reaches this scan only
        through a `bindings` entry -- the exact shape the kinematics
        spec's "A name inside a binding is covered" scenario names, and
        the reason `_called_names` above is passed the table as well as
        the document rather than the document alone."""
        self.assertTrue(self.sharing_bindings)
        document_only = _called_names(self.sharing_document)
        with_bindings = _called_names(self.sharing_document,
                                      self.sharing_bindings)
        self.assertNotIn('floor', document_only)
        self.assertIn('floor', with_bindings)
