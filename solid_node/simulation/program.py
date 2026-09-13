# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The compiled program: a running root's relations as EXPRESSIONS over
coordinate ids.

Untimed and looping, a relation sets its driven coordinate to
``f(driver)``. Running, it contributes ``f(end) - f(start)`` over a tick,
from where the coordinate stood -- which is exact across the kinks of
``abs``, ``min`` and ``max`` and of the compositions built on them,
because it is the difference of two exact evaluations. Nothing about the
law changes; what changes is which of its two readings the run takes.

To take the difference of two evaluations the run has to be able to
EVALUATE the law at values of its own choosing, and a law is already an
expression builder: ``Affine.forward`` is ordinary arithmetic over
whatever it is handed, ``solid_node.math``'s primitives emit ``call``
nodes whose names are the closed list ``SYMBOLIC_BUILTINS``, and a
``symbol()`` builds the graph. So each law is applied ONCE here, to a
symbolic token per source coordinate, in the direction the REST RENDER
solved it, and the graph that application builds -- over the qualified
ids of its sources -- is what the run evaluates on every tick.

That application is also the inspection. What the expression cannot say
is refused by relation identity, at construction, rather than integrated
wrongly: a DISCONTINUOUS primitive (``floor``, ``ceil``, ``sign``, ``%``,
a comparison) is a jump, and jumps are the next cycle's; a law that
raises when handed a symbol, or whose graph holds text the framework
cannot evaluate, is not an expression over its sources at all; and an
edge into a bank coordinate whose source nothing in the program computes
is a value stated in ``simulate()`` rather than as a relation.

