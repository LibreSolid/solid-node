"""Spike-level shims for named-driver expressions. NON-SHIPPING.

Everything here lives OUTSIDE the framework (spike/expressions/SCOPE.md
forbids framework edits) and exists to answer one question each. Every
place a shim reaches past a public surface is marked SEAM: that is the
finding, not an accident.

Three pieces:

- `DriverToken` -- the candidate expression representation: a subclass
  of solid2's `OpenSCADConstant` whose string IS the eagerly qualified
  driver id. Because solid2 arithmetic is string-eager and
  `solid_node.math` dispatches on `isinstance(x, OpenSCADConstant)`,
  ordinary project arithmetic and degree trig produce a well-formed
  wire expression for free -- no new operator overloads, no expression
  tree to maintain.

- `bind()` -- a link-aware, pre-render, per-instance binding walk. The
  framework's own `set_state` cannot do this: it merges ONE flat dict
  and propagates the SAME dict to every child, and it validates each
  value as a plain number.

- `collect_ops()` -- reads back what a render actually produced, in
  the same order and by the same rules the shipped `serialize_node`
  uses, so the numeric and symbolic passes can be compared key by key.
"""

from solid2.core.object_base import OpenSCADConstant

from solid_node.simulation.driver import declared_drivers


# ----------------------------------------------------------------- ids

def instance_path(node):
    """The node's path from the serialization root: the chain of
    `name`s above it, computed from `_parent` links, NEVER stored.

    `name` is the attribute name the parent holds the child under
    (base.py `_link_child`/`_attr_name_for`), which is precisely the
    Modelica-flattening component name -- and it is derived by the
    parent, so it exists only after linking. See findings 2.
    """
    parts = []
    current = node
    while getattr(current, '_parent', None) is not None:
        parts.append(current.name)
        current = current._parent
    return tuple(reversed(parts))


def driver_id(node, name, sep='.'):
    """`x_axis.motor`: the instance path joined with the class-local
    driver name. `sep='__'` produces the flat-identifier variant."""
    return sep.join(instance_path(node) + (name,))


class DriverToken(OpenSCADConstant):
    """A symbolic read of one driver on one node instance.

    Subclassing `OpenSCADConstant` is the whole trick. Arithmetic
    flattens into a plain `OpenSCADConstant` carrying the qualified id
    inside the string (string-eagerness working FOR us, since the id is
    final at the moment the token is made), and `solid_node.math`'s
    `_is_symbolic` accepts it, so degree trig emits OpenSCAD call
    strings around the id exactly as it does around `$t`.

    The object references are kept only for diagnostics; nothing in the
    spike reads them to build the wire string.
    """

    def __init__(self, node, name, sep='.'):
        self.driver_node = node
        self.driver_name = name
        super().__init__(driver_id(node, name, sep))


# ------------------------------------------------------------- binding

def bind(node, resolve, sep='.'):
    """Bind every declared driver in the tree below (and including)
    `node`, per instance, then render and recurse.

    `resolve(node, name, declaration)` returns the value to bind --
    a `DriverToken` for the symbolic pass, a number for a snapshot.

    Order is the load-bearing part and mirrors `InternalNode.as_scad`
    and `core/serializer.serialize_node`: bind THIS node, render it
    (which is where its expressions are built), then link each child
    BEFORE recursing into it, so by the time a child's render() runs it
    already knows its own name and parent -- which is what makes eager
    qualification possible at all.

    SEAM 1 (symbolic binding): `_states` is written directly rather
    than through `set_state`, because `AssemblyNode._validate_state`
    rejects anything `as_number()` rejects. A symbolic value is
    deliberately not a number, so the loud-unbound/plain-number
    contract and a symbolic serialization pass cannot both go through
    today's single door.

    SEAM 2 (per-instance binding): `set_state` propagates one flat dict
    to every descendant, so two instances of one class cannot be given
    different values for their same-named driver. This walk binds each
    node's own dict.
    """
    states = getattr(node, '_states', None)
    if states is None:                      # a leaf: no drivers, no children
        return
    for name, declaration in declared_drivers(type(node)).items():
        states[name] = resolve(node, name, declaration)
    rendered = node.render()
    if type(rendered) not in (list, tuple):
        return
    for child in rendered:
        node._link_child(child)
        bind(child, resolve, sep)


def bind_symbolic(node, sep='.'):
    """Bind every driver in the tree to its own qualified token."""
    bind(node, lambda n, name, decl: DriverToken(n, name, sep), sep)


def bind_numeric(node, snapshot, sep='.'):
    """Bind every driver from a snapshot keyed by QUALIFIED id --
    the state-bank shape sub-question 5 asks for."""
    def resolve(n, name, declaration):
        key = driver_id(n, name, sep)
        if key not in snapshot:
            raise KeyError(f'no value for driver {key}; snapshot has '
                           f'{sorted(snapshot)}')
        return snapshot[key]
    bind(node, resolve, sep)


def qualified_drivers(root, sep='.'):
    """Every driver in the assembled tree, by qualified id, with the
    node instance and declaration -- the enumeration a driver TABLE (or
    a qualified `Sim` state bank) would publish. Requires the tree to
    have been linked already (see `bind`)."""
    found = {}

    def walk(node):
        if not hasattr(node, '_states'):
            return
        for name, declaration in declared_drivers(type(node)).items():
            found[driver_id(node, name, sep)] = (node, name, declaration)
        rendered = node.render()
        if type(rendered) not in (list, tuple):
            return
        for child in rendered:
            node._link_child(child)
            walk(child)

    walk(root)
    return found


# ------------------------------------------------------------- readback

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
