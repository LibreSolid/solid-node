# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`solid_node/core/expressions.py`: the expression language reader.

The grammar is exactly what the two producers emit (design.md D2): solid2's
`OpenSCADConstant.__operator_base__` / `__unary_operator_base__` / `__abs__`,
and `solid_node.math._symbolic_call`. Every case here is built by calling the
real producer where possible, rather than typed by hand, so the corpus is
honest about what the parser has to read.
"""

from unittest import TestCase

from solid2.core.object_base import OpenSCADConstant
from solid2 import get_animation_time

from solid_node.core.expressions import (
    BindingTableError, ExpressionError, Interner, bind_expressions, parse,
    render,
)
from solid_node.node.qualified import DriverToken
import solid_node.math as m


def _text(value):
    return str(value)


class ReadsEveryEmittedFormTest(TestCase):
    """Task 1.1: one case per form the framework can emit."""

    def setUp(self):
        self.interner = Interner()

    def parse(self, text):
        return parse(text, self.interner)

    def test_animation_time(self):
        node = self.parse(_text(get_animation_time()))
        self.assertEqual(node.kind, 'name')
        self.assertEqual(node.text, '$t')

    def test_a_bare_driver_id(self):
        node = self.parse(_text(DriverToken('motor')))
        self.assertEqual(node.kind, 'name')
        self.assertEqual(node.text, 'motor')

    def test_a_dotted_driver_id(self):
        node = self.parse(_text(DriverToken('x_axis.motor')))
        self.assertEqual(node.kind, 'name')
        self.assertEqual(node.text, 'x_axis.motor')

    def test_integer_literal(self):
        node = self.parse(_text(2))
        self.assertEqual(node.kind, 'num')
        self.assertEqual(node.text, '2')

    def test_decimal_literal(self):
        node = self.parse(_text(208.47))
        self.assertEqual(node.kind, 'num')
        self.assertEqual(node.text, '208.47')

    def test_exponent_literal_lowercase(self):
        node = self.parse(_text(1e-05))
        self.assertEqual(node.kind, 'num')
        self.assertEqual(node.text, '1e-05')

    def test_exponent_literal_uppercase_hand_written(self):
        node = self.parse('1E+3')
        self.assertEqual(node.kind, 'num')

    def test_leading_dot_literal_hand_written(self):
        node = self.parse('.5')
        self.assertEqual(node.kind, 'num')

    def _binary(self, op, build):
        driver = DriverToken('motor')
        built = build(driver)
        node = self.parse(_text(built))
        self.assertEqual(node.kind, 'binop')
        self.assertEqual(node.op, op)
        self.assertEqual(len(node.children), 2)

    def test_add(self):
        self._binary('+', lambda d: d + 1.0)

    def test_sub(self):
        self._binary('-', lambda d: d - 1.0)

    def test_mul(self):
        self._binary('*', lambda d: d * 1.0)

    def test_div(self):
        self._binary('/', lambda d: d / 1.0)

    def test_mod(self):
        self._binary('%', lambda d: d % 3.0)

    def test_pow(self):
        self._binary('^', lambda d: d ** 2.0)

    def test_eq(self):
        self._binary('==', lambda d: d == 1.0)

    def test_ne(self):
        self._binary('!=', lambda d: d != 1.0)

    def test_lt(self):
        self._binary('<', lambda d: d < 1.0)

    def test_gt(self):
        self._binary('>', lambda d: d > 1.0)

    def test_le(self):
        self._binary('<=', lambda d: d <= 1.0)

    def test_ge(self):
        self._binary('>=', lambda d: d >= 1.0)

    def test_unary_minus(self):
        driver = DriverToken('motor')
        node = self.parse(_text(-driver))
        self.assertEqual(node.kind, 'unary')
        self.assertEqual(node.op, '-')

    def test_nested_unary_minus(self):
        driver = DriverToken('motor')
        node = self.parse(_text(-(-driver)))
        self.assertEqual(node.kind, 'unary')
        self.assertEqual(node.children[0].kind, 'unary')
        self.assertEqual(node.children[0].children[0].kind, 'name')

    def test_a_one_argument_call(self):
        node = self.parse(_text(m.floor(DriverToken('motor'))))
        self.assertEqual(node.kind, 'call')
        self.assertEqual(node.op, 'floor')
        self.assertEqual(len(node.children), 1)

    def test_a_two_argument_call(self):
        node = self.parse(_text(m.atan2(DriverToken('motor'), 2.0)))
        self.assertEqual(node.kind, 'call')
        self.assertEqual(node.op, 'atan2')
        self.assertEqual(len(node.children), 2)

    def test_abs_from_the_dunder(self):
        node = self.parse(_text(abs(DriverToken('motor'))))
        self.assertEqual(node.kind, 'call')
        self.assertEqual(node.op, 'abs')

    def test_scad_inline_with_no_parentheses_and_addition_before_multiplication(self):
        node = self.parse('1 + 2 * 3')
        self.assertEqual(node.kind, 'binop')
        self.assertEqual(node.op, '+')
        self.assertEqual(node.children[0].text, '1')
        right = node.children[1]
        self.assertEqual(right.kind, 'binop')
        self.assertEqual(right.op, '*')

    def test_scad_inline_power_is_right_associative(self):
        node = self.parse('2 ^ 3 ^ 2')
        self.assertEqual(node.kind, 'binop')
        self.assertEqual(node.op, '^')
        self.assertEqual(node.children[0].text, '2')
        right = node.children[1]
        self.assertEqual(right.kind, 'binop')
        self.assertEqual(right.op, '^')
        self.assertEqual(right.children[0].text, '3')
        self.assertEqual(right.children[1].text, '2')


class UnreadableTextTest(TestCase):
    """Task 1.2: text the parser cannot read is reported, never guessed."""

    def parse(self, text):
        return parse(text, Interner())

    def test_unbalanced_parenthesis(self):
        with self.assertRaises(ExpressionError):
            self.parse('(1 + 2')

    def test_an_unmatched_close_paren(self):
        with self.assertRaises(ExpressionError):
            self.parse('1 + 2)')

    def test_an_unknown_token(self):
        with self.assertRaises(ExpressionError):
            self.parse('1 & 2')

    def test_a_trailing_comma(self):
        with self.assertRaises(ExpressionError):
            self.parse('floor(1,)')

    def test_a_bare_vector_literal(self):
        with self.assertRaises(ExpressionError):
            self.parse('[1, 2]')

    def test_the_error_names_the_offending_text(self):
        try:
            self.parse('[1, 2]')
        except ExpressionError as error:
            self.assertIn('[1, 2]', str(error))
        else:
            self.fail('expected an ExpressionError')


class StructuralInterningTest(TestCase):
    """Task 1.3: interning is structural, not textual."""

    def test_different_spellings_intern_to_one_node(self):
        interner = Interner()
        from_solid2 = parse(_text(OpenSCADConstant('1.0') + 2.0), interner)
        from_scad_inline = parse('1.0+2.0', interner)
        self.assertIs(from_solid2, from_scad_inline)

    def test_the_memo_does_not_change_the_answer(self):
        text = _text((DriverToken('motor') + 1.0) * (DriverToken('motor') + 1.0))

        with_memo = parse(text, Interner(), memo={})
        without_memo = parse(text, Interner(), memo=None)

        self.assertEqual(render(with_memo), render(without_memo))
        self.assertEqual(with_memo.kind, without_memo.kind)
        self.assertEqual(with_memo.op, without_memo.op)


class RoundTripTest(TestCase):
    """Task 1.4: a rendered node re-parses to itself."""

    def test_every_node_of_a_corpus_tree_round_trips(self):
        interner = Interner()
        driver = DriverToken('x_axis.motor')
        expressions = [
            _text(get_animation_time()),
            _text(driver),
            _text(2),
            _text(208.47),
            _text(driver + 1.0),
            _text(driver - 1.0),
            _text(driver * 2.0),
            _text(driver / 2.0),
            _text(driver % 3.0),
            _text(driver ** 2.0),
            _text(driver == 1.0),
            _text(-driver),
            _text(-(-driver)),
            _text(m.floor(driver)),
            _text(m.atan2(driver, 2.0)),
            _text(abs(driver)),
        ]
        nodes = [parse(expr, interner) for expr in expressions]

        for node in nodes:
            self._assert_round_trips(node, interner)

    def _assert_round_trips(self, node, interner):
        rendered = render(node)
        reparsed = parse(rendered, interner)
        self.assertIs(reparsed, node,
                       f'{rendered!r} did not re-parse to the same node')
        for child in node.children:
            self._assert_round_trips(child, interner)


class UnknownNameDoesNotRefuseTheBuildTest(TestCase):
    """Adversarial finding 1: the ordering rule binds only MINTED names.

    A name the framework does not know -- a `scad_inline` constant like
    `PI`, anything a project's own arithmetic reached solid2 with directly
    -- is the project's business, never a table defect (design.md D2: a
    document a project built and that rendered yesterday must still build
    tomorrow). Only a name that LOOKS like one of the table's own minted
    references but does not resolve is a genuine defect.
    """

    def test_an_unknown_name_reused_still_binds_and_does_not_raise(self):
        rewritten, bindings, warnings = bind_expressions(
            ['(PI * $t)', '(PI * $t)'], [])

        self.assertEqual(rewritten, ['_b0', '_b0'])
        self.assertEqual(bindings, [{'name': '_b0', 'expression': '(PI * $t)'}])
        self.assertEqual(warnings, [])

    def test_a_stray_reference_to_a_minted_looking_name_still_refuses(self):
        """The other half: a name that DOES look minted (matches the
        table's own `_b<N>` pattern) but is not $t, declared, or earlier
        is still a defect -- unreachable from a real model, reachable only
        by patching internals, exactly as the other wrong-table tests in
        `tests/test_expression_bindings.py` are."""
        from solid_node.core import expressions as expr

        bindings = [{'name': '_b0', 'expression': '_b7'}]
        with self.assertRaises(BindingTableError):
            expr._validate_bindings(bindings, driver_ids=[], prefix='_b')


class DeepChainSharingTest(TestCase):
    """Deep valid expressions now share without a recursion fallback."""

    def _left_nested_chain(self, depth):
        """`((((($t + 0) + 1) + 2) + 3) ...)`, the shape solid2 itself
        builds for a left-associative chain: every level its own
        parenthesised group."""
        text = '$t'
        for i in range(depth):
            text = f'({text} + {i})'
        return text

    def test_a_very_deep_chain_is_shared_without_a_warning(self):
        deep = self._left_nested_chain(3000)

        rewritten, bindings, warnings = bind_expressions([deep, deep], [])

        self.assertEqual(rewritten, [bindings[-1]['name']] * 2)
        self.assertEqual(len(bindings), 3000)
        self.assertEqual(warnings, [])

    def test_a_shallow_shared_expression_beside_it_still_binds(self):
        deep = self._left_nested_chain(3000)
        shallow_a = '(floor($t) + 1.0)'
        shallow_b = '(floor($t) + 2.0)'

        rewritten, bindings, warnings = bind_expressions(
            [deep, shallow_a, shallow_b], [])

        self.assertEqual(rewritten[0], deep)
        self.assertEqual(warnings, [])
        self.assertEqual(bindings, [{'name': '_b0', 'expression': 'floor($t)'}])
        self.assertEqual(rewritten[1], '(_b0 + 1.0)')
        self.assertEqual(rewritten[2], '(_b0 + 2.0)')

    def test_recursion_error_never_escapes_bind_expressions(self):
        deep = self._left_nested_chain(5000)
        try:
            bind_expressions([deep], [])
        except RecursionError:
            self.fail('RecursionError escaped bind_expressions')


class NonStringSlotIsReturnedUntouchedTest(TestCase):
    """Adversarial finding 3: defensive -- no current producer emits a
    non-string slot value, but one is never parsed and never warned
    about, only passed through exactly as it was received."""

    def test_a_float_slot_is_untouched_and_silent(self):
        rewritten, bindings, warnings = bind_expressions([1.5, 1.5], [])

        self.assertEqual(rewritten, [1.5, 1.5])
        self.assertEqual(bindings, [])
        self.assertEqual(warnings, [])