This module is imported by ``Sim.__init__`` only when the root declares
``Time.running()``, so a model that declares no running time pays for
none of it (capability ``cli-startup-cost``).
"""

import hashlib

from solid2.core.object_base import OpenSCADConstant

from solid_node.expression_graph import postorder
from solid_node.math import SYMBOLIC_BUILTINS
from solid_node.motion.couplings import (_solved_formulas, _wirings,
                                         CouplingError)
from solid_node.motion.joints import coordinates_of, declared_joints
from solid_node.node.qualified import driver_id, instance_path
from solid_node.scad_expression import GraphValue, as_node, symbol


# The primitives a continuous law may not contain. `floor`, `ceil` and
# `sign` jump by construction; `%` jumps at every period; a comparison is
# a step. Each is a crossing to be located inside the tick and
# subtracted, which is cycle 2's business, so this cycle refuses them by
# name rather than integrating across a discontinuity.
_JUMP_CALLS = ('floor', 'ceil', 'sign')
_JUMP_OPERATORS = ('%', '<', '<=', '>', '>=', '==', '!=')


class UnsupportedLaw(CouplingError):
    """A relation cannot be compiled into the running program: its law
    contains a jump, is not an expression over its sources, or is
    sourced from a coordinate the run does not own and no edge
    computes."""


def qualified_coordinates(root):
    """Every JOINT COORDINATE in `root`'s linked tree, by qualified id.

    `{qualified_id: (node, name)}`, the id being the instance path
    joined with the name `coordinates_of` reports -- the joint's own for
    a joint owning one, `<joint>.<coordinate>` for each of a `Free`.
    Every linked node the walk reaches is visited, LEAVES INCLUDED,
    because a joint may be declared on a leaf; only an assembly has
    children to descend into, exactly as `drive_tree`'s own walk has it.

    Plain ports and derived coordinates are deliberately absent: they are
    calculations over the state, recomputed by the ordinary enumeration
    on every tick, and the run stores no calculation.
    """
    from solid_node.node.assembly import _rest_children

    found = {}

    def visit(node, path):
        for joint in declared_joints(type(node)).values():
            for name in coordinates_of(joint):
                found[driver_id(path, name)] = (node, name)
        if getattr(node, '_states', None) is None:
            return
        for child in _rest_children(node):
            visit(child, path + (child.name,))

    visit(root, ())
    return found


##############################################
# What the program is made of


class Edge:
    """One step of the program: what it reads, what it determines, and
    how.

    `needs` and `gives` are keys into the program's node table. `gives`
    is empty for a CHECK, which determines nothing and only compares what
    its formula predicts with what its coordinate received -- the one
    place a conflict can be detected in this cycle.
    """

    __slots__ = ('kind', 'needs', 'gives', 'graphs', 'names', 'factors',
                 'constant', 'slot_key', 'description', 'stated_by')

    def __init__(self, kind, needs, gives, description, stated_by,
                 graphs=(), names=(), factors=(), constant=0.0,
                 slot_key=None):
        self.kind = kind
        self.needs = tuple(needs)
        self.gives = tuple(gives)
        self.graphs = tuple(graphs)
        self.names = tuple(names)
        self.factors = tuple(factors)
        self.constant = constant
        self.slot_key = slot_key
        self.description = description
        self.stated_by = stated_by

    def __repr__(self):
        return f'<{self.kind} edge {self.description}>'

    ##############################################
    # Evaluation

    def _inputs(self, values, deltas=None):
        """The graph's free names bound to the values its sources hold,
        optionally advanced by the tick's increments."""
        if deltas is None:
            return {name: values[key]
                    for name, key in zip(self.names, self.needs)}
        return {name: values[key] + deltas[key]
                for name, key in zip(self.names, self.needs)}

    def values(self, values):
        """What this edge's targets hold at the committed state."""
        if self.kind == 'law':
            inputs = self._inputs(values)
            return [(key, _evaluated(graph, inputs))
                    for key, graph in zip(self.gives, self.graphs)]
        if self.kind == 'wiring':
            factor = self.factors[0]
            return [(self.gives[0], values[self.needs[0]] * factor)]
        if self.kind == 'formula':
            return [(self.gives[0], self._linear(values))]
        return []

    def increments(self, values, deltas):
        """What this edge's targets MOVE BY over the tick: the difference
        of two exact evaluations, which is what makes a kink exact."""
        if self.kind == 'law':
            start = self._inputs(values)
            end = self._inputs(values, deltas)
            return [(key, _evaluated(graph, end) - _evaluated(graph, start))
                    for key, graph in zip(self.gives, self.graphs)]
        if self.kind == 'wiring':
            return [(self.gives[0], deltas[self.needs[0]] * self.factors[0])]
        if self.kind == 'formula':
            return [(self.gives[0], self._linear(deltas, constant=0.0))]
        return []

    def _linear(self, held, constant=None):
        """The linear combination this formula edge states, in the
        direction the rest render resolved it.

        Forward, that is the formula itself. Backward into one term, it
        is the formula rearranged for that term -- exact, because a
        derived coordinate is a coefficient map and a constant, not an
        expression tree.
        """
        total = self.constant if constant is None else constant
        if self.slot_key in self.gives:
            for key, factor in zip(self.needs, self.factors):
                total = total + held[key] * factor
            return total
        # Backward: `gives` is the one term the formula solves for, and
        # `needs` carries the slot first, then the other terms.
        value = held[self.slot_key] - total
        own = None
        for key, factor in zip(self.needs, self.factors):
            if key == self.slot_key:
                continue
            if key == self.gives[0]:
                own = factor
                continue
            value = value - held[key] * factor
        return value / own

    def predicts(self, held, constant=None):
        """What a CHECK edge's formula says its coordinate should hold,
        or move by."""
        total = self.constant if constant is None else constant
        for key, factor in zip(self.needs, self.factors):
            if key == self.slot_key:
                continue
            total = total + held[key] * factor
        return total


def _evaluated(graph, inputs):
    if graph is None:
        # A law whose expression has no free coordinate -- a constant --
        # has zero slope everywhere, so it contributes nothing. The
        # refusal the decision asks for needs jump detection to tell a
        # gate from a constant, and is cycle 2's.
        return 0.0
    return graph.evaluate(inputs)


