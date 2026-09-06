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
"""

import re
from unittest import TestCase

import solid_node.math as snmath
from solid_node.core.serializer import serialize_node, symbolic_document

from tests.expression_project.vocabulary import Vocabulary


def _called_names(document):
    return set(re.findall(r'([A-Za-z_]\w*)\(', str(document)))


class CorpusCoverageTest(TestCase):

    def setUp(self):
        tree = Vocabulary()
        with symbolic_document(tree) as (self.declarations, _):
            self.document = serialize_node(tree, lambda rigid: rigid.name)

    def test_every_emitted_builtin_is_exercised(self):
        called = _called_names(self.document)
        missing = sorted(set(snmath.SYMBOLIC_BUILTINS) - called)
        self.assertEqual(
            missing, [],
            f'{", ".join(missing)} can be emitted by solid_node.math but no '
            f'operation in tests/expression_project/vocabulary.py puts it on '
            f'the wire, so the parity fixture would not pin it')

    def test_the_corpus_emits_nothing_it_cannot_name(self):
        called = _called_names(self.document)
        self.assertEqual(sorted(called - set(snmath.SYMBOLIC_BUILTINS)), [])

    def test_the_corpus_is_driven(self):
        """Every call must reach a symbolic argument, or it folds to a
        number and puts no name on the wire at all."""
        self.assertIn('drive', self.declarations)
        rendered = str(self.document)
        self.assertIn('$t', rendered)
        self.assertIn('drive', rendered)
