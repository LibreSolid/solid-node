# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""What a jump plan looks like once it is published, and the collision a
per-plan placeholder makes (design section 1.3).

Runs over a running root of the framework's own fixtures; pass a module
path and class name to run it over a project instead, e.g. the acceptance
project:

    PYTHONPATH="$PWD:<project dir>" python \
        openspec/changes/publish-the-mechanical-program/evidence/probe_placeholders.py \
        simulation.pascaline Pascaline
"""

import sys
from importlib import import_module

from solid_node.core.expressions import bind_expressions
from solid_node.expression_graph import ExpressionNode, postorder
from solid_node.scad_expression import GraphValue, as_node
from solid_node.simulation import Sim


def renamed(graph, mapping):
    """`graph` with every branch placeholder replaced through `mapping`."""
    if graph is None:
        return None
    root = as_node(graph)
    replaced = {}
    for node in postorder([root]):
        if node.kind == 'name' and node.text in mapping:
            replaced[node] = ExpressionNode('name', text=mapping[node.text])
        elif node.children:
            children = tuple(replaced.get(child, child)
                             for child in node.children)
            if children != node.children:
                replaced[node] = ExpressionNode(
                    node.kind, node.op, children, node.text)
    return GraphValue(replaced.get(root, root))


def slots(program, document_wide):
    """Every expression the program would publish, with placeholders minted
    document-wide (`document_wide=True`) or per plan, as the compiler names
    them (`document_wide=False`)."""
    minted = 0
    found, labels = [], []
    for edge in program.edges:
        for index, graph in enumerate(edge.graphs):
            plan = edge.plans[index] if edge.plans else None
            mapping = {}
            if plan is not None:
                for jump in plan.jumps:
                    if document_wide:
                        mapping[jump.placeholder] = f'_j{minted}'
                        minted += 1
                    else:
                        mapping[jump.placeholder] = (
                            '_' + jump.placeholder.lstrip('$'))
            driven = program.nodes[edge.gives[index]].name
            if graph is not None:
                found.append(renamed(graph, {}))
                labels.append(f'{driven}: expression')
            if plan is not None:
                found.append(renamed(plan.skeleton, mapping))
                labels.append(f'{driven}: plan.skeleton')
                for jump in plan.jumps:
                    found.append(renamed(jump.argument, mapping))
                    labels.append(
                        f'{driven}: plan.jump {mapping[jump.placeholder]} '
                        f'primitive={jump.primitive} affine={jump.affine}')
    return found, labels


def report(program, document_wide):
    found, labels = slots(program, document_wide)
    ids = [key for key, _ in program.inputs] + list(program.coordinates)
    rewritten, bindings, _warnings = bind_expressions(found, ids)
    kind = 'DOCUMENT-WIDE' if document_wide else 'PER PLAN'
    print(f'--- placeholders minted {kind}: {len(bindings)} bindings')
    shared = [entry for entry in bindings if '_j' in entry['expression']]
    for entry in shared:
        print(f'   a binding over a placeholder: '
              f'{entry["name"]} = {entry["expression"]}')
    for label, text in zip(labels, rewritten):
        print(f'   {label} => '
              f'{text if len(text) < 110 else text[:110] + " ..."}')


if __name__ == '__main__':
    if len(sys.argv) > 2:
        root = getattr(import_module(sys.argv[1]), sys.argv[2])()
    else:
        from tests.running_project.machine import Window
        root = Window()
    program = Sim(root, 1 / 60).program
    print(program)
    report(program, document_wide=False)
    report(program, document_wide=True)