class Program:
    """A running root's relations, compiled once, in order.

    `identity` is what a snapshot is checked against: a digest of the
    root class, the bank's ids, the inputs' declarations and every edge's
    ends, direction and expression, so a snapshot cannot be restored into
    a tree whose kinematics have moved on.
    """

    def __init__(self, root, inputs, coordinates, nodes, edges):
        self.root_class = type(root)
        self.inputs = tuple(inputs)
        self.coordinates = tuple(coordinates)
        self.nodes = nodes
        self.edges = tuple(edges)
        self.determiner = {key: edge for edge in self.edges
                           for key in edge.gives}
        self.identity = hashlib.sha256(
            self.described().encode()).hexdigest()

    def described(self):
        """The canonical listing the identity is taken of, and what a
        message about the program prints."""
        lines = [f'root {self.root_class.__module__}.'
                 f'{self.root_class.__qualname__}']
        for identifier, declaration in self.inputs:
            lines.append(f'input {identifier} dtype={declaration.dtype!r} '
                         f'scale={declaration.scale!r}')
        for identifier in self.coordinates:
            lines.append(f'coordinate {identifier}')
        for edge in self.edges:
            ends = (f'{[self.nodes[key].name for key in edge.needs]} -> '
                    f'{[self.nodes[key].name for key in edge.gives]}')
            if edge.kind == 'law':
                how = ' | '.join('constant' if graph is None else str(graph)
                                 for graph in edge.graphs)
            elif edge.kind == 'wiring':
                how = f'identity * {edge.factors[0]!r}'
            else:
                how = (f'{list(edge.factors)!r} + {edge.constant!r} '
                       f'on {self.nodes[edge.slot_key].name}')
            lines.append(f'{edge.kind} {ends} {how} [{edge.description}]')
        return '\n'.join(lines)

    def __repr__(self):
        return (f'<program of {self.root_class.__name__}: '
                f'{len(self.nodes)} coordinates, {len(self.edges)} edges>')


class _Node:
    """One coordinate the program computes over: a bank id, or an
    INTERMEDIATE a compiled edge determines."""

    __slots__ = ('key', 'name', 'kind')

    def __init__(self, key, name, kind):
        self.key = key
        self.name = name
        self.kind = kind

    def __repr__(self):
        return f'<{self.kind} {self.name}>'


##############################################
# Compiling


def compile_program(root, inputs, coordinates):
    """The program of `root`, read off what the REST RENDER solved.

    `inputs` is `{qualified id: Driver}` and `coordinates` is
    `{qualified id: (node, name)}`; together they are the bank.
    """
    nodes = {}
    for identifier, _declaration in inputs.items():
        nodes[('input', identifier)] = _Node(
            ('input', identifier), identifier, 'input')
    bank_keys = set(nodes)
    for identifier, (node, name) in coordinates.items():
        from solid_node.motion.ports import get_coordinate

        slot = get_coordinate(node, name)
        key = ('slot', id(slot))
        nodes[key] = _Node(key, identifier, 'bank')
        bank_keys.add(key)

    candidates = []
    for assembly, path, records, formulas, wirings in _units(root):
        for record in records:
            edge = _relation_edge(root, assembly, record, nodes, bank_keys)
            if edge is not None:
                candidates.append(edge)
        for wiring in wirings:
            edge = _wiring_edge(root, assembly, wiring, nodes)
            if edge is not None:
                candidates.append(edge)
        for formula in formulas:
            edge = _formula_edge(root, assembly, formula, nodes)
            if edge is not None:
                candidates.append(edge)

    kept = _reaching_the_bank(candidates, bank_keys)
    _refuse_opaque(kept, bank_keys, nodes)
    ordered = _ordered(kept, nodes)
    return Program(root, sorted(inputs.items()), sorted(coordinates),
                   nodes, ordered)


def _units(root):
    """Every assembly of the linked tree with what its own rest render
    recorded: its relation records, the derived coordinates it solves and
    its wirings, in tree order."""
    from solid_node.node.assembly import _rest_children

    found = []

    def visit(node, path):
        if getattr(node, '_states', None) is None:
            return
        records = node.__dict__.get('_relations', ())
        found.append((node, path, records,
                      _solved_formulas(node, records), _wirings(node)))
        for child in _rest_children(node):
            visit(child, path + (child.name,))

    visit(root, ())
    return found


def _register(nodes, root, end):
    """`end`'s program node, created on first sight."""
    if end.is_driver:
        key = ('input', _qualified(root, end))
    else:
        key = ('slot', id(end.slot))
    found = nodes.get(key)
    if found is None:
        found = nodes[key] = _Node(key, _qualified(root, end), 'intermediate')
    return found


def _qualified(root, end):
    from solid_node.node.qualified import DriverIdError

    try:
        return driver_id(instance_path(end.node, root), end.name)
    except DriverIdError:
        return f'{type(end.node).__name__}.{end.name}'


