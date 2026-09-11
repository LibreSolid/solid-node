"""Capture numeric Curta poses as independent expectations for its export.

This acceptance probe reads the originating project's current laws; it does
not derive expected numbers by evaluating the symbolic expression graph.
Run in the framework bench with PYTHONPATH pointing to it.
"""
import argparse
import hashlib
import json
from pathlib import Path

from solid_node.core.loader import load_node, select_model
from solid_node.core.serializer import serialize_node, symbolic_document
from solid_node.expression_graph import ExpressionNode, postorder
from solid_node.core.expressions import _canonical


def slots(node, path=''):
    path += '/' + node['name']
    result = {}
    for i, operation in enumerate(node.get('operations', [])):
        values = [operation[1]] if operation[0] == 'r' else operation[1]
        for j, value in enumerate(values):
            result[f'{path}:op:{i}:{j}'] = value
    for name, value in node.get('flexible', {}).get('params', {}).items():
        result[f'{path}:param:{name}'] = value
    for child in node.get('children', []):
        result.update(slots(child, path))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    selection = select_model(str(args.project / 'simulation/curta.py') + ':Curta')
    selection.anchor()
    node = load_node(selection.reference)
    document = json.loads(args.manifest.read_text())
    symbolic = slots(document['root'])
    defaults = {key: value['default'] for key, value in document['drivers'].items()}
    poses = [('rest', {})]
    poses += [(f'carry-{turn}', dict(operand=1, initial_result=9, crank_turns=turn))
              for turn in (0, .1, .3, .5, .7, .9, .99, 1, 1.01)]
    poses += [('subtract', dict(operand=1, initial_result=10, subtract=1, crank_turns=.8)),
              ('shift', dict(operand=12, carriage_position=1, crank_turns=1)),
              ('clear', dict(initial_result=12345, initial_turns=123, clear=1))]
    cases = []
    summaries = []
    for label, overrides in poses:
        state = dict(defaults, **overrides)
        node.set_state(**state)
        node.set_keyframe(0)
        numeric = slots(serialize_node(node, lambda leaf: leaf.name))
        assert numeric.keys() == symbolic.keys()
        params = {k: float(v) for k, v in numeric.items() if ':param:' in k}
        summaries.append(dict(pose=label, state=state, flexible_params=params))
        for key, expected in numeric.items():
            cases.append(dict(key=label+'|'+key, expression=symbolic[key],
                              scope=dict(time=0, drivers=state), expected=float(expected)))
    node.clear_keyframe()
    with symbolic_document(node):
        collected = slots(serialize_node(node, lambda leaf: leaf.name, graph_values=True))
    roots = [value for value in collected.values() if isinstance(value, ExpressionNode)]
    native_nodes = len(list(postorder(roots)))
    _, canonical = _canonical(roots)
    payload = dict(drivers=document['drivers'], bindings=document['bindings'], cases=cases,
                   native_graph_nodes=native_nodes, canonical_graph_nodes=len(canonical.order),
                   poses=summaries, manifest_bytes=args.manifest.stat().st_size,
                   manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest())
    args.output.write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(dict(poses=len(poses), cases=len(cases), slots=len(symbolic),
                         bindings=len(document['bindings']), native_graph_nodes=native_nodes,
                         canonical_graph_nodes=len(canonical.order),
                         manifest_bytes=payload['manifest_bytes']), indent=2))


if __name__ == '__main__':
    main()
