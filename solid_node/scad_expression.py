# Copyright (C) 2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""SolidPython compatibility around native shared motion values.

Only this facade knows SolidPython. Its base class supplies type compatibility,
never arithmetic or eager initialization. SCAD text is an output, not storage.
"""

from solid2.core.object_base import OpenSCADConstant

from solid_node.expression_graph import ExpressionNode


def as_node(value):
    if isinstance(value, GraphValue):
        return value._expression_node
    if isinstance(value, ExpressionNode):
        return value
    if isinstance(value, OpenSCADConstant):
        from solid_node.core.expressions import parse, ExpressionError
        text = str(value)
        try:
            return parse(text)
        except ExpressionError:
            return ExpressionNode('raw', text=text)
    return ExpressionNode('num', text=str(value))


class GraphValue(OpenSCADConstant):
    def __init__(self, node):
        self._expression_node = node

    @property
    def value(self):
        return str(self)

    def __str__(self):
        from solid_node.core.expressions import scad_expression
        return scad_expression(self._expression_node)

    def __repr__(self):
        return repr(self._expression_node)

    def __float__(self):
        return float(self.evaluate({}))

    def evaluate(self, inputs):
        """Resolve a restored scalar with explicit inputs, never implicit time.

        Normal poses still rerun the author's law with numbers. This small
        iterative evaluator is for expression/operation round-trips only.
        """
        import math
        import operator
        from solid_node import math as degree_math
        from solid_node.expression_graph import postorder
        operators = {'+': operator.add, '-': operator.sub, '*': operator.mul,
                     '/': operator.truediv, '%': math.fmod, '^': operator.pow,
                     '<': operator.lt, '<=': operator.le, '>': operator.gt,
                     '>=': operator.ge, '==': operator.eq, '!=': operator.ne}
        values = {}
        for node in postorder([self._expression_node]):
            args = [values[child] for child in node.children]
            if node.kind == 'num':
                value = float(node.text)
            elif node.kind == 'name':
                if node.text not in inputs:
                    raise ValueError(f'Unresolved motion input {node.text[:80]!r}')
                value = float(inputs[node.text])
            elif node.kind == 'binop':
                value = operators[node.op](*args)
            elif node.kind == 'unary':
                value = -args[0] if node.op == '-' else +args[0]
            elif node.kind == 'call' and node.op in degree_math.SYMBOLIC_BUILTINS:
                value = getattr(degree_math, node.op)(*args)
            else:
                raise ValueError(f'Cannot numerically resolve {node!r}')
            values[node] = value
        return values[self._expression_node]

    def _render(self):
        return str(self)

    def __operator_base__(self, op, other):
        return GraphValue(ExpressionNode(
            'binop', op, (self._expression_node, as_node(other))))

    def __roperator_base__(self, op, other):
        return GraphValue(ExpressionNode(
            'binop', op, (as_node(other), self._expression_node)))

    def __unary_operator_base__(self, op):
        return GraphValue(ExpressionNode('unary', op, (self._expression_node,)))

    # Reflected methods must be distinct from the base implementation for
    # Python to prefer this subtype when a legacy constant is on the left.
    def __radd__(self, other): return self.__roperator_base__('+', other)
    def __rsub__(self, other): return self.__roperator_base__('-', other)
    def __rmul__(self, other): return self.__roperator_base__('*', other)
    def __rtruediv__(self, other): return self.__roperator_base__('/', other)
    def __rmod__(self, other): return self.__roperator_base__('%', other)
    def __rpow__(self, other): return self.__roperator_base__('^', other)
    def __lt__(self, other): return self.__operator_base__('<', other)
    def __le__(self, other): return self.__operator_base__('<=', other)
    def __gt__(self, other): return self.__operator_base__('>', other)
    def __ge__(self, other): return self.__operator_base__('>=', other)
    def __eq__(self, other): return self.__operator_base__('==', other)
    def __ne__(self, other): return self.__operator_base__('!=', other)

    def __abs__(self):
        return call('abs', self)


def call(name, *args):
    return GraphValue(ExpressionNode('call', name, tuple(as_node(x) for x in args)))


def symbol(name):
    return GraphValue(ExpressionNode('name', text=name))


def get_animation_time():
    return symbol('$t')


def depends_on_time(value):
    if isinstance(value, OpenSCADConstant):
        from solid_node.expression_graph import postorder
        node = as_node(value)
        return any((item.kind == 'name' and item.text == '$t') or
                   (item.kind == 'raw' and '$t' in item.text)
                   for item in postorder([node]))
    return False


def scalar(value, graph=False):
    """A producer collects native roots; standalone callers get closed SCAD."""
    if graph and isinstance(value, OpenSCADConstant):
        return as_node(value)
    return str(value)


def restore_scalar(value):
    if isinstance(value, str):
        from solid_node.core.expressions import parse, ExpressionError
        try:
            node = parse(value)
        except ExpressionError:
            return OpenSCADConstant(value)
        if node.kind == 'num':
            return value
        return GraphValue(node)
    return value