def _relation_edge(root, assembly, record, nodes, bank_keys):
    """One relation as an edge, in the direction the rest render solved
    it -- or `None` when the rest render left it to no one."""
    if record.direction not in ('forward', 'backward'):
        return None
    if record.direction == 'forward':
        sources, targets = record.driver_ends, record.driven_ends
    else:
        sources, targets = record.driven_ends, record.driver_ends
    source_nodes = [_register(nodes, root, end) for end in sources]
    target_nodes = [_register(nodes, root, end) for end in targets]

    banked = [node.key in bank_keys for node in target_nodes]
    if any(banked) and not all(banked):
        raise UnsupportedLaw(
            f'{record.described()}, stated by {type(assembly).__name__}: '
            f'its driven ends are '
            f'{", ".join(node.name for node in target_nodes)}, of which the '
            f'running simulation owns only some. A relation drives one '
            f'group; state the rest as joints, or as a relation of their '
            f'own.')

    graphs = _law_graphs(assembly, record, source_nodes, len(target_nodes))
    return Edge('law', [node.key for node in source_nodes],
                [node.key for node in target_nodes],
                record.described(), type(assembly).__name__,
                graphs=graphs, names=[node.name for node in source_nodes])


def _law_graphs(assembly, record, source_nodes, count):
    """The law applied ONCE to a symbolic token per source, checked to be
    an expression the run can evaluate."""
    def refuse(detail):
        raise UnsupportedLaw(
            f'{record.described()}, stated by {type(assembly).__name__}: '
            f'{detail}')

    tokens = [symbol(node.name) for node in source_nodes]
    try:
        if record.direction == 'backward':
            returned = record.law.inverse(tokens[0])
        else:
            returned = record.law.forward(*tokens)
    except Exception as failure:
        refuse(f'the law {record.law!r} cannot be applied to symbols '
               f'({type(failure).__name__}: {failure}). A running law is '
               f'an expression over its sources: it is applied once, to a '
               f'token per source, and the graph it builds is what the run '
               f'integrates. Write it with solid_node.math, whose '
               f'primitives are symbolic.')

    if count == 1:
        returned = (returned,)
    else:
        try:
            length = len(returned)
        except TypeError:
            length = None
        if length != count:
            refuse(f'the law {record.law!r} returned {returned!r} for '
                   f'{count} driven ends, which is not a sequence of '
                   f'exactly {count} values.')
    return [_graph_of(value, refuse) for value in returned]


def _graph_of(value, refuse):
    """`value` as the expression graph the run evaluates, `None` for a
    constant, or the refusal naming what it is instead."""
    if isinstance(value, bool):
        refuse(f'the law returned {value!r}, which is neither a number nor '
               f'an expression.')
    if isinstance(value, (int, float)):
        return None
    if not isinstance(value, OpenSCADConstant):
        refuse(f'the law returned {value!r}, which is neither a number nor '
               f'an expression over its sources.')
    root = as_node(value)
    for item in postorder([root]):
        if item.kind == 'raw':
            refuse(f'its expression carries the text {item.text!r}, which '
                   f'the framework cannot evaluate: a running law is an '
                   f'expression over its sources.')
        if item.kind == 'call':
            if item.op in _JUMP_CALLS:
                refuse(f'its expression contains {item.op}(), which is a '
                       f'jump; jumps are not yet supported by the running '
                       f'mode, and locating a crossing inside the tick is '
                       f'the next cycle. Untimed and looping, the same law '
                       f'poses exactly as it always did.')
            if item.op not in SYMBOLIC_BUILTINS:
                refuse(f'its expression calls {item.op!r}, which is outside '
                       f'the symbolic vocabulary the run can evaluate.')
        if item.kind == 'binop' and item.op in _JUMP_OPERATORS:
            refuse(f"its expression contains the operator '{item.op}', "
                   f'which is a jump; jumps are not yet supported by the '
                   f'running mode.')
    return GraphValue(root)


def _wiring_edge(root, assembly, wiring, nodes):
    """A wiring as the forward-only identity edge it already is."""
    source = _slot_node(nodes, root, wiring.slot)
    target = _slot_node(nodes, root, wiring.target)
    factor = 1.0 if wiring.target.scale is None else wiring.target.scale
    return Edge('wiring', [source.key], [target.key],
                wiring.described(), type(assembly).__name__,
                factors=[factor], names=[source.name])


def _slot_node(nodes, root, slot):
    key = ('slot', id(slot))
    found = nodes.get(key)
    if found is None:
        from solid_node.node.qualified import DriverIdError

        try:
            name = driver_id(instance_path(slot.node, root), slot.name)
        except DriverIdError:
            name = f'{type(slot.node).__name__}.{slot.name}'
        found = nodes[key] = _Node(key, name, 'intermediate')
    return found


