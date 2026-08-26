"""Readback for the expression spike. NON-SHIPPING.

This file used to hold the spike's shims -- `DriverToken`, a link-aware
per-instance binding walk, a qualified-id helper and a qualified driver
enumeration -- each marked with the SEAM it reached past. The
`instance-qualified-drivers` change shipped all four, so they are
deleted rather than adapted, exactly as `spike/axis/steplab.py` was
when stage 2 landed:

- `DriverToken` and `driver_id`/`instance_path` are
  `solid_node.node.qualified`;
- the binding walk is `solid_node.node.qualified.drive_tree`, reached
  publicly through `AssemblyNode.set_state` (numeric, by qualified id)
  and `solid_node.core.serializer.symbolic_drivers` (symbolic);
- the qualified enumeration is
  `solid_node.simulation.enumeration.qualified_drivers`.

What remains is not a shim. `collect_ops` is measurement: it reads back
what a render actually produced, keyed the way this spike's transcript
and its client-parity harness compare passes. The framework's own
`serialize_node` publishes a nested document with model paths; the
comparison here wants a flat map of operation scalars, so this stays
spike-local.
"""


def collect_ops(root):
    """Every operation scalar in the tree, keyed by
    `node/path#index.slot`, in `serialize_node` order.

    Values come from `operation.serialized`, i.e. `str(value)` -- the
    exact wire form the client evaluates. Under a numeric binding those
    strings are numerals; under a symbolic binding they are
    expressions. Same keys either way, so the two passes compare.
    """
    values = {}
    chain = {}
    nodes = {}

    def walk(node, path, parent_path):
        chain[path] = (parent_path, [])
        nodes[path] = node
        for index, operation in enumerate(node.operations):
            serialized = operation.serialized
            if serialized[0] == 'r':
                values[f'{path}#{index}.angle'] = serialized[1]
                chain[path][1].append(('r', serialized[2],
                                       [f'{path}#{index}.angle']))
            else:
                slots = []
                for slot, component in enumerate(serialized[1]):
                    key = f'{path}#{index}.t{slot}'
                    values[key] = component
                    slots.append(key)
                chain[path][1].append(('t', None, slots))
        rendered = node.render()
        if type(rendered) not in (list, tuple):
            return
        for child in rendered:
            node._link_child(child)
            walk(child, f'{path}/{child.name}', path)

    walk(root, root.name, None)
    return values, chain, nodes
