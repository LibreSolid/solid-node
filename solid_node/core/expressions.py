# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Compile native motion graphs and legacy scalar text into shared outputs.

Framework arithmetic stores operand references, not strings. Publication
interns only reachable nodes, counts repeated uses and emits the existing
schema-4 binding language. The SCAD boundary emits closed scalar let bindings.
The iterative parser imports legacy scalar text (including those closures);
unknown legacy syntax keeps its verbatim fallback with a bounded warning.

This is an internal compiler, not a new public motion or viewer language.
Numerical order, degree math and the original schema-4 contract are preserved.
"""
import logging
import re


logger = logging.getLogger('core.expressions')

#: Kinds a node take. 'num' and 'name' are leaves; the rest are compound.
_LEAF_KINDS = ('num', 'name')

_NAME_RE = re.compile(r'\$t|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')

#: How much of an unreadable expression a warning names -- a published
#: expression may be megabytes, and the offending text is diagnostic, not
#: the whole document restated.
_WARNING_TRUNCATION = 200


class ExpressionError(ValueError):
    """Text that is not in the language the two producers emit.

    Never raised for text that publishes and renders today: solid2's own
    output always parses. This is raised only for a `scad_inline` string,
    or otherwise hand-built text, outside that language -- and the caller
    (`bind_expressions`) catches it, publishing the offending expression
    verbatim and unshared rather than failing the build.
    """


class BindingTableError(ValueError):
    """A bindings table the producer would publish is wrong.

    Always a framework defect, never a project's fault (design.md D2):
    an entry naming a later entry, a name colliding with a declared
    driver id, or a rewrite that does not reproduce what the producer
    built. Raising here means the document is not written at all.
    """


class Node:
    """One structurally-interned expression node.

    `kind` is one of `'num'`, `'name'` (leaves, carrying their own literal
    `text`) or `'unary'`, `'binop'`, `'call'` (compound, carrying `children`
    and an `op` -- the operator symbol or the called name). Interning makes
    identity equality structural equality: two parses of equal structure
    return the SAME `Node` object, which is what lets occurrence counting
    and the round-trip test (tasks.md 1.4) use `is`.
    """

    __slots__ = ('id', 'kind', 'op', 'children', 'text')

    def __init__(self, id, kind, op=None, children=(), text=None):
        self.id = id
        self.kind = kind
        self.op = op
        self.children = children
        self.text = text

    def __repr__(self):
        if self.kind in _LEAF_KINDS:
            return f'<Node {self.kind} {self.text[:80]!r}>'
        return f'<Node {self.kind} {self.op!r} x{len(self.children)}>'


class Interner:
    """The structural table: one canonical `Node` per `(kind, op, child
    ids)`, and how many times each was returned.

    `order` is creation order. A compound node is only created once its
    children already exist, so `order` is a topological order -- a child
    always precedes its parents -- which is what lets the bindings table be
    built by a single pass over it (design.md D5).
    """

    def __init__(self):
        self._table = {}
        self.order = []
        self.counts = {}

    def leaf(self, kind, text):
        key = (kind, text)
        node = self._table.get(key)
        if node is None:
            node = Node(len(self.order), kind, op=text, text=text)
            self._table[key] = node
            self.order.append(node)
        self.touch(node)
        return node

    def compound(self, kind, op, children):
        key = (kind, op, tuple(child.id for child in children))
        node = self._table.get(key)
        if node is None:
            node = Node(len(self.order), kind, op=op, children=children)
            self._table[key] = node
            self.order.append(node)
        self.touch(node)
        return node

    def touch(self, node):
        """Record one more use of `node` -- including its own creation,
        which is the first use. `(big * big)` uses `big` twice even though
        nothing else ever will (design.md D5: "occurrences, not distinct
        parents")."""
        self.counts[node] = self.counts.get(node, 0) + 1


def parse(text, interner=None, memo=None):
    """Parse a scalar or a local SCAD closure without Python recursion.

    The optional memo argument is retained for legacy callers. Sharing comes
    from the supplied interner, not substring copies of the input text.
    """
    from .expression_parser import Parser
    return Parser(text, interner if interner is not None else Interner(),
                  ExpressionError).parse()


def render(node, names=None):
    """Render once into tokens, substituting shared children before descent.

    Unlike recursively concatenating strings, this takes output-linear memory
    for deep unshared expressions too. The root itself is always rendered.
    """
    names = names or {}
    output = []
    stack = [node]
    first = True
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            output.append(item)
            continue
        if not first and item in names:
            output.append(names[item])
            continue
        first = False
        if item.kind in ('num', 'name', 'raw'):
            output.append(item.text)
        elif item.kind == 'unary':
            stack.extend([')', item.children[0], '(-'])
        elif item.kind == 'binop':
            left, right = item.children
            stack.extend([')', right, f' {item.op} ', left, '('])
        elif item.kind == 'call':
            stack.append(')')
            for index in range(len(item.children) - 1, -1, -1):
                stack.append(item.children[index])
                if index:
                    stack.append(', ')
            stack.append(item.op + '(')
        else:
            raise AssertionError(f'unknown node kind {item.kind!r}')
    return ''.join(output)

def _truncate(text, limit=_WARNING_TRUNCATION):
    if len(text) <= limit:
        return text
    return f'{text[:limit]}... ({len(text)} characters total)'


def _is_bindable(node):
    """Every shared node except a bare number or a bare name (design.md
    D5): a reference costs four characters, and a literal or a driver id is
    shorter written out than referenced."""
    return node.kind not in _LEAF_KINDS


def _mint_prefix(driver_ids):
    """The prefix `_mint_names` mints under: `_b`, lengthened by a leading
    underscore for as long as some declared driver id matches
    `<prefix>\\d+` (design.md D4). Returned separately from the names
    themselves so a caller -- `_validate_bindings` -- can recognise a
    MINTED-LOOKING name without re-deriving the prefix from the table."""
    prefix = '_b'
    while True:
        pattern = re.compile(r'\A' + re.escape(prefix) + r'\d+\Z')
        if not any(pattern.match(identifier) for identifier in driver_ids):
            return prefix
        prefix = '_' + prefix


def _mint_names(shared_nodes, prefix):
    """`_b0`, `_b1`, ... in table order, under `prefix` (design.md D4)."""
    return {node: f'{prefix}{index}' for index, node in enumerate(shared_nodes)}


def _bindings_list(shared_nodes, names):
    """The ordered table: each entry's own text, built with only the
    names minted before it visible -- which is what makes an entry name
    only $t, a driver id, or an earlier entry (design.md D3)."""
    entries = []
    visible = {}
    for node in shared_nodes:
        entries.append({'name': names[node], 'expression': render(node, visible)})
        visible[node] = names[node]
    return entries


def _name_leaves(node):
    from solid_node.expression_graph import postorder
    for item in postorder([node]):
        if item.kind == 'name':
            yield item.text

def _validate_bindings(bindings, driver_ids, prefix):
    """Refuse a table that would be wrong (design.md D2): an entry naming
    a later entry, or a name colliding with a declared driver id. Cheap --
    proportional to the table's own text, not the document it replaces --
    and a defect caught here is always the framework's, never a project's:
    a correct table can never trip it.

    The ordering rule binds only MINTED names -- those matching
    `<prefix>\\d+`, `prefix` being exactly what `_mint_prefix` chose for
    this document. Any other leaf name an entry's expression carries ($t
    aside) is the project's business, not this table's: a `scad_inline`
    constant, a name from solid2 the framework never declared, anything the
    consumer already resolves or already refuses on its own -- publishing
    it unexamined is what D2 requires ("refusal is for a table that would
    be wrong, never a project's fault"). Only a name that LOOKS like one of
    this table's own references but does not resolve is a genuine defect:
    an entry naming a later entry, or a stray reference to a name this
    table never minted.
    """
    declared = set(driver_ids)
    earlier = set()
    minted = re.compile(r'\A' + re.escape(prefix) + r'\d+\Z')
    for entry in bindings:
        name, expression = entry['name'], entry['expression']
        if name in declared:
            raise BindingTableError(
                f'binding name {name!r} collides with a declared driver id')
        if name in earlier:
            raise BindingTableError(f'binding name {name!r} is minted twice')
        try:
            node = parse(expression)
        except (ExpressionError, RecursionError) as error:
            # A binding's own text is always something this module rendered
            # from an already-parsed node (bind_expressions never binds an
            # expression it could not read), so this can only mean the
            # renderer and the parser disagree -- a framework defect.
            raise BindingTableError(
                f"binding {name!r}'s expression {_truncate(expression)!r} is not in "
                f'the language this table is written in: {error}') from error
        for leaf in _name_leaves(node):
            if leaf == '$t' or leaf in declared or leaf in earlier:
                continue
            if not minted.match(leaf):
                # An ordinary name this table did not mint: the project's
                # business, unexamined (see the docstring above).
                continue
            raise BindingTableError(
                f'binding {name!r} names {leaf!r}, which looks like a '
                f'minted binding reference but is not $t, a declared '
                f'driver id, or an entry earlier in the table')
        earlier.add(name)


def _matches(original, candidate, names):
    """Compare graph structure without expansion or recursive equality."""
    stack = [(original, candidate)]
    seen = set()
    while stack:
        a, b = stack.pop()
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if a in names and b.kind == 'name' and b.text == names[a]:
            continue
        if a.kind != b.kind or a.op != b.op:
            return False
        if a.kind in _LEAF_KINDS:
            if a.text != b.text:
                return False
        elif len(a.children) != len(b.children):
            return False
        stack.extend(zip(a.children, b.children))
    return True

def _verify_reconstruction(rewritten, parsed, bindings, names):
    """Refuse a rewrite that does not reproduce what the producer built
    (design.md D2) -- a framework defect, never reachable from correct
    model input, since the rewrite is built directly from the same nodes
    this checks against. A safety net, not a re-derivation: cost is
    proportional to the published (small) text, not the document that was
    flattened to build it."""
    entry_text = {entry['name']: entry['expression'] for entry in bindings}
    for node, name in names.items():
        candidate = parse(entry_text[name])
        if not _matches(node, candidate, names):
            raise BindingTableError(
                f'binding {name!r} does not reproduce the subexpression '
                f'it was minted for')
    for text, original in zip(rewritten, parsed):
        if original is None:
            continue
        if names.get(original) == text:
            continue
        candidate = parse(text)
        if not _matches(original, candidate, names):
            raise BindingTableError(
                'a rewritten expression does not reproduce what the '
                'producer built once its bindings are resolved')


def _canonical(roots):
    """Intern reachable identities, then count occurrences (saturated at two)."""
    from solid_node.expression_graph import postorder
    interner = Interner()
    copies = {}
    for node in postorder(roots):
        if node.kind in ('num', 'name', 'raw'):
            copies[node] = interner.leaf(node.kind, node.text)
        else:
            copies[node] = interner.compound(
                node.kind, node.op, tuple(copies[c] for c in node.children))
    result = [copies[node] for node in roots]
    counts = {}
    for node in result:
        counts[node] = min(2, counts.get(node, 0) + 1)
    for node in reversed(interner.order):
        count = counts.get(node, 0)
        for child in node.children:
            counts[child] = min(2, counts.get(child, 0) + count)
    interner.counts = counts
    return result, interner


def scad_expression(root):
    """A closed SCAD scalar. No expanded intermediate, no global variables."""
    roots, interner = _canonical([root])
    root = roots[0]
    occupied = {n.text for n in interner.order if n.kind == 'name'}
    # Opaque legacy text can contain free identifiers outside our scalar
    # grammar; avoid capturing any of them as well.
    for node in interner.order:
        if node.kind == 'raw':
            occupied.update(_NAME_RE.findall(node.text))
    prefix = '_s'
    while any(re.fullmatch(re.escape(prefix) + r'\d+', n) for n in occupied):
        prefix = '_' + prefix
    shared = [n for n in interner.order
              if n.kind not in ('num', 'name', 'raw') and interner.counts[n] > 1]
    names = _mint_names(shared, prefix)
    if not shared:
        return render(root)
    bindings = _bindings_list(shared, names)
    body = names.get(root) or render(root, names)
    definitions = ', '.join(f"{b['name']} = {b['expression']}" for b in bindings)
    return f'let({definitions}) {body}'


def bind_expressions(expressions, driver_ids):
    """Compile native roots and legacy scalar strings into schema-4 bindings.

    Native motion never passes through text. Unreadable legacy expressions
    retain their historical verbatim fallback and bounded warning.
    """
    from solid_node.expression_graph import ExpressionNode, postorder
    driver_ids = tuple(driver_ids)
    parsed = []
    originals = []
    warnings = []
    legacy_interner = Interner()
    expressions = list(expressions)
    native_roots = [getattr(expr, '_expression_node', expr) for expr in expressions]
    raw = {}
    for node in postorder([n for n in native_roots if isinstance(n, (ExpressionNode, Node))]):
        raw[node] = node.kind == 'raw' or any(raw[c] for c in node.children)
    for expression, native in zip(expressions, native_roots):
        if isinstance(native, (ExpressionNode, Node)):
            if raw[native]:
                original = scad_expression(native)
                node = None
            else:
                original, node = None, native
        elif isinstance(expression, str):
            original = expression
            try:
                node = parse(expression, legacy_interner)
            except ExpressionError:
                node = None
        else:
            originals.append(expression)
            parsed.append(None)
            continue
        if node is None:
            message = ('an expression could not be read by the bindings pass '
                       'and will be published verbatim and unshared '
                       f'(text: {_truncate(original)!r})')
            warnings.append(message)
            logger.warning(message)
        parsed.append(node)
        originals.append(original)

    valid, interner = _canonical([node for node in parsed if node is not None])
    valid = iter(valid)
    parsed = [next(valid) if node is not None else None for node in parsed]
    shared = [node for node in interner.order
              if _is_bindable(node) and interner.counts.get(node, 0) > 1]
    names = _mint_names(shared, _mint_prefix(driver_ids))
    bindings = _bindings_list(shared, names)
    # Compute descendant flags once, including for deep unshared chains.
    has_names = {}
    for node in interner.order:
        has_names[node] = any(c in names or has_names[c] for c in node.children)
    rewritten = []
    for original, node in zip(originals, parsed):
        if node is None:
            rewritten.append(original)
        elif node in names:
            rewritten.append(names[node])
        elif has_names[node] or original is None or re.search(r'\blet\s*\(', original):
            rewritten.append(render(node, names))
        else:
            rewritten.append(original)
    _validate_bindings(bindings, driver_ids, _mint_prefix(driver_ids))
    _verify_reconstruction(rewritten, parsed, bindings, names)
    return rewritten, bindings, warnings