def _formula_edge(root, assembly, formula, nodes):
    """A derived coordinate as the LINEAR edge it is, in the direction
    the rest render resolved it -- or as a CHECK when its slot and every
    term were bound by others, which is the one place two inputs
    prescribing one rigid group can be caught."""
    slot = formula.slot_of(assembly)
    slot_node = _slot_node(nodes, root, slot)
    terms = formula.resolved_terms(assembly)
    term_nodes = [(_register(nodes, root, end), float(coefficient))
                  for end, coefficient in terms]
    constant = float(formula.resolved_constant(assembly))
    described = f"the derived coordinate '{formula.described()}' " \
                f'({formula.written})'

    if slot.binder is formula:
        return Edge('formula', [node.key for node, _ in term_nodes],
                    [slot_node.key], described, type(assembly).__name__,
                    factors=[factor for _, factor in term_nodes],
                    constant=constant, slot_key=slot_node.key)
    for (node, _factor), (end, _coefficient) in zip(term_nodes, terms):
        if end.slot is not None and end.slot.binder is formula:
            needs = [slot_node.key] + [other.key for other, _ in term_nodes
                                       if other is not node]
            factors = ([0.0] + [factor for other, factor in term_nodes
                                if other is not node])
            # The solved-for term's own coefficient travels with it, so
            # `_linear` can divide by it.
            needs.append(node.key)
            factors.append(next(factor for other, factor in term_nodes
                                if other is node))
            return Edge('formula', needs, [node.key], described,
                        type(assembly).__name__, factors=factors,
                        constant=constant, slot_key=slot_node.key)
    needs = [slot_node.key] + [node.key for node, _ in term_nodes]
    factors = [0.0] + [factor for _, factor in term_nodes]
    return Edge('check', needs, (), described, type(assembly).__name__,
                factors=factors, constant=constant, slot_key=slot_node.key)


def _reaching_the_bank(candidates, bank_keys):
    """The edges that matter: one determining a coordinate the run owns,
    one determining anything such an edge reads, and a CHECK over what
    those produce.

    A relation or wiring whose driven ends are all outside the bank and
    reach no bank coordinate -- a pulley driving a belt's plain port --
    is left to the ordinary enumeration, which recomputes it from the
    run-bound sources on every tick.
    """
    matters = set(bank_keys)
    kept = []
    changed = True
    while changed:
        changed = False
        for edge in candidates:
            if edge in kept:
                continue
            reached = (set(edge.needs) if edge.kind == 'check'
                       else set(edge.gives))
            if not (reached & matters):
                continue
            kept.append(edge)
            matters.update(edge.needs)
            matters.update(edge.gives)
            changed = True
    return kept


def _refuse_opaque(kept, bank_keys, nodes):
    """An edge reading a coordinate the run does not own and no kept edge
    computes is refused by name: a plain port the author's `simulate()`
    binds is a value stated imperatively, not a relation the run can
    integrate."""
    computed = {key for edge in kept for key in edge.gives}
    for edge in kept:
        for key in edge.needs:
            if key in bank_keys or key in computed:
                continue
            raise UnsupportedLaw(
                f'{edge.description}, stated by {edge.stated_by}: it is '
                f'sourced from {nodes[key].name}, which the running '
                f'simulation does not own and no relation computes -- a '
                f'plain port an author\'s simulate() binds. The run '
                f'integrates relations over drivers and joint '
                f'coordinates, so state that value as a relation, or give '
                f'the part a joint.')


def _ordered(kept, nodes):
    """The edges in an order where every edge's sources are determined
    before it runs: Kahn over the ends each edge determines.

    A coordinate no edge determines is resolved from the start -- it is
    an input, or it HOLDS -- so an edge waits only on the ends something
    else in the program moves.
    """
    determiner = {}
    for edge in kept:
        for key in edge.gives:
            determiner[key] = edge
    resolved = {key for key in nodes if key not in determiner}
    order = []
    remaining = list(kept)
    while remaining:
        ready = [edge for edge in remaining
                 if all(key in resolved for key in edge.needs)]
        if not ready:
            stuck = ', '.join(edge.description for edge in remaining)
            raise UnsupportedLaw(
                f'the relations {stuck} form a cycle the run cannot order: '
                f'each waits on a coordinate another determines. A running '
                f'program is acyclic, because the rest render solved every '
                f'relation in one direction.')
        for edge in ready:
            order.append(edge)
            remaining.remove(edge)
            resolved.update(edge.gives)
    return order
